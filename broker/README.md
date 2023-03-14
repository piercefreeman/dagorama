# dagorama-broker

## Environment Variables

`DAGORAMA_ENVIRONMENT` - If set to "development", will activate verbose logging. Otherwise (by default) will log only warnings and above.

`DAGORAMA_HOST` - Hostname of the broker. Defaults to `localhost`.

`DAGORAMA_PORT` - Port of the broker. Defaults to `50051`.

`DAGORAMA_STORAGE_ENABLED` - `true` or `false`. If `true`, will persist data to a Postgres database. If `false` will only use an in-memory heap. Defaults to `false`.

`DAGORAMA_STORAGE_HOST` - Hostname of the Postgres database.

`DAGORAMA_STORAGE_PORT` - Port of the Postgres database.

`DAGORAMA_STORAGE_USER` - Username of the Postgres database.

`DAGORAMA_STORAGE_PASSWORD` - Password of the Postgres database.

`DAGORAMA_STORAGE_DATABASE` - Name of the Postgres database.

## Persistence

The broker can either be backed by a Postgres database or an in-memory data store. The `memory` mode is useful for testing and development, but is not recommended for production use. When the broker restarts in memory mode, all computation graph state will be lost.

Note that even when backed by a database, we still rely on an in-memory heap for low-latency querying of data. The persistence layer is merely used as a store to synchronize data between broker spawns. This means that your broker will still need as much memory available as you expect the maximum size of your job queue will grow to become.

## Testing

To run unit tests, you'll want a postgres database operational locally. By default the broker unit tests will interface with a `dagorama` user with the `dagorama_test_db` database. You can create these with the following commands:

```
createuser dagorama
createdb -O dagorama dagorama_test_db
```

```
go test .
```
