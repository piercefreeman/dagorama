package main

import "os"

func getTestPersistentConfig() *Config {
	os.Setenv("DAGORAMA_STORAGE_ENABLED", "true")
	os.Setenv("DAGORAMA_ENVIRONMENT", "development")

	// Read test-specific env variables
	testStorageHost := os.Getenv("DAGORAMA_TEST_STORAGE_HOST")
	testStoragePort := os.Getenv("DAGORAMA_TEST_STORAGE_PORT")
	testStorageUsername := os.Getenv("DAGORAMA_TEST_STORAGE_USERNAME")
	testStoragePassword := os.Getenv("DAGORAMA_TEST_STORAGE_PASSWORD")
	testStorageDatabase := os.Getenv("DAGORAMA_TEST_STORAGE_DATABASE")

	// Fallback to defaults
	testStorageUsername = TernaryIf(testStorageUsername == "", "dagorama", testStorageUsername)
	testStorageDatabase = TernaryIf(testStorageDatabase == "", "dagorama_test_db", testStorageDatabase)

	os.Setenv("DAGORAMA_STORAGE_HOST", testStorageHost)
	os.Setenv("DAGORAMA_STORAGE_PORT", testStoragePort)
	os.Setenv("DAGORAMA_STORAGE_USERNAME", testStorageUsername)
	os.Setenv("DAGORAMA_STORAGE_PASSWORD", testStoragePassword)
	os.Setenv("DAGORAMA_STORAGE_DATABASE", testStorageDatabase)

	return loadConfig()
}

func getTestMemoryConfig() *Config {
	os.Setenv("DAGORAMA_ENVIRONMENT", "development")
	os.Setenv("DAGORAMA_STORAGE_ENABLED", "false")

	return loadConfig()
}
