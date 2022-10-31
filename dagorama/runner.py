from typing import Any
from uuid import UUID

from dagorama.definition import RUN_LOOP_PROMISES, DAGPromise
from dagorama.serializer import name_to_function

# result identifier -> result payload
dependencies_met: dict[UUID, Any] = {}

# Recursively resolves promises in the given structures they appear
# Supports nested lists and dictionaries
# Will also deposit found nested promises into the identified_promises list
def resolve_promises(obj: Any, unresolved_promises: list[DAGPromise]) -> Any:
    # Deal with iterables
    if isinstance(obj, dict):
        return {
            key: resolve_promises(value, unresolved_promises)
            for key, value in obj.items()
        }
    elif isinstance(obj, set):
        return {
            resolve_promises(value, unresolved_promises)
            for value in obj
        }
    elif isinstance(obj, list):
        return [
            resolve_promises(value, unresolved_promises)
            for value in obj
        ]
    elif isinstance(obj, tuple):
        return tuple([
            resolve_promises(value, unresolved_promises)
            for value in obj
        ])

    # Otherwise we just have a raw value
    if isinstance(obj, DAGPromise):
        if obj.id in dependencies_met:
            cached_value = dependencies_met[obj.id]
            if isinstance(cached_value, DAGPromise):
                # We need to resolve this promise
                # TODO: Check for DAG legitimacy during build-up to avoid infinite loops
                return resolve_promises(cached_value, unresolved_promises)
            return cached_value
        else:
            unresolved_promises.append(obj)
            return obj
    else:
        return obj


def execute():
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
