from typing import Any
from uuid import UUID

from dagorama.definition import dagorama_context
from dagorama.models.promise import DAGPromise
from dagorama.models.arguments import DAGArguments
from dagorama.serializer import name_to_function
import grpc
import dagorama.api.api_pb2 as pb2
import dagorama.api.api_pb2_grpc as pb2_grpc
from time import sleep
from dagorama.inspection import resolve_promises
from pickle import dumps, loads


def execute():
    with dagorama_context() as context:
        worker = context.CreateWorker(
            pb2.WorkerConfigurationMessage(
                excludeQueues=[],
                includeQueues=[],
                queueTolerations=[],
            )
        )

        while True:
            try:
                next_item = context.GetWork(worker)
            except grpc._channel._InactiveRpcError as e:
                if e.details() == "no work available":
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

            result = name_to_function(next_item.functionName, next_item.instanceId)(*resolved_args, greedy_execution=True, **resolved_kwargs)
            print("RESULT", result)

            context.SubmitWork(
                pb2.WorkCompleteMessage(
                    instanceId=next_item.instanceId,
                    nodeId=next_item.identifier,
                    result=dumps(result),
                )
            )
