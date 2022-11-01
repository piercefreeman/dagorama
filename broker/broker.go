package main

import (
	"math"
	"sync"
)

// TODO: https://github.com/grpc/grpc/blob/v1.50.0/examples/python/route_guide/route_guide_client.py

type DAGNode struct {
	identifier   string
	functionName string

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
}

func (node *DAGNode) ValueDidResolve(value []byte) {
	/*
	 * Called by clients when we have finalized a value for this DAG Node
	 */
	// Handle resolution
	node.resolvedValue = value
	node.completed = true

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
	nodeLock sync.RWMutex
	nodes    map[string]*DAGNode

	broker *Broker
}

func (instance *DAGInstance) NewNode(
	identifier string,
	functionName string,
	arguments []byte,
	sources []*DAGNode,
) *DAGNode {
	node := &DAGNode{
		identifier:   identifier,
		functionName: functionName,
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

func (instance *DAGInstance) release() {
	/*
	 * Release cached values associated with DAG
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
	executionsLock sync.RWMutex
	executions     map[string]*DAGInstance
}

func NewBroker() *Broker {
	return &Broker{
		taskQueuesLock: sync.Mutex{},
		taskQueues:     make(map[string]*HeapQueue),
		executionsLock: sync.RWMutex{},
		executions:     make(map[string]*DAGInstance),
	}
}

func (broker *Broker) NewInstance(identifier string) *DAGInstance {
	broker.executionsLock.Lock()
	defer broker.executionsLock.Unlock()

	instance := &DAGInstance{
		identifier: identifier,
		order:      len(broker.executions),
		nodeLock:   sync.RWMutex{},
		nodes:      make(map[string]*DAGNode),
		broker:     broker,
	}
	broker.executions[identifier] = instance

	return instance
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
	}

	// Add to queue
	broker.taskQueues[node.functionName].PushItem(node, node.instance.order)
}

func (broker *Broker) PopNextNode(queues []string) *DAGNode {
	// Find the queue with the minimum priority
	// Ties in priority from different queues will choose an item arbitrarily
	broker.taskQueuesLock.Lock()
	defer broker.taskQueuesLock.Unlock()

	minimumPriority := math.MaxInt64
	minimumQueueName := ""

	for queueName, queue := range broker.taskQueues {
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

	return broker.taskQueues[minimumQueueName].PopItem().node
}

func (broker *Broker) filterForQueues(
	excludeQueues []string,
	includeQueues []string,
	queueTolerations []string,
) []string {
	/*
	 * Queues that are specifically parameterized by a "worker_taint"
	 * need to be specifically picked up by a worker with it provided
	 * in the `queue_tolerations`
	 */
	allQueues := make([]string, 0)
	for queueName, _ := range broker.taskQueues {
		allQueues = append(allQueues, queueName)
	}

	// If include_queues is provided, we need to limit our search
	// to only those queues
	if len(includeQueues) > 0 {
		allQueues = filterSlice(allQueues, func(queueName string) bool {
			return contains(includeQueues, queueName)
		})
	}

	// Exclude the listed queues
	allQueues = filterSlice(allQueues, func(queueName string) bool {
		return !contains(excludeQueues, queueName)
	})

	// If a toleration is provided on the queue, make sure it is in our
	// list of tolerations
	allQueues = filterSlice(allQueues, func(queueName string) bool {
		queue := broker.taskQueues[queueName]
		return contains(queueTolerations, queue.taint)
	})

	return allQueues
}
