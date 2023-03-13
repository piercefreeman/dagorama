package main

import "os"

func getTestPersistentConfig() *Config {
	os.Setenv("DAGORAMA_ENVIRONMENT", "development")
	os.Setenv("DAGORAMA_STORAGE_ENABLED", "true")
	os.Setenv("DAGORAMA_STORAGE_USERNAME", "dagorama")
	os.Setenv("DAGORAMA_STORAGE_DATABASE", "dagorama_test_db")

	return loadConfig()
}

func getTestMemoryConfig() *Config {
	os.Setenv("DAGORAMA_ENVIRONMENT", "development")
	os.Setenv("DAGORAMA_STORAGE_ENABLED", "false")

	return loadConfig()
}
