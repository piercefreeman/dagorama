package main

import (
	"math"
	"math/rand"
)

type RetryPolicy struct {
	/*
	 * Policy to retry failedRequests
	 */
	currentAttempt int
	maxAttempts    int

	// Seconds
	staticInterval int

	// Base of the exponent (x^t) where t is the times that we
	// have previously tried the backoff
	// If specified will also add a jitter of [0, 1]sec to avoid situations
	// where multiple clients are sending requests in synchronized waves
	exponentialBackoffBase int
}

func NewStaticRetryPolicy(staticInterval int, maxAttempts int) *RetryPolicy {
	return &RetryPolicy{
		maxAttempts:            maxAttempts,
		staticInterval:         staticInterval,
		exponentialBackoffBase: 0,
		currentAttempt:         0,
	}
}

func NewExponentialRetryPolicy(exponentialBackoffBase int, maxAttempts int) *RetryPolicy {
	return &RetryPolicy{
		maxAttempts:            maxAttempts,
		exponentialBackoffBase: exponentialBackoffBase,
		staticInterval:         0,
		currentAttempt:         0,
	}
}

func (policy *RetryPolicy) getWaitIntervalMilliseconds() int {
	/*
	 * Gets the wait interval since the last attempt
	 * Also increments the current attempt counter. For use specifically when determining
	 * the next phase that we should wait.
	 *
	 * -1 if we shouldn't retry
	 */
	if policy.currentAttempt >= policy.maxAttempts {
		return -1
	}

	defer func() { policy.currentAttempt += 1 }()

	if policy.staticInterval > 0 {
		return policy.staticInterval * 1000
	} else if policy.exponentialBackoffBase > 0 {
		jitter := rand.Float64() * 1000
		waitSeconds := math.Pow(float64(policy.exponentialBackoffBase), float64(policy.currentAttempt))
		return int(math.Round((waitSeconds * 1000) + jitter))
	}

	return -1
}
