package main

func filterSlice[T any](s []T, f func(T) bool) []T {
	filtered := make([]T, 0)

	for _, value := range s {
		if f(value) {
			filtered = append(filtered, value)
		}
	}

	return filtered
}

func contains[T comparable](s []T, e T) bool {
	for _, v := range s {
		if v == e {
			return true
		}
	}
	return false
}

func TernaryIf[T any](condition bool, trueValue T, falseValue T) T {
	if condition {
		return trueValue
	}
	return falseValue
}
