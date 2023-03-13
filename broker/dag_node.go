package main

import (
	"sync"

	"github.com/uptrace/bun"
)

type DAGFailure struct {
	/*
	 * Record client-side errors and exceptions
	 */
	traceback string
}

type DAGNode struct {
	identifier   string
	functionName string

	queueName string
	taintName string

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

	// Store failures on past invocations of this node
	retryPolicy  *RetryPolicy
	failures     []*DAGFailure
	failuresLock sync.RWMutex
}

func (node *DAGNode) ExecutionDidResolve(value []byte) {
	/*
	 * Called by clients when we have finalized a value for this DAG Node
	 */
	// Handle resolution
	node.resolvedValue = value
	node.completed = true

	// Release the worker lock from the element
	node.ReleaseWorkerLock()

	// Dequeue destinations
	// If all are valid, enqueue into the actual DAG queue
	for _, destination := range node.destinations {
		destination.DependencyDidResolve()
	}

	// Update the database
	node.UpsertIntoDatabase(node.instance.broker.database, 0)
}

func (node *DAGNode) ExecutionDidFail(traceback string) {
	failure := DAGFailure{
		traceback: traceback,
	}

	// Release the worker lock
	node.ReleaseWorkerLock()

	// Record the failure as part of this node
	node.failuresLock.Lock()
	defer node.failuresLock.Unlock()
	node.failures = append(node.failures, &failure)

	// Requeue back into the DAG with the node's backoff policy
	node.instance.broker.BackoffNode(node)
}

func (node *DAGNode) ReleaseWorkerLock() {
	/*
	 * Releases the worker's sole control over this element
	 * but won't yet requeue the element
	 */
	worker := node.dequeueWorker
	if worker != nil {
		worker.claimedWorkLock.Lock()
		defer worker.claimedWorkLock.Unlock()

		worker.claimedWork = filterSlice(worker.claimedWork, func(compareNode *DAGNode) bool {
			return compareNode.identifier != node.identifier
		})
	}

	// Release the worker lock from the note
	node.dequeueTimestamp = 0
	node.dequeueWorker = nil
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

func (node *DAGNode) UpsertIntoDatabase(
	db *bun.DB,
	priority int64,
) error {
	/*
	 * Upsert the node into the database
	 */
	persistentNode := PersistentDAGNode{
		Priority: priority,

		Identifier:   node.identifier,
		FunctionName: node.functionName,
		QueueName:    node.queueName,
		TaintName:    node.taintName,
		FunctionHash: node.functionHash,
		Arguments:    node.arguments,
		SourceIdentifiers: func() []string {
			identifiers := make([]string, len(node.sources))
			for i, source := range node.sources {
				identifiers[i] = source.identifier
			}
			return identifiers
		}(),
		DestinationIdentifiers: func() []string {
			identifiers := make([]string, len(node.destinations))
			for i, destination := range node.destinations {
				identifiers[i] = destination.identifier
			}
			return identifiers
		}(),
		ResolvedValue:                     node.resolvedValue,
		Completed:                         node.completed,
		InstanceIdentifier:                node.instance.identifier,
		RetryPolicyEnabled:                node.retryPolicy != nil,
		RetryPolicyCurrentAttempt:         TernaryIfDelayed(node.retryPolicy != nil, func() int { return node.retryPolicy.currentAttempt }, func() int { return -1 }),
		RetryPolicyMaxAttempts:            TernaryIfDelayed(node.retryPolicy != nil, func() int { return node.retryPolicy.maxAttempts }, func() int { return -1 }),
		RetryPolicyStaticInterval:         TernaryIfDelayed(node.retryPolicy != nil, func() int { return node.retryPolicy.staticInterval }, func() int { return -1 }),
		RetryPolicyExponentialBackoffBase: TernaryIfDelayed(node.retryPolicy != nil, func() int { return node.retryPolicy.exponentialBackoffBase }, func() int { return -1 }),
		Failures: func() []interface{} {
			failures := make([]interface{}, len(node.failures))
			for i, failure := range node.failures {
				failures[i] = *failure
			}
			return failures
		}(),
	}

	err := upsertDatabaseObject(db, &persistentNode)
	return err
}
