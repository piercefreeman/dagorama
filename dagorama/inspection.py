from typing import Any
from dagorama.models import DAGPromise

def find_promises(obj: Any) -> list[DAGPromise]:
    """
    Find all DAGPromises that are explicitly within the object, given standard python types. Note that this
    is just intended to find one layer of dependencies from obj. It does not recurse over additional dependencies
    that might be part of the found promises.

    """
    if isinstance(obj, dict):
        return [
            promise
            for value in obj.values()
            for promise in find_promises(value)
        ]
    elif isinstance(obj, (set, list, tuple)):
        return [
            promise
            for value in obj
            for promise in find_promises(value)
        ]

    # Otherwise we just have a raw value
    if isinstance(obj, DAGPromise):
        return [obj]
    else:
        return []
