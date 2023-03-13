package main

import (
	"context"
	"os"
	"testing"
)

func getTestConfig() *Config {
	os.Setenv("DAGORAMA_ENVIRONMENT", "development")
	os.Setenv("DAGORAMA_STORAGE_ENABLED", "true")
	os.Setenv("DAGORAMA_STORAGE_USERNAME", "dagorama")
	os.Setenv("DAGORAMA_STORAGE_DATABASE", "dagorama_test_db")

	return loadConfig()
}

func clearTestDatabase() {
	config := getTestConfig()

	db := NewDatabase(
		config.storage.host,
		config.storage.port,
		config.storage.username,
		config.storage.password,
		config.storage.database,
	)

	// Delete all rows from the tables
	db.NewDropTable().Model((*PersistentDAGNode)(nil)).Exec(context.Background())
	db.NewDropTable().Model((*PersistentDAGInstance)(nil)).Exec(context.Background())
}

func TestNewDatabase(t *testing.T) {
	clearTestDatabase()

	config := getTestConfig()

	db := NewDatabase(
		config.storage.host,
		config.storage.port,
		config.storage.username,
		config.storage.password,
		config.storage.database,
	)
	if db == nil {
		t.Fatalf("Expected database to be non-nil")
	}

	// Query the tables and make sure they exist
	_, err := db.NewSelect().Model((*PersistentDAGNode)(nil)).Count(context.Background())
	if err != nil {
		t.Fatalf("Expected no error, got %s", err)
	}

	_, err = db.NewSelect().Model((*PersistentDAGInstance)(nil)).Count(context.Background())
	if err != nil {
		t.Fatalf("Expected no error, got %s", err)
	}
}

func TestGetAutoUpdatingFields(t *testing.T) {
	obj := PersistentDAGNode{
		Priority: 1,
	}

	// Test a sample of fields known to contain the auto-updating flag
	updatingFields := getAutoUpdatingFields(&obj)
	knownFields := []string{"FunctionName", "QueueName", "TaintName"}

	foundFields := filterSlice(updatingFields, func(field string) bool {
		return contains(knownFields, field)
	})

	if len(foundFields) != len(knownFields) {
		t.Fatalf("Expected to find %d auto-updating fields, got %d", len(knownFields), len(foundFields))
	}
}
