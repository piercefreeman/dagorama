package main

import (
	"testing"
)

func TestBroker(t *testing.T) {
	broker := NewBroker()
	worker := &Worker{}
	instance := broker.NewInstance("1")

	// Entrypoint and one function
	entrypoint := instance.NewNode("A", "Entrypoint", []byte{}, []*DAGNode{})
	instance.NewNode("B", "Secondary", []byte{}, []*DAGNode{entrypoint})

	allQueues := []string{"A", "B"}

	// Determine which one to prioritize first
	nextNode := broker.PopNextNode(allQueues)

	if nextNode == nil {
		t.Fatalf("Expected next node to be non-nil")
	}

	if nextNode.functionName != "Entrypoint" {
		t.Fatalf("Expected next node to be Entrypoint, got %s", nextNode.functionName)
	}

	// We shouldn't be able to pull anything out of the queue because we haven't
	// yet completed the next node
	if broker.PopNextNode(allQueues) != nil {
		t.Fatalf("Expected no jobs are ready yet.")
	}

	nextNode.ValueDidResolve([]byte{})

	nextNode = broker.PopNextNode(allQueues)

	if nextNode.functionName != "Secondary" {
		t.Fatalf("Expected next node to be Secondary, got %s", nextNode.functionName)
	}

	// Simulate the job completing
	nextNode.ValueDidResolve([]byte{})
}
