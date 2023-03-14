package main

import (
	"sort"
	"testing"
	"time"
)

func TestBroker(t *testing.T) {
	broker := NewBroker(getTestMemoryConfig())
	instance := broker.NewInstance("1")

	// Entrypoint and one function
	entrypoint := instance.NewNode("A", "Entrypoint", "hash(1)", "queue_1", "", []byte{}, []*DAGNode{}, nil)
	instance.NewNode("B", "Secondary", "hash(2)", "queue_2", "", []byte{}, []*DAGNode{entrypoint}, nil)

	worker := &Worker{
		// All queues
		allowedQueues: []string{"queue_1", "queue_2"},
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

	nextNode.ExecutionDidResolve([]byte{})

	nextNode = broker.PopNextNode(worker)

	if nextNode.functionName != "Secondary" {
		t.Fatalf("Expected next node to be Secondary, got %s", nextNode.functionName)
	}

	// Simulate the job completing
	nextNode.ExecutionDidResolve([]byte{})
}

func TestPersistentBroker(t *testing.T) {
	clearTestDatabase()
	allowedQueues := []string{"queue_1", "queue_2"}

	// The broker should read the env params that are
	config := getTestPersistentConfig()

	// Lifecycle of the first broker
	{
		broker := NewBroker(config)
		instance := broker.NewInstance("1")

		// Entrypoint and one function
		entrypoint := instance.NewNode("A", "Entrypoint", "hash(1)", "queue_1", "", []byte{}, []*DAGNode{}, nil)
		instance.NewNode("B", "Secondary", "hash(2)", "queue_2", "", []byte{}, []*DAGNode{entrypoint}, nil)

		worker := &Worker{
			// All queues
			allowedQueues: allowedQueues,
		}

		// Determine which one to prioritize first
		nextNode := broker.PopNextNode(worker)

		if nextNode == nil {
			t.Fatalf("Expected next node to be non-nil")
		}

		if nextNode.functionName != "Entrypoint" {
			t.Fatalf("Expected next node to be Entrypoint, got %s", nextNode.functionName)
		}

		nextNode.ExecutionDidResolve([]byte{})
	}

	// Lifecycle of the second broker, should pick up where the first left off
	{
		// Restart the broker
		broker := NewBroker(config)

		worker := &Worker{
			// All queues
			allowedQueues: allowedQueues,
		}

		nextNode := broker.PopNextNode(worker)

		if nextNode.functionName != "Secondary" {
			t.Fatalf("Expected next node to be Secondary, got %s", nextNode.functionName)
		}

		// Simulate the job completing
		nextNode.ExecutionDidResolve([]byte{})
	}
}

func TestAllowedQueues(t *testing.T) {
	config := getTestMemoryConfig()
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
		broker := NewBroker(config)
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

func TestGarbageCollectWorkers(t *testing.T) {
	config := getTestMemoryConfig()
	broker := NewBroker(config)
	worker := broker.NewWorker([]string{}, []string{}, []string{})
	worker.lastPing = time.Now().Add(-1 * time.Hour).Unix()

	worker2 := broker.NewWorker([]string{}, []string{}, []string{})
	worker2.lastPing = time.Now().Add(-30 * time.Second).Unix()

	broker.GarbageCollectWorkersExecute()

	if !worker.invalidated {
		t.Fatalf("Expected worker to be garbage collected")
	}
	if worker2.invalidated {
		t.Fatalf("Expected worker2 to not be garbage collected")
	}
}

func TestQueueFutureScheduledExecute(t *testing.T) {
	config := getTestMemoryConfig()
	broker := NewBroker(config)
	worker := broker.NewWorker([]string{}, []string{}, []string{})

	// Create a node that is scheduled to run in the future
	instance := broker.NewInstance("1")

	// We should try again almost instantly (in 1 second)
	retryPolicy := NewStaticRetryPolicy(1, 1)
	instance.NewNode("A", "Entrypoint", "hash(1)", "queue_1", "", []byte{}, []*DAGNode{}, retryPolicy)

	// Dequeue from the main queue, should be the only one in the queue
	node := broker.PopNextNode(worker)

	// Indicate that the node has failed for some reason so it should be placed into the
	node.ExecutionDidFail("")

	if broker.futureScheduledNodes.Length() != 1 {
		t.Fatalf("Expected 1 future scheduled node, got %d", broker.futureScheduledNodes.Length())
	}

	if broker.taskQueues["queue_1"].Length() != 0 {
		t.Fatalf("Expected no length in queue_1, got %d", broker.taskQueues["queue_1"].Length())
	}

	// Wait for enough time to let our backoff expire
	time.Sleep(2 * time.Second)

	// Run the garbage collection, which should move the node to the main queue
	broker.QueueFutureScheduledExecute()

	// At this point it should be back in the main queue
	if broker.futureScheduledNodes.Length() != 0 {
		t.Fatalf("Expected no future scheduled nodes, got %d", broker.futureScheduledNodes.Length())
	}

	if broker.taskQueues["queue_1"].Length() != 1 {
		t.Fatalf("Expected node to be back in the queue, got %d", broker.taskQueues["queue_1"].Length())
	}
}

func TestQueueFutureScheduledPersistentExecute(t *testing.T) {
	clearTestDatabase()
	config := getTestPersistentConfig()

	{
		broker := NewBroker(config)
		worker := broker.NewWorker([]string{}, []string{}, []string{})

		// Create a node that is scheduled to run in the future
		instance := broker.NewInstance("1")

		// We should try again almost instantly (in 1 second)
		retryPolicy := NewStaticRetryPolicy(1, 1)
		instance.NewNode("A", "Entrypoint", "hash(1)", "queue_1", "", []byte{}, []*DAGNode{}, retryPolicy)

		// Dequeue from the main queue, should be the only one in the queue
		node := broker.PopNextNode(worker)

		// Indicate that the node has failed for some reason so it should be placed into the
		node.ExecutionDidFail("")

		if broker.futureScheduledNodes.Length() != 1 {
			t.Fatalf("Expected 1 future scheduled node, got %d", broker.futureScheduledNodes.Length())
		}

		if broker.taskQueues["queue_1"].Length() != 0 {
			t.Fatalf("Expected no length in queue_1, got %d", broker.taskQueues["queue_1"].Length())
		}
	}

	// Wait for enough time to let our backoff expire
	time.Sleep(2 * time.Second)

	{
		broker := NewBroker(config)

		// Run the garbage collection, which should move the node to the main queue
		broker.QueueFutureScheduledExecute()

		// At this point it should be back in the main queue
		if broker.futureScheduledNodes.Length() != 0 {
			t.Fatalf("Expected no future scheduled nodes, got %d", broker.futureScheduledNodes.Length())
		}

		if broker.taskQueues["queue_1"].Length() != 1 {
			t.Fatalf("Expected node to be back in the queue, got %d", broker.taskQueues["queue_1"].Length())
		}
	}
}
