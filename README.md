# dagorama (WIP)

Dagorama is an opinionated computation library for use in background processing. You can think of it as a hybrid between Celery, Airflow, and Dask.

Its primary design goal is to let users write chained data processing logic in vanilla Python and easily scale to external dedicated machines. In addition, it strives to provide:
- Easily interpretable control flow in vanilla Python, without having to learn a new language ORM
- Be written for modern Python, with support for IDE suggestions and mypy typehints
- Support dynamic logic, like branching if statements that condition a sub-tree execution on some runtime conditions
- Easily integrate with unit tests on one machine when testing
- Provide sensible defaults for background processing

## Quick Start

Let's take this trivial example, representative of wanting to perform a series of long running blocking tasks. Those tasks could be ML inference, image rendering, or data aggregation. In any case it needs to process for a few seconds before returning results. In particular we care about logic that fully utilizes the compute resources of the current process. This is unlike web requests, which have network induced latency and can be trivially parallelized through asyncio.

```python
from collections import Counter
from time import sleep, time

class MyTask:
    def entrypoint(self):
        results = [
            self.perform_work(i)
            for i in range(4)
        ]

        return self.rollup_statuses(results)

    def perform_work(self, identifier: int) -> int:
        sleep(2)
        return identifier // 2

    def rollup_statuses(self, responses: list[int]):
        return Counter([status for status in responses])

def main():
    start = time()
    task = MyTask()
    response = task.entrypoint()
    end = time()
    print(f"Response: {response} in {round(end-start, 2)}s")
    assert response == Counter({0: 2, 1: 2})

if __name__ == "__main__":
    main()
```

If you let this run, you should see an echoed counter after a bit of processing.

```bash
$ python samples/test1.py
Response: Counter({0: 2, 1: 2}) in 8.01s
```

This code also has valid typehints, so mypy is happy during the typehinting.

```bash
$ mypy samples/test1.py
Success: no issues found in 1 source file
```

Naturally we want to get our results as quickly as possible, while scaling to the available resources of the machine (or machines) that are in our compute cluster. This would _almost_ be a natural fit for something like a Celery queue - we'll spawn four separate jobs, one for each `perform_work` function. But how do we handle the aggregation stage? Do we block on a main process until it's done? How is state managed? What if the main process exits before we're completed, how can we pick up from where we were before?

This dependency chaining actually isn't great for queues. Instead you'll want something more akin to a computation graph or DAG, one that can condition later functions on the successful completion of previous functions. Here's how you would write the same thing in dagorama.

```python
from dagorama.decorators import dagorama
from dagorama.definition import DAGDefinition, resolve
from dagorama.runner import launch_workers
from dagorama_broker.launch import launch_broker

from collections import Counter
from time import sleep, time

class MyTask(DAGDefinition):
    @dagorama()
    def entrypoint(self):
        results = [
            self.perform_work(i)
            for i in range(4)
        ]

        return self.rollup_statuses(results)

    @dagorama()
    def perform_work(self, identifier: int) -> int:
        sleep(2)
        return identifier // 2

    @dagorama()
    def rollup_statuses(self, responses: list[int]):
        return Counter([status for status in responses])

def main():
    with launch_broker():
        start = time()
        task = MyTask()
        promise = task()

        with launch_workers(4):
            sleep(3)
        response = resolve(task, promise)
        end = time() 

    print(f"Response: {response} in {round(end-start, 2)}s")
    assert response == Counter({0: 2, 1: 2})

if __name__ == "__main__":
    main()
```

For the sake of fitting this logic in one script there are a few different things going on here.

1. We've wrapped each function in a `@dagorama` decorator. This decorator indicates that a function execution like `self.perform_work()` or `self.rollup_statuses()` should be performed on a separate worker node. This is akin to launching a new task within a conventional queue.
2. We launch the background broker with `with launch_broker()`. This will spawn a separate broker process that coordinates across multiple workers.
3. We launch the workers themselves with launch_workers. In this case we perform the work in separate processes. This could just as easily be on separate machines without changing the APIs or code.

Unlike before, we now complete in roughly the time for the primary work.

```
$ python run samples/test2.py
Response: Counter({0: 2, 1: 2}) in 3.03s
```

Mypy is similarly happy with our DAG definition.
```bash
$ mypy samples/test2.py
Success: no issues found in 1 source file
```

You'll notice the diff of the core MyTask class is very small:

```bash
$ diff samples/test1.py samples/test2.py 
1c1,2
< class MyTask:
---
> class MyTask(DAGDefinition):
>     @dagorama()
9a11
>     @dagorama()
13a16
>     @dagorama()
```

This is the core design goal of dagorama: write vanilla python and scale easily.

## API Notes

This section attempts to be the only section you'll need to know to use dagorama in day-to-day development, without starting to offroad.

Each group of logical code that you want to flow to one another should be contained in a class that inherits from `DAGDefinition`. You'll want this code to be deployed on each worker node so they're able to access the same core definition files. Docker is the preferred mechanism to ensure that the same code is mirrored on each device and computations will happen as expected. Each instance of a DAGDefinition created via `DAGDefinition()` wraps one execution of the functions within the DAG. If you're processing 5 separate input images, for example, you'll want to spawn 5 DAGDefinitions.

The dagorama broker will ensure that earlier DAG instances will complete before ones that are invoked later. The prioritization scheme is FIFO on the DAG instantiation order. This is useful in situations where you want to decrease the latency from start of processing to DAG completion for use in near-realtime logic.

Each function that you want to execute on a separate machine should be wrapped in a `@dagorama` decorator. Calls to this function will be added to the computational graph and distributed appropriately. Class functions that aren't decorated will be run inline to the current executor.

A `@dagorama` decorated function will _look_ like it returns the typehinted values to static analyzers like mypy. This allows you to write more interpretable code by passing around logical values. In reality, however, @dagorama functions will return a `DAGPromise` at runtime. This DAGPromise is meaningless - it doesn't have a value yet, since it hasn't yet been passed to a runner. These response values should only be passed to other `@dagorama` decorated functions as function arguments. When this is done workers will only execute that function once all its dependencies have been realized.

There are some situations where you want to limit the functions that will run on certain hardware. A common case is for ML functions to only be run on GPU accelerated devices. We follow the kubernetes model here by adding a taint to each function that shouldn't be deployed by default, like `@dagorama(taint_name="GPU")`. To pull from this queue workers will have to explicitly specify this taint, otherwise they won't pull from the backing queue.

To launch a worker function, install the python package in your virtualenv and run:

```
worker [--include-queue {queue}] [--exclude-queue {queue}] [--toleration {toleration}]
```

## Production Deployment (WIP)

Outside of local testing, you probably won't want to run the workers on your same machine. Instead you'll want to distribute them across multiple machines. In this setup we recommend:

- 1 Broker: Go executable running on a VM, kubernetes pod, or within docker. Backed by a persistent database to resume state in case of runtime interruptions.
- N Workers. The devices that perform the computation. Can be the same physical hardware configurations or different depending on usecase.
- M Spawners. The service that will first instantiate the DAG. This is typically the end application like a server backend.

## Typehinting

Dagorama should satisfy typehints the same way that normal functions do. In other words, you can treat the DAGPromise returned as a fulfilled value before passing it into other functions downstream of the main DAG.

## Development

Hacking on dagorama is encouraged. Here are some quick getting started steps.

### Installing Python Dependencies

We manage our dependencies with poetry. It's not strictly speaking necessary (the pyproject.toml should install via pip in a standard virtual environment) but.

If you don't already have Poetry, install it [here](https://python-poetry.org/docs/).

```
poetry install
```

### Installing gRPC

Clients communicate with the broker over gRPC. You'll need support to generate the protobuf files within Golang and Python.

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

### Unit Tests

If you want to run unit tests you'll also need `dagorama-broker` installed. This convenience package allows the tests to dynamically spawn and tear down a broker via pytest fixtures.

```
poetry run pip install -e ./dagorama-broker
```
