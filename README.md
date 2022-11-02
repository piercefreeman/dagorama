# dagorama

Design Conditions
- Only @dagorama decorated functions can accept DAGPromises as call parameters, otherwise the promises don't take on any values during the current runtime session
- Porting code to a distributed deployment should be as easy as wrapping the class and individual functions


## Typehinting

```
poetry run mypy sample_dag.py
```

## Development

You'll need gRPC support for Golang and Python.

Golang quick start: https://grpc.io/docs/languages/go/quickstart/

```
go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.28
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.2
export PATH="$PATH:$(go env GOPATH)/bin"
```

When you update the grpc files, re-generate the client and server definition files via:

```
./build_protobuf.sh
```

If you want to run unit tests you'll:

```
poetry run pip install -e ./dagorama-broker
```
