package main

// TODO: https://github.com/grpc/grpc/blob/v1.50.0/examples/python/route_guide/route_guide_client.py

type ArgumentOrder struct {
	index int

	// optional keyword key if this is part of the python kwargs
	// blank if part of the args list
	kwarg string

	// pickled value
	staticValue byte

	// src values of the (src, dst) that end at this dst
	dynamicValue *DAGNode
}

type DAGNode struct {
	functionName string
	arguments    []ArgumentOrder

	// dst of the (src, dst) edges that start at this src
	destinations []*DAGNode

	// Once we have determined the value for the DAG (ie. the return value
	// of the actual function), populate the next DAGs with the value
	// Might be null even for completed objects if no return value is specified
	resolvedValue byte

	// True if this node has resolved its execution
	completed bool
}

func (node *DAGNode) validDidResolve(value byte) {
	// handle resolution
	node.resolvedValue = value
	node.completed = true

	// dequeue destinations
	// if all are valid, enqueue into the actual DAG queue
}

type DAGInstance struct {
	/*
	 * One instance of a DAG. The result of an client-side `entrypoint` that kicks
	 * off the rest of the job logic.
	 */
	// DAGs are prioritized based on the order in which they were inserted into
	// the queue. This becomes the priority order added to the queue DAGs.
	order int

	// ID -> DAGDefinition
	definitions map[string]*DAGNode
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
	taskQueues map[string]*HeapQueue

	// Separate instantiations of each DAG
	executions map[string]*DAGInstance
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
	});

	return allQueues;
}

func (broker *Broker) popJob(
	dag *DAGInstance,
	queues: []string,
) {
}
