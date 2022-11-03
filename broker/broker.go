package main

import (
	"log"
	"math"
	"sync"
	"time"

	"github.com/google/uuid"
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
	claimedWork []*DAGNode

	// True if a worker has been garbage collected by the server
	invalidated bool
}

func (worker *Worker) Ping() {
	worker.lastPing = time.Now().Unix()
}

type DAGNode struct {
	identifier   string
	functionName string

	// Hash of function code logic, used by workers to determine if their local
	// version of the code is the same as the version that was queued originally
	functionHash string

	// The arguments array should contain all arguments that are passed to this node, including
	// client side
	arguments []byte

	// src values of the (src, dst) that end at this dst
	sources []*DAGNode

	// dst of the (src, dst) edges that start at this src
	destinations []*DAGNode

	// Once we have determined the value for the DAG (ie. the return value
	// of the actual function), populate the next DAGs with the value
	// Might be null even for completed objects if no return value is specified
	resolvedValue []byte

	// True if this node has resolved its execution
	completed bool

	// The instance that spawned this DAG node
	instance *DAGInstance

	// Worker that is currently executing this node
	dequeueTimestamp int64
	dequeueWorker    *Worker
}

func (node *DAGNode) ValueDidResolve(value []byte) {
	/*
	 * Called by clients when we have finalized a value for this DAG Node
	 */
	// Handle resolution
	node.resolvedValue = value
	node.completed = true

	// Release the worker lock
	node.dequeueTimestamp = 0
	node.dequeueWorker = nil

	// Dequeue destinations
	// If all are valid, enqueue into the actual DAG queue
	for _, destination := range node.destinations {
		destination.DependencyDidResolve()
	}
}

func (node *DAGNode) DependencyDidResolve() {
	/*
	 * Check if all dependencies have resolved
	 * If so, enqueue into the DAG queue
	 */
	dependenciesComplete := true
	for _, dependency := range node.sources {
		if !dependency.completed {
			dependenciesComplete = false
			break
		}
	}

	if dependenciesComplete {
		// Add to queue
		node.instance.broker.EnqueueNode(node)
	}
}

type DAGInstance struct {
	/*
	 * One instance of a DAG. The result of an client-side `entrypoint` that kicks
	 * off the rest of the job logic.
	 */
	// DAGs are prioritized based on the order in which they were inserted into
	// the queue. This becomes the priority order added to the queue DAGs.
	identifier string
	order      int

	// ID -> DAGNode
	// Will keep nodes retained until we cleanup the instance
	nodeLock sync.RWMutex
	nodes    map[string]*DAGNode

	broker *Broker
}

func (instance *DAGInstance) NewNode(
	identifier string,
	functionName string,
	functionHash string,
	arguments []byte,
	sources []*DAGNode,
) *DAGNode {
	node := &DAGNode{
		identifier:   identifier,
		functionName: functionName,
		functionHash: functionHash,
		arguments:    arguments,
		sources:      sources,
		destinations: make([]*DAGNode, 0),
		completed:    false,
		instance:     instance,
	}

	instance.nodeLock.Lock()
	defer instance.nodeLock.Unlock()

	instance.nodes[identifier] = node

	// Make sure we create the back-link
	for _, source := range sources {
		source.destinations = append(source.destinations, node)
	}

	// Determine whether this node is ready to be executed
	// This is the same logic as the notification that we receive when
	// an actual dependency is completed, so we can reuse the same
	// notification function
	node.DependencyDidResolve()

	return node
}

func (instance *DAGInstance) GetNode(identifier string) *DAGNode {
	instance.nodeLock.RLock()
	defer instance.nodeLock.RUnlock()

	return instance.nodes[identifier]
}

func (instance *DAGInstance) release() {
	/*
	 * Release cached values associated with DAG
	 * Also destroy the DAGNode objects
	 * TODO: Execute automatically under some conditions, like all DAG stages
	 * completed or similar.
	 */
}

type Broker struct {
	// Mapping of function name to queue
	// Once an item is added to the queue it should be ready for execution
	taskQueuesLock sync.Mutex
	taskQueues     map[string]*HeapQueue

	// Separate instantiations of each DAG
	// Mapping of ID -> DAGInstance
	instancesLock sync.RWMutex
	instances     map[string]*DAGInstance

	workerLock sync.RWMutex
	workers    map[string]*Worker

	// Require a ping within this interval or a worker will be considered unhealthy
	// and removed from the pool, seconds
	requiredPingInterval int
}

func NewBroker() *Broker {
	return &Broker{
		taskQueuesLock:       sync.Mutex{},
		taskQueues:           make(map[string]*HeapQueue),
		instancesLock:        sync.RWMutex{},
		instances:            make(map[string]*DAGInstance),
		workerLock:           sync.RWMutex{},
		workers:              make(map[string]*Worker),
		requiredPingInterval: 60,
	}
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
	broker.taskQueuesLock.Lock()
	defer broker.taskQueuesLock.Unlock()

	// Create the queue if it doesn't exist
	if _, ok := broker.taskQueues[node.functionName]; !ok {
		broker.taskQueues[node.functionName] = NewHeapQueue()

		// Clear the cache of allowed worker queues since we have just added
		// a new one that will invalidate the cache
		for _, worker := range broker.workers {
			worker.allowedQueues = []string{}
		}
	}

	// Add to queue
	broker.taskQueues[node.functionName].PushItem(node, node.instance.order)
}

func (broker *Broker) PopNextNode(worker *Worker) *DAGNode {
	// Find the queue with the minimum priority
	// Ties in priority from different queues will choose an item arbitrarily
	broker.taskQueuesLock.Lock()
	defer broker.taskQueuesLock.Unlock()

	minimumPriority := math.MaxInt64
	minimumQueueName := ""

	allowedQueues := broker.getAllowedQueues(worker)
	log.Printf("Allowed queues: %v", allowedQueues)

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
			log.Printf("Garbage collecting worker %s", workerID)

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
