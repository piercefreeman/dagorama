package main

import (
	"context"
	"testing"
)

func TestUpsertNode(t *testing.T) {
	nodeIdentifier := "123"
	nodeInitialFunction := "Entrypoint"
	nodeUpdatedFunction := "Updated Entrypoint"

	clearTestDatabase()

	config := getTestPersistentConfig()
	db := NewDatabase(
		config.storage.host,
		config.storage.port,
		config.storage.username,
		config.storage.password,
		config.storage.database,
	)

	node := &DAGNode{
		identifier:   nodeIdentifier,
		functionName: nodeInitialFunction,
		instance:     &DAGInstance{},
		retryPolicy:  &RetryPolicy{},
	}

	// Test the insert
	err := node.UpsertIntoDatabase(db)

	if err != nil {
		t.Fatalf("Expected no error on upsert, got %s", err)
	}

	// Make sure it has saved into the database
	nodes := []PersistentDAGNode{}
	err = db.NewSelect().
		Model(&nodes).
		Where("identifier = ?", nodeIdentifier).
		Scan(context.Background())

	if err != nil {
		t.Fatalf("Expected no error on select, got %s", err)
	}

	if len(nodes) != 1 {
		t.Fatalf("Expected 1 node, got %d", len(nodes))
	}

	if nodes[0].FunctionName != nodeInitialFunction {
		t.Fatalf("Expected function name to be '%s', got %s", nodeInitialFunction, nodes[0].FunctionName)
	}

	// Update the node
	node.functionName = nodeUpdatedFunction
	node.UpsertIntoDatabase(db)

	// Make sure the updated data has been saved into the database
	// Make sure it has saved into the database
	nodes = []PersistentDAGNode{}
	err = db.NewSelect().
		Model(&nodes).
		Where("identifier = ?", nodeIdentifier).
		Scan(context.Background())

	if err != nil {
		t.Fatalf("Expected no error on select, got %s", err)
	}

	if len(nodes) != 1 {
		t.Fatalf("Expected 1 node, got %d", len(nodes))
	}

	if nodes[0].FunctionName != nodeUpdatedFunction {
		t.Fatalf("Expected function name to be '%s', got %s", nodeUpdatedFunction, nodes[0].FunctionName)
	}
}
