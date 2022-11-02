from pickle import dumps, loads
from time import sleep
from contextlib import contextmanager

import grpc

import dagorama.api.api_pb2 as pb2
from dagorama.definition import dagorama_context
from dagorama.inspection import resolve_promises
from dagorama.models.arguments import DAGArguments
from dagorama.serializer import name_to_function
from multiprocessing import Process
from dagorama.code_signature import calculate_function_hash


def execute(
    exclude_queues: list | None = None,
    include_queues: list | None = None,
    queue_tolerations: list | None = None,
    infinite_loop: bool = True,
):
    with dagorama_context() as context:
        worker = context.CreateWorker(
            pb2.WorkerConfigurationMessage(
                excludeQueues=exclude_queues or [],
                includeQueues=include_queues or [],
                queueTolerations=queue_tolerations or [],
            )
        )

        while True:
            try:
                next_item = context.GetWork(worker)
            except grpc.RpcError as e:
                if e.details() == "no work available":
                    if not infinite_loop:
                        return
                    print("No work available, polling in 1s...")
                    sleep(1)
                    continue
                else:
                    raise

            arguments = DAGArguments.from_server_bytes(next_item.arguments)

            resolved_values = {
                source.identifier: loads(source.resolvedValue)
                for source in next_item.sources
            }

            # TODO: Add actual resolution
            print("------")
            print(next_item)
            print(arguments)
            print("resolved values", resolved_values)
            resolved_args = resolve_promises(arguments.calltime_args, resolved_values)
            resolved_kwargs = resolve_promises(arguments.calltime_kwargs, resolved_values)
            print("Resolved", resolved_args)
            print("Resolved", resolved_kwargs)

            resolved_fn = name_to_function(next_item.functionName, next_item.instanceId)

            # Ensure that we have the correct local version of the function
            print("FOUND FN", resolved_fn)
            print("COMPARE VALUES", calculate_function_hash(resolved_fn.original_fn), next_item.functionHash)
            if calculate_function_hash(resolved_fn.original_fn) != next_item.functionHash:
                raise ValueError(f"Local function code does not mirror remote spawned function code. This might be due to an outdated worker code deployment.")

            result = resolved_fn(*resolved_args, greedy_execution=True, **resolved_kwargs)
            print("RESULT", result)

            context.SubmitWork(
                pb2.WorkCompleteMessage(
                    instanceId=next_item.instanceId,
                    nodeId=next_item.identifier,
                    result=dumps(result),
                )
            )


@contextmanager
def launch_workers(n: int = 1):
    """
    Helper function to spawn multiple workers without having to launch
    them in separate shell sessions.

    Mostly intended for unit testing.

    """
    workers = [Process(target=execute) for _ in range(n)]
    for worker in workers:
        worker.start()

    yield

    for worker in workers:
        worker.terminate()
