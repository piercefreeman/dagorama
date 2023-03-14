package main

import (
	"context"
	"sync"

	"github.com/uptrace/bun"
)

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
	queueName string,
	taintName string,
	arguments []byte,
	sources []*DAGNode,
	retryPolicy *RetryPolicy,
) *DAGNode {
	node := &DAGNode{
		identifier:         identifier,
		functionName:       functionName,
		functionHash:       functionHash,
		queueName:          queueName,
		taintName:          taintName,
		arguments:          arguments,
		sources:            sources,
		destinations:       make([]*DAGNode, 0),
		completed:          false,
		instance:           instance,
		failures:           make([]*DAGFailure, 0),
		failuresLock:       sync.RWMutex{},
		retryPolicy:        retryPolicy,
		nextRetryAvailable: -1,
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

func (instance *DAGInstance) InsertIntoDatabase(db *bun.DB) error {
	persistentInstance := PersistentDAGInstance{
		Identifier: instance.identifier,
		Order:      instance.order,
	}

	_, err := db.NewInsert().Model(&persistentInstance).Exec(context.Background())
	return err
}
