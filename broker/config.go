package main

import (
	"fmt"
	"log"
	"os"
	"strconv"
)

type Config struct {
	host        string
	port        int
	environment string

	storage StorageConfig
}

type StorageConfig struct {
	enabled  bool
	username string
	password string
	host     string
	port     int
	database string
}

func getEnvValue(key string, defaultValue string, required bool) string {
	value := os.Getenv(key)
	if value == "" && defaultValue == "" && required {
		log.Fatal(fmt.Errorf("Required environment variable not set: `%s`\n", key))
	}
	if value == "" {
		return defaultValue
	}
	return value
}

func loadConfig() *Config {
	/*
	 * Loads the config from the environment and sets
	 * local defaults
	 */
	environment := getEnvValue("DAGORAMA_ENVIRONMENT", "production", false)
	host := getEnvValue("DAGORAMA_HOST", "localhost", true)
	port := getEnvValue("DAGORAMA_PORT", "50051", true)

	storageEnabled := getEnvValue("DAGORAMA_STORAGE_ENABLED", "false", true)
	storageUsername := getEnvValue("DAGORAMA_STORAGE_USERNAME", "dagorama", true)
	storagePassword := getEnvValue("DAGORAMA_STORAGE_PASSWORD", "", false)
	storageHost := getEnvValue("DAGORAMA_STORAGE_HOST", "localhost", true)
	storagePort := getEnvValue("DAGORAMA_STORAGE_PORT", "5432", true)
	storageDatabase := getEnvValue("DAGORAMA_STORAGE_DATABASE", "dagorama_db", true)

	// Type conversions
	portInt, err := strconv.Atoi(port)
	if err != nil {
		log.Fatal(fmt.Errorf("Integer port parsing failed: %w", err))
	}

	storagePortInt, err := strconv.Atoi(storagePort)
	if err != nil {
		log.Fatal(fmt.Errorf("Integer storage port parsing failed: %w", err))
	}

	storageEnabledBool, err := strconv.ParseBool(storageEnabled)
	if err != nil {
		log.Fatal(fmt.Errorf("Boolean storage enabled parsing failed: %w", err))
	}

	return &Config{
		host:        host,
		port:        portInt,
		environment: environment,
		storage: StorageConfig{
			enabled:  storageEnabledBool,
			username: storageUsername,
			password: storagePassword,
			host:     storageHost,
			port:     storagePortInt,
			database: storageDatabase,
		},
	}
}
