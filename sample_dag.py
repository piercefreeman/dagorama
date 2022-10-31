from dagorama.definition import DAGDefinition, dagorama, DAGPromise, RUN_LOOP_PROMISES
from dagorama.serializer import name_to_function
from itertools import chain
from typing import Any


class CustomDag(DAGDefinition):
    """
    This DAG takes an input number and manipulates it arbitrarily.

    obj (1) --> obj2 (2) -->
                          obj3 (2) --> obj5 (4)
                                                 --> obj7 (9)
                          obj4 (3) --> obj6 (5)
    
    """
    @dagorama()
    def entrypoint(self, number: int):
        return self.linear_continue(number)

    @dagorama()
    def linear_continue(self, number: int):
        obj2 = number + 1
        results = [
            self.loop_map(obj2+i)
            for i in range(2)
        ]
        return self.loop_consolidate(results)

    @dagorama()
    def loop_map(self, number: int):
        # obj4 or obj5
        return number + 2

    @dagorama()
    def loop_consolidate(self, numbers: list[int]):
        # obj7
        return sum(numbers)


if __name__ == "__main__":
    dag = CustomDag()
    dag_result = dag(1)

    # This should only be used in situations where blocking code on results is really
    # desirable, like in testing. In practice there might be errors with the DAG that
    # result in this infinite blocking so this is not recommended.
    # Add timeout to the resolution
    #await dag_result.resolve()

    path_to_dag = {}

    # result identifier -> result payload
    dependencies_met = {}

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

    while RUN_LOOP_PROMISES:
        # We'll need to find these functions in the runtime based on the function name
        next_item = RUN_LOOP_PROMISES.pop(0)

        unresolved = []

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

    unresolved = []
    final_result = resolve_promises(dag_result, unresolved)
    assert not unresolved
    assert final_result == 9

    print("DONE")
