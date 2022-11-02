package main

import (
	"sort"
	"testing"
)

func TestBroker(t *testing.T) {
	broker := NewBroker()
	instance := broker.NewInstance("1")

	// Entrypoint and one function
	entrypoint := instance.NewNode("A", "Entrypoint", "hash(1)", []byte{}, []*DAGNode{})
	instance.NewNode("B", "Secondary", "hash(2)", []byte{}, []*DAGNode{entrypoint})

	worker := &Worker{
		// All queues
		allowedQueues: []string{"Entrypoint", "Secondary"},
	}

	// Determine which one to prioritize first
	nextNode := broker.PopNextNode(worker)

	if nextNode == nil {
		t.Fatalf("Expected next node to be non-nil")
	}

	if nextNode.functionName != "Entrypoint" {
		t.Fatalf("Expected next node to be Entrypoint, got %s", nextNode.functionName)
	}

	// We shouldn't be able to pull anything out of the queue because we haven't
	// yet completed the next node
	if broker.PopNextNode(worker) != nil {
		t.Fatalf("Expected no jobs are ready yet.")
	}

	nextNode.ValueDidResolve([]byte{})

	nextNode = broker.PopNextNode(worker)

	if nextNode.functionName != "Secondary" {
		t.Fatalf("Expected next node to be Secondary, got %s", nextNode.functionName)
	}

	// Simulate the job completing
	nextNode.ValueDidResolve([]byte{})
}

func TestAllowedQueues(t *testing.T) {
	taintName := "TAINT_KEY"

	var tests = []struct {
		regularQueues, taintedQueues                   []string
		includeQueues, excludeQueues, queueTolerations []string
		expectedQueues                                 []string
	}{
		// No parameters should return everything
		{
			[]string{"A", "B", "C"},
			[]string{},
			[]string{},
			[]string{},
			[]string{},
			[]string{"A", "B", "C"},
		},
		// Tolerations should support the taint
		{
			[]string{"A", "B", "C"},
			[]string{"D"},
			[]string{},
			[]string{},
			[]string{taintName},
			[]string{"A", "B", "C", "D"},
		},
		// Inclusions should limit the full list
		{
			[]string{"A", "B", "C"},
			[]string{},
			[]string{"A"},
			[]string{},
			[]string{},
			[]string{"A"},
		},
		// Exclusions should limit the full list
		{
			[]string{"A", "B", "C"},
			[]string{},
			[]string{},
			[]string{"A"},
			[]string{},
			[]string{"B", "C"},
		},
	}

	for _, tt := range tests {
		broker := NewBroker()
		for _, queueName := range tt.regularQueues {
			broker.taskQueues[queueName] = NewHeapQueue()
		}
		for _, queueName := range tt.taintedQueues {
			queue := NewHeapQueue()
			queue.taint = taintName
			broker.taskQueues[queueName] = queue
		}

		// No previous information to cache
		worker := broker.NewWorker(
			tt.excludeQueues,
			tt.includeQueues,
			tt.queueTolerations,
		)

		allowedQueues := broker.getAllowedQueues(worker)

		// Align the two queues
		sort.Strings(allowedQueues)
		sort.Strings(tt.expectedQueues)

		if len(allowedQueues) != len(tt.expectedQueues) {
			t.Fatalf("Expected %d queues, got %d", len(tt.expectedQueues), len(allowedQueues))
		}

		for i := 0; i < len(allowedQueues); i++ {
			if allowedQueues[i] != tt.expectedQueues[i] {
				t.Fatalf("Expected queue index %d: %s, got %s", i, tt.expectedQueues[i], allowedQueues[i])
			}
		}
	}
}
