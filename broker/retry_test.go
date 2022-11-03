package main

import (
	"testing"
)

func TestRetryStatic(t *testing.T) {
	policy := NewStaticRetryPolicy(1, 3)

	if ms := policy.getWaitIntervalMilliseconds(); ms != 1000 {
		t.Fatalf("Expected 1s, got %d", ms)
	}

	if ms := policy.getWaitIntervalMilliseconds(); ms != 1000 {
		t.Fatalf("Expected 1s, got %d", ms)
	}

	if ms := policy.getWaitIntervalMilliseconds(); ms != 1000 {
		t.Fatalf("Expected 1s, got %d", ms)
	}

	if ms := policy.getWaitIntervalMilliseconds(); ms != -1 {
		t.Fatalf("Expected -1, got %d", ms)
	}
}

func TestRetryBackoff(t *testing.T) {
	policy := NewExponentialRetryPolicy(3)

	// 2^0 = 1
	if ms := policy.getWaitIntervalMilliseconds(); !(ms >= 1000 && ms <= 2000) {
		t.Fatalf("Expected [1000,2000]ms, got %d", ms)
	}

	// 2^1 = 2
	if ms := policy.getWaitIntervalMilliseconds(); !(ms >= 2000 && ms <= 3000) {
		t.Fatalf("Expected [2000,3000]ms, got %d", ms)
	}

	// 2^2 = 4
	if ms := policy.getWaitIntervalMilliseconds(); !(ms >= 4000 && ms <= 5000) {
		t.Fatalf("Expected [4000,5000]ms, got %d", ms)
	}

	// We now should exhaust the retry logic
	if ms := policy.getWaitIntervalMilliseconds(); ms != -1 {
		t.Fatalf("Expected -1, got %d", ms)
	}
}
