package main

import (
	"container/heap"
	"sync"
)

type QueuedJob struct {
	node *DAGNode

	// Lower denotes highest priority, since we increment by the creation order
	// of the parent DAGs. This is opposite of traditional p-queues where higher
	// ranked items are popped first.
	priority int64

	// The index of the item in the heap, used by the backing heap implementation.
	index int
}

type HeapQueue struct {
	/*
	 * min-heap of queue jobs
	 */

	// Both reads and writes have to be locked because we want to avoid a situation
	// where we are in the middle of inserting a new object that should be dequeued
	// over existing objects.
	accessLock sync.Mutex

	// If a taint is provided workers will need to explicitly tolerate it to run
	taint string

	heap Heap
}

func NewHeapQueue() *HeapQueue {
	newHeap := &HeapQueue{
		accessLock: sync.Mutex{},
		heap:       make([]*QueuedJob, 0),
	}
	heap.Init(&newHeap.heap)
	return newHeap
}

func (queue *HeapQueue) PushItem(node *DAGNode, priority int64) {
	// Nodes should only be added via the PushItem method
	item := &QueuedJob{
		node:     node,
		priority: priority,
		index:    -1,
	}

	queue.accessLock.Lock()
	defer queue.accessLock.Unlock()
	heap.Push(&queue.heap, item)
}

func (queue *HeapQueue) UpdateItem(item *QueuedJob, node *DAGNode, priority int64) {
	// Nodes should only be modified via the update method
	item.node = node
	item.priority = priority

	queue.accessLock.Lock()
	defer queue.accessLock.Unlock()
	heap.Fix(&queue.heap, item.index)
}

func (queue *HeapQueue) PopItem() *QueuedJob {
	queue.accessLock.Lock()
	defer queue.accessLock.Unlock()
	if len(queue.heap) == 0 {
		return nil
	}
	return heap.Pop(&queue.heap).(*QueuedJob)
}

func (queue *HeapQueue) PeekItem() *QueuedJob {
	queue.accessLock.Lock()
	defer queue.accessLock.Unlock()
	if len(queue.heap) == 0 {
		return nil
	}
	return queue.heap[0]
}

func (queue *HeapQueue) Length() int {
	return queue.heap.Len()
}

/*
 * HeapQueue implements heap.Interface.
 */

type Heap []*QueuedJob

func (h Heap) Len() int {
	// interface: heap
	return len(h)
}

func (h Heap) Less(i, j int) bool {
	// interface: heap
	// Heaps should have smallest priority at index 0
	return h[i].priority < h[j].priority
}

func (h Heap) Swap(i, j int) {
	// interface: heap
	h[i], h[j] = h[j], h[i]
	h[i].index = i
	h[j].index = j
}

func (h *Heap) Push(x any) {
	// interface: heap
	n := len(*h)
	item := x.(*QueuedJob)
	item.index = n
	*h = append(*h, item)
}

func (h *Heap) Pop() any {
	// interface: heap
	old := *h
	n := len(old)
	x := old[n-1]
	*h = old[0 : n-1]
	return x
}
