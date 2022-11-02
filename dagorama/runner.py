from typing import Any
from uuid import UUID

from dagorama.definition import dagorama_context
from dagorama.models import DAGPromise, DAGArguments
from dagorama.serializer import name_to_function
import grpc
import dagorama.api.api_pb2 as pb2
import dagorama.api.api_pb2_grpc as pb2_grpc
from time import sleep
from dagorama.inspection import find_promises
from pickle import dumps, loads

# result identifier -> result payload
dependencies_met: dict[UUID, Any] = {}


# Recursively resolves promises in the given structures they appear
# Supports nested lists and dictionaries
# Will also deposit found nested promises into the identified_promises list
def resolve_promises(obj: Any, resolved_values: dict[str, Any]) -> Any:
    # NOTE: Correctly cast the serialized pickle to DAGPromise
    if isinstance(obj, dict) and "function_name" in obj:
        # We should have been provided a value for this dependency from the server
        if str(obj["identifier"]) not in resolved_values:
            raise ValueError("Unexpected promise in resolved value")
        return resolved_values[str(obj["identifier"])]

    # Deal with iterables
    if isinstance(obj, dict):
        return {
            key: resolve_promises(value, resolved_values)
            for key, value in obj.items()
        }
    elif isinstance(obj, set):
        return {
            resolve_promises(value, resolved_values)
            for value in obj
        }
    elif isinstance(obj, list):
        return [
            resolve_promises(value, resolved_values)
            for value in obj
        ]
    elif isinstance(obj, tuple):
        return tuple([
            resolve_promises(value, resolved_values)
            for value in obj
        ])

    # Otherwise we just have a raw value
    # NOTE: Correctly cast the serialized pickle to DAGPromise
    #if isinstance(obj, DAGPromise):
    if hasattr(obj, "function_name"):
        # We should have been provided a value for this dependency from the server
        if obj.identifier not in resolved_values:
            raise ValueError("Unexpected promise in resolved value")
        return resolved_values[str(obj["identifier"])]
    else:
        return obj


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

            arguments = DAGArguments.from_bytes(next_item.arguments)

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
    return



    while RUN_LOOP_PROMISES:
        # We'll need to find these functions in the runtime based on the function name
        next_item = RUN_LOOP_PROMISES.pop(0)

        unresolved: list[DAGPromise] = []

        resolved_args = [
            resolve_promises(argument, unresolved)
            for argument in next_item.calltime_args
        ]
        resolved_kwargs = {
            key: resolve_promises(argument, unresolved)
            for key, argument in next_item.calltime_kwargs.items()
        }

        if unresolved:
            # Re-queue to the end
            RUN_LOOP_PROMISES.append(next_item)
            continue

        # Run the defined function
        # For now we hard-code the DAG but this should be dynamically instantiated as needed
        result = name_to_function(next_item.function_name)(*resolved_args, greedy_execution=True, **resolved_kwargs)
        dependencies_met[next_item.id] = result
