#! /bin/bash -e

# Ensure we are relative to the root directory for all commands
scriptPath=$(realpath $0)
rootDirectory="$(dirname "$scriptPath")"

# Golang generation
(
    cd $rootDirectory
    && mkdir -p broker/api \
    && protoc \
            -I./protos/dagorama/api \
            --go_out=./broker/api \
            --go_opt=paths=source_relative \
            --go-grpc_out=./broker/api \
            --go-grpc_opt=paths=source_relative \
            protos/dagorama/api/api.proto
)

# Python generation
# We explicitly set up the protos directory to mirror the structure of the python
# application so imports are relative to the root `dagorama` package
(
    cd $rootDirectory
    && mkdir -p dagorama/api \
    && touch dagorama/api/__init__.py \
    && poetry run python -m grpc_tools.protoc \
        -I./protos \
        --python_out=. \
        --grpc_python_out=. \
        --mypy_out=. \
        --mypy_grpc_out=. \
        protos/dagorama/api/api.proto

)
