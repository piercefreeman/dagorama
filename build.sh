
# Golang generation

(
    mkdir -p broker/api \
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
    mkdir -p dagorama/api \
    && poetry run python -m grpc_tools.protoc \
        -I./protos \
        --python_out=. \
        --grpc_python_out=. \
        protos/dagorama/api/api.proto

)
