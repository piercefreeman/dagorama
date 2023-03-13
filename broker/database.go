package main

import (
	"context"
	"database/sql"
	"fmt"
	"reflect"
	"strings"

	"github.com/uptrace/bun"
	"github.com/uptrace/bun/dialect/pgdialect"
	"github.com/uptrace/bun/driver/pgdriver"
)

// Used to specify custom field behavior for database tables
// This syntax sugar currently supports:
// - "auto-update", which will automatically update the given field on every DB upsert
const databaseMarkup = "dagorama_db"
const (
	MarkupAutoUpdate string = "auto-update"
)

type PersistentDAGInstance struct {
	bun.BaseModel `bun:"table:dag_instance"`

	Identifier string `bun:",pk"`
	Order      int

	nodeIdentifiers []string `bun:",array"`
}

type PersistentDAGNode struct {
	/*
	 * Mirror of the DAGNode struct, but with struct pointers
	 * converted to identifiers
	 * We avoid foreign keys since we typically can't guarantee an ordering
	 * of insertion for DAGNodes
	 * For more information on the values here see the DAGNode struct
	 */
	bun.BaseModel `bun:"table:dag_node"`

	// Priority queue (QueuedJob)
	Priority int64

	// DAGNode
	Identifier             string   `bun:",pk"`
	FunctionName           string   `dagorama_db:"auto-update"`
	QueueName              string   `dagorama_db:"auto-update"`
	TaintName              string   `dagorama_db:"auto-update"`
	FunctionHash           string   `dagorama_db:"auto-update"`
	Arguments              []byte   `dagorama_db:"auto-update"`
	SourceIdentifiers      []string `bun:",array" dagorama_db:"auto-update"`
	DestinationIdentifiers []string `bun:",array" dagorama_db:"auto-update"`
	ResolvedValue          []byte   `dagorama_db:"auto-update"`
	Completed              bool     `dagorama_db:"auto-update"`
	InstanceIdentifier     string   `dagorama_db:"auto-update"`

	RetryPolicyEnabled                bool `dagorama_db:"auto-update"`
	RetryPolicyCurrentAttempt         int  `dagorama_db:"auto-update"`
	RetryPolicyMaxAttempts            int  `dagorama_db:"auto-update"`
	RetryPolicyStaticInterval         int  `dagorama_db:"auto-update"`
	RetryPolicyExponentialBackoffBase int  `dagorama_db:"auto-update"`

	Failures []interface{} `bun:"type:jsonb" dagorama_db:"auto-update"`
}

func NewDatabase(
	host string,
	port int,
	username string,
	password string,
	database string,
) *bun.DB {
	dsn := fmt.Sprintf(
		"postgres://%s:%s@%s:%d/%s?sslmode=disable",
		username,
		password,
		host,
		port,
		database,
	)
	sqldb := sql.OpenDB(pgdriver.NewConnector(pgdriver.WithDSN(dsn)))

	db := bun.NewDB(sqldb, pgdialect.New())

	tables := []interface{}{
		(*PersistentDAGInstance)(nil),
		(*PersistentDAGNode)(nil),
	}

	// Create the tables on bootup if they don't exist yet
	for _, table := range tables {
		_, err := db.NewCreateTable().Model(table).IfNotExists().Exec(context.Background())
		if err != nil {
			panic(err)
		}
	}

	return db
}

func getAutoUpdatingFields(model interface{}) []string {
	/*
	 * Get the fields of a struct that are marked as auto-updating
	 * :param model: a pointer to a struct
	 */
	fields := make([]string, 0)
	t := reflect.TypeOf(model).Elem()

	for i := 0; i < t.NumField(); i++ {
		field := t.Field(i)

		if strings.Contains(field.Tag.Get(databaseMarkup), MarkupAutoUpdate) {
			fields = append(fields, field.Name)
		}
	}

	return fields
}

func upsertDatabaseObject(db *bun.DB, model interface{}) error {
	insertOperation := db.NewInsert().
		Model(model).
		On("CONFLICT (identifier) DO UPDATE")

	autoUpdatingFields := getAutoUpdatingFields(model)
	for _, field := range autoUpdatingFields {
		columnName := Underscore(field)
		insertOperation = insertOperation.Set(fmt.Sprintf("%s = EXCLUDED.%s", columnName, columnName))
	}

	_, err := insertOperation.Exec(context.Background())

	return err
}
