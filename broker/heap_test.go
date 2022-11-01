package main

import (
	"testing"
)

func TestHigherPriorityFirst(t *testing.T) {
	queue := NewHeapQueue()
	queue.PushItem(&DAGNode{functionName: "A"}, 10)
	queue.PushItem(&DAGNode{functionName: "B"}, 1)

	if len(queue.heap) != 2 {
		t.Errorf("Expected heap to have 2 elements, got %d", len(queue.heap))
	}

	if queue.heap[0].priority != 1 {
		t.Errorf("Expected first element to have priority 1, got %d", queue.heap[0].priority)
	}

	if queue.heap[1].priority != 10 {
		t.Errorf("Expected second element to have priority 10, got %d", queue.heap[1].priority)
	}

	dequeuedItem := queue.PopItem()
	if dequeuedItem.functionName != "B" {
		t.Errorf("Expected first element to be B, got %s", dequeuedItem.functionName)
	}
}
