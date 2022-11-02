from typing import Any, Callable
from dagorama.models.promise import DAGPromise


def find_promises(obj: Any) -> list[DAGPromise]:
    """
    Find all DAGPromises that are explicitly within the object, given standard python types. Note that this
    is just intended to find one layer of dependencies from obj. It does not recurse over additional dependencies
    that might be part of the found promises.

    """
    found_promises = []

    def find_function(promise: DAGPromise) -> None:
        nonlocal found_promises
        found_promises.append(promise)
        return None

    map_promises(obj, find_function)
    return found_promises


def resolve_promises(obj: Any, resolved_values: dict[str, Any]) -> Any:
    """
    Recursively resolves promises in the given structures they appear

    """
    def resolution_function(promise: DAGPromise) -> Any:
        # We should have been provided a value for this dependency from the server
        if str(promise.identifier) not in resolved_values:
            raise ValueError("Unexpected promise in resolved value")
        return resolved_values[str(promise.identifier)]

    return map_promises(obj, resolution_function)


def extract_promise_identifiers(obj: Any) -> Any:
    """
    Instead of persisting full DAGPromise objects, we just want to persist the identifier. This
    identifier should already be mapped to a fully hydrated version of the promise in the server.

    """
    def simplify_function(promise: DAGPromise) -> DAGPromise:
        return DAGPromise(identifier=promise.identifier)

    return map_promises(obj, simplify_function)


def map_promises(obj: Any, identifier_mapper: Callable[[DAGPromise], Any]) -> Any:
    """
    Recursively map promises given a user-defined function. Used by other functions that want
    to iterative build up some logic in the full argument chain.

    Supports nested lists and dictionaries

    """
    # Deal with iterables
    if isinstance(obj, dict):
        return {
            key: map_promises(value, identifier_mapper)
            for key, value in obj.items()
        }
    elif isinstance(obj, set):
        return {
            map_promises(value, identifier_mapper)
            for value in obj
        }
    elif isinstance(obj, list):
        return [
            map_promises(value, identifier_mapper)
            for value in obj
        ]
    elif isinstance(obj, tuple):
        return tuple([
            map_promises(value, identifier_mapper)
            for value in obj
        ])

    # Otherwise we just have a raw value
    if isinstance(obj, DAGPromise):
        return identifier_mapper(obj)
    else:
        return obj
