from asyncio import run
from contextlib import contextmanager
from inspect import isawaitable
from multiprocessing import Process
from pickle import dumps, loads
from threading import Thread
from time import sleep
from traceback import format_exc

import grpc

import dagorama.api.api_pb2 as pb2
import dagorama.api.api_pb2_grpc as pb2_grpc
from dagorama.code_signature import calculate_function_hash
from dagorama.definition import dagorama_context
from dagorama.inspection import resolve_promises
from dagorama.models.arguments import DAGArguments
from dagorama.serializer import name_to_function


class CodeMismatchException(Exception):
    """
    If raised, the queued DAGNode and the current runner are using
    different versions of the function code.

    """
    pass


def schedule_ping(
    context: pb2_grpc.DagoramaStub,
    worker: pb2.WorkerMessage,
    interval: int = 30,
):
    """
    Send a ping to the server to keep the connection alive.
    """
    while True:
        context.Ping(worker)
        sleep(interval)


async def execute_async(
    exclude_queues: list | None = None,
    include_queues: list | None = None,
    queue_tolerations: list | None = None,
    infinite_loop: bool = True,
    catch_exceptions: bool = True,
):
    with dagorama_context() as context:
        worker = context.CreateWorker(
            pb2.WorkerConfigurationMessage(
                excludeQueues=exclude_queues or [],
                includeQueues=include_queues or [],
                queueTolerations=queue_tolerations or [],
            )
        )

        Thread(
            target=schedule_ping,
            args=(context, worker),
            # Stop the thread when the rest of the process finishes
            daemon=True,
        ).start()

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

            # Since this function was queued as part of the worker, we can assume that it will
            # be a wrapped @dagorama function - it will therefore be a standard callable without
            # async since it takes care of the client-side async logic internally.
            resolved_fn = name_to_function(next_item.functionName, next_item.instanceId)
            print("RESOLVED FN", resolved_fn)

            # Ensure that we have the correct local version of the function
            print("FOUND FN", resolved_fn)
            #print("COMPARE VALUES", calculate_function_hash(resolved_fn.original_fn), next_item.functionHash)
            if calculate_function_hash(resolved_fn.original_fn) != next_item.functionHash:
                raise CodeMismatchException()

            if catch_exceptions:
                try:
                    result = resolved_fn(*resolved_args, greedy_execution=True, **resolved_kwargs)
                    if isawaitable(result):
                        result = await result
                except Exception as e:
                    traceback = format_exc()
                    print("Exception encountered, reporting to broker:", e, traceback)
                    context.SubmitFailure(
                        pb2.WorkFailedMessage(
                            instanceId=next_item.instanceId,
                            nodeId=next_item.identifier,
                            workerId=worker.identifier,
                            traceback=traceback
                        )
                    )
                    continue
            else:
                result = resolved_fn(*resolved_args, greedy_execution=True, **resolved_kwargs)
                if isawaitable(result):
                    result = await result

            context.SubmitWork(
                pb2.WorkCompleteMessage(
                    instanceId=next_item.instanceId,
                    nodeId=next_item.identifier,
                    workerId=worker.identifier,
                    result=dumps(result),
                )
            )


def execute(
    exclude_queues: list | None = None,
    include_queues: list | None = None,
    queue_tolerations: list | None = None,
    infinite_loop: bool = True,
    catch_exceptions: bool = True,
):
    """
    Run the execute function in a synchronous manner. Assumes no runloop
    is already running or asyncio will raise an error.

    """
    return run(
        execute_async(
            exclude_queues=exclude_queues,
            include_queues=include_queues,
            queue_tolerations=queue_tolerations,
            infinite_loop=infinite_loop,
            catch_exceptions=catch_exceptions,
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
