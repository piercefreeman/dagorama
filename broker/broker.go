package main

import (
	"context"
	"fmt"
	"math"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/uptrace/bun"
	"go.uber.org/zap"
)

type Worker struct {
	identifier string

	// Milliseconds since epoch of last client ping
	lastPing int64

	// Constraints on choosing the allowed queues
	excludeQueues    []string
	includeQueues    []string
	queueTolerations []string

	// Cache of allowed queues that the worker is allowed to pull from.
	// When this list is empty, we will re-compute the allowed queues given
	// the above defined constraints.
	allowedQueues []string

	// We only expect one task to be executing at a time but we store nodes as a
	// list to allow for future expansion.
	claimedWork     []*DAGNode
	claimedWorkLock sync.RWMutex

	// True if a worker has been garbage collected by the server
	invalidated bool
}

func (worker *Worker) Ping() {
	worker.lastPing = time.Now().Unix()
}

type Broker struct {
	// Mapping of function name to queue
	// Once an item is added to the queue it should be ready for execution
	taskQueuesLock sync.Mutex
	taskQueues     map[string]*HeapQueue

	// Unscheduled DAGs aren't yet ready for queuing because we are still waiting
	// for their backoff intervals. Unlike in the regular task queues these objects
	// are parameterized by their timestamp rather than their desired execution order
	futureScheduledNodesLock sync.RWMutex
	futureScheduledNodes     *HeapQueue

	// Separate instantiations of each DAG
	// Mapping of ID -> DAGInstance
	instancesLock sync.RWMutex
	instances     map[string]*DAGInstance

	workerLock sync.RWMutex
	workers    map[string]*Worker

	// Require a ping within this interval or a worker will be considered unhealthy
	// and removed from the pool, seconds
	requiredPingInterval int

	logger *zap.Logger

	// Only set if we're using a persistent storage backend
	database *bun.DB
}

func NewBroker(config *Config) *Broker {
	// If we're set to debug, allocate a debug session
	// Otherwise default to production
	var logger *zap.Logger
	if config.environment == "development" {
		logger, _ = zap.NewDevelopment()
	} else {
		logger, _ = zap.NewProduction()
	}

	var database *bun.DB = nil
	if config.storage.enabled {
		database = NewDatabase(
			config.storage.host,
			config.storage.port,
			config.storage.username,
			config.storage.password,
			config.storage.database,
		)
	}

	broker := &Broker{
		taskQueuesLock:           sync.Mutex{},
		taskQueues:               make(map[string]*HeapQueue),
		futureScheduledNodesLock: sync.RWMutex{},
		futureScheduledNodes:     NewHeapQueue(),
		instancesLock:            sync.RWMutex{},
		instances:                make(map[string]*DAGInstance),
		workerLock:               sync.RWMutex{},
		workers:                  make(map[string]*Worker),
		requiredPingInterval:     60,
		logger:                   logger,
		database:                 database,
	}

	if database != nil {
		err := broker.LoadFromDatabase()
		if err != nil {
			panic(err)
		}
	}

	return broker
}

func (broker *Broker) NewWorker(
	excludeQueues []string,
	includeQueues []string,
	queueTolerations []string,
) *Worker {
	worker := &Worker{
		identifier:       uuid.New().String(),
		excludeQueues:    excludeQueues,
		includeQueues:    includeQueues,
		queueTolerations: queueTolerations,
		claimedWork:      make([]*DAGNode, 0),
		claimedWorkLock:  sync.RWMutex{},
		invalidated:      false,
	}
	worker.Ping()

	broker.workerLock.Lock()
	defer broker.workerLock.Unlock()
	broker.workers[worker.identifier] = worker

	return worker
}

func (broker *Broker) NewInstance(identifier string) *DAGInstance {
	broker.instancesLock.Lock()
	defer broker.instancesLock.Unlock()

	instance := &DAGInstance{
		identifier: identifier,
		order:      len(broker.instances),
		nodeLock:   sync.RWMutex{},
		nodes:      make(map[string]*DAGNode),
		broker:     broker,
	}
	broker.instances[identifier] = instance

	// Add to the database
	if broker.database != nil {
		instance.InsertIntoDatabase(broker.database)
	}

	return instance
}

func (broker *Broker) GetWorker(identifier string) *Worker {
	broker.workerLock.RLock()
	defer broker.workerLock.RUnlock()

	return broker.workers[identifier]
}

func (broker *Broker) GetInstance(identifier string) *DAGInstance {
	broker.instancesLock.RLock()
	defer broker.instancesLock.RUnlock()

	return broker.instances[identifier]
}

func (broker *Broker) EnqueueNode(node *DAGNode) {
	/*
	 * Enqueue a DAG node into the appropriate queue
	 */
	broker.logger.Info("Enqueueing node", zap.String("identifier", node.identifier))
	broker.taskQueuesLock.Lock()
	defer broker.taskQueuesLock.Unlock()

	// Create the queue if it doesn't exist
	if _, ok := broker.taskQueues[node.queueName]; !ok {
		newQueue := NewHeapQueue()
		newQueue.taint = node.taintName
		broker.taskQueues[node.queueName] = newQueue

		// Clear the cache of allowed worker queues since we have just added
		// a new one that will invalidate the cache
		for _, worker := range broker.workers {
			worker.allowedQueues = []string{}
		}
	}

	// Add to queue
	nodePriority := int64(node.instance.order)
	broker.taskQueues[node.queueName].PushItem(node, nodePriority)

	// Save if relevant
	if broker.database != nil {
		node.UpsertIntoDatabase(broker.database, nodePriority)
	}
}

func (broker *Broker) BackoffNode(node *DAGNode) {
	/*
	 * The given node has failed so we need to determine when we want to retry
	 */
	if node.retryPolicy == nil {
		// No policy to retry, can skip
		return
	}

	broker.futureScheduledNodesLock.Lock()
	defer broker.futureScheduledNodesLock.Unlock()

	backoffInterval := node.retryPolicy.getWaitIntervalMilliseconds()
	if backoffInterval == -1 {
		// Have exhausted retry attempts, shouldn't queue back
		return
	}
	nodePriority := time.Now().UnixMilli() + int64(backoffInterval)
	broker.futureScheduledNodes.PushItem(node, nodePriority)

	// Save if relevant
	if broker.database != nil {
		node.UpsertIntoDatabase(broker.database, nodePriority)
	}
}

func (broker *Broker) PopNextNode(worker *Worker) *DAGNode {
	// Find the queue with the minimum priority
	// Ties in priority from different queues will choose an item arbitrarily
	broker.taskQueuesLock.Lock()
	defer broker.taskQueuesLock.Unlock()

	minimumPriority := int64(math.MaxInt64)
	minimumQueueName := ""

	allowedQueues := broker.getAllowedQueues(worker)
	broker.logger.Debug("Pop next node", zap.String("worker", worker.identifier), zap.Strings("allowedQueues", allowedQueues))

	for queueName, queue := range broker.taskQueues {
		// Only support the given queues
		if !contains(allowedQueues, queueName) {
			continue
		}

		topItem := queue.PeekItem()
		if topItem == nil {
			continue
		}

		if topItem.priority < minimumPriority {
			minimumPriority = topItem.priority
			minimumQueueName = queueName
		}
	}

	// Unable to find a matching item
	if minimumQueueName == "" {
		return nil
	}

	node := broker.taskQueues[minimumQueueName].PopItem().node

	// Assign to the given worker
	node.dequeueTimestamp = time.Now().Unix()
	node.dequeueWorker = worker
	worker.claimedWork = append(worker.claimedWork, node)

	return node
}

func (broker *Broker) GarbageCollectWorkers() {
	/*
	 * Periodically garbage collect workers that have not pinged in a while
	 */
	for true {
		broker.GarbageCollectWorkersExecute()
		time.Sleep(time.Duration(broker.requiredPingInterval) * time.Second)
	}
}

func (broker *Broker) GarbageCollectWorkersExecute() {
	for workerID, worker := range broker.workers {
		if worker.lastPing < time.Now().Unix()-int64(broker.requiredPingInterval) {
			broker.logger.Info("Garbage collecting worker", zap.String("identifier", workerID))

			// Free the currently processing nodes back into the pool
			for _, node := range worker.claimedWork {
				node.dequeueTimestamp = 0
				node.dequeueWorker = nil
				broker.EnqueueNode(node)
			}

			worker.claimedWork = make([]*DAGNode, 0)
			worker.invalidated = true
		}
	}
}

func (broker *Broker) QueueFutureScheduled() {
	/*
	 * Determines if any of the future scheduled nodes should be queued as being ready
	 * for work.
	 */
	for true {
		broker.QueueFutureScheduledExecute()
		time.Sleep(time.Duration(10) * time.Second)
	}
}

func (broker *Broker) QueueFutureScheduledExecute() {
	if broker.futureScheduledNodes.Length() == 0 {
		return
	}

	// The first element in the queue should always be the one that
	// is first in line to re-queue. The second that we hit an object that
	// isn't ready yet, we know all objects after it will be too.
	broker.futureScheduledNodesLock.Lock()
	defer broker.futureScheduledNodesLock.Unlock()

	for true {
		nextNode := broker.futureScheduledNodes.PeekItem()
		if nextNode == nil {
			break
		}

		if nextNode.priority > time.Now().UnixMilli() {
			// Not ready yet
			break
		}

		// Ready to re-queue
		node := broker.futureScheduledNodes.PopItem().node
		broker.EnqueueNode(node)
	}
}

func (broker *Broker) LoadFromDatabase() error {
	instances := []PersistentDAGInstance{}
	nodes := []PersistentDAGNode{}

	err := broker.database.NewSelect().Model(&instances).Scan(context.Background())

	if err != nil {
		return err
	}

	err = broker.database.NewSelect().Model(&nodes).Scan(context.Background())

	if err != nil {
		return err
	}

	// First we create all the relevant objects, without the obj->obj pointer mappings
	instancesById := make(map[string]*DAGInstance)
	nodesById := make(map[string]*DAGNode)
	invalidNodeIdentifiers := []string{}

	for _, instance := range instances {
		instancesById[instance.Identifier] = &DAGInstance{
			identifier: instance.Identifier,
			order:      instance.Order,
			broker:     broker,
		}
	}

	for _, node := range nodes {
		instance, exists := instancesById[node.InstanceIdentifier]

		if !exists {
			broker.logger.Error("Unable to find node->instance", zap.String("node", node.Identifier), zap.String("instance", node.InstanceIdentifier))
			continue
		}

		nodesById[node.Identifier] = &DAGNode{
			identifier:   node.Identifier,
			functionName: node.FunctionName,
			queueName:    node.QueueName,
			taintName:    node.TaintName,
			functionHash: node.FunctionHash,
			arguments:    node.Arguments,
			sources:      make([]*DAGNode, len(node.SourceIdentifiers)),
			destinations: make([]*DAGNode, len(node.DestinationIdentifiers)),
			instance:     instance,
		}
	}

	// Now go through and set the obj->obj pointers
	for _, node := range nodes {
		for i, sourceIdentifier := range node.SourceIdentifiers {
			source, exists := nodesById[sourceIdentifier]

			if !exists {
				broker.logger.Error("Unable to find node->source", zap.String("node", node.Identifier), zap.String("source", sourceIdentifier))
				invalidNodeIdentifiers = append(invalidNodeIdentifiers, node.Identifier)
				continue
			}

			nodesById[node.Identifier].sources[i] = source
		}
		for i, destinationIdentifier := range node.DestinationIdentifiers {
			destination, exists := nodesById[destinationIdentifier]

			if !exists {
				broker.logger.Error("Unable to find node->destination", zap.String("node", node.Identifier), zap.String("destination", destinationIdentifier))
				invalidNodeIdentifiers = append(invalidNodeIdentifiers, node.Identifier)
				continue
			}

			nodesById[node.Identifier].destinations[i] = destination
		}
	}

	// If a node is in the invalidNodeIdentifiers list, we couldn't resolve all their dependencies
	// We should drop their value from the map
	for _, invalidIdentifier := range invalidNodeIdentifiers {
		fmt.Printf("Invalid node dependencies %s, removing from queue.\n", invalidIdentifier)
		delete(nodesById, invalidIdentifier)
	}

	// Add to the broker
	for _, instance := range instancesById {
		broker.instances[instance.identifier] = instance
	}
	for _, node := range nodesById {
		broker.EnqueueNode(node)
	}

	return nil
}

func (broker *Broker) getAllowedQueues(worker *Worker) []string {
	/*
	 * Queues that are specifically parameterized by a "worker_taint"
	 * need to be specifically picked up by a worker with it provided
	 * in the `queue_tolerations`
	 */
	if len(worker.allowedQueues) > 0 {
		return worker.allowedQueues
	}

	allQueues := make([]string, 0)
	for queueName, _ := range broker.taskQueues {
		allQueues = append(allQueues, queueName)
	}

	// If include_queues is provided, we need to limit our search
	// to only those queues
	if len(worker.includeQueues) > 0 {
		allQueues = filterSlice(allQueues, func(queueName string) bool {
			return contains(worker.includeQueues, queueName)
		})
	}

	// Exclude the listed queues
	allQueues = filterSlice(allQueues, func(queueName string) bool {
		return !contains(worker.excludeQueues, queueName)
	})

	// If a toleration is provided on the queue, make sure it is in our
	// list of tolerations
	allQueues = filterSlice(allQueues, func(queueName string) bool {
		queue := broker.taskQueues[queueName]
		if queue.taint == "" {
			return true
		}
		return contains(worker.queueTolerations, queue.taint)
	})

	worker.allowedQueues = allQueues
	return allQueues
}
