from abc import ABC, abstractmethod
from functools import wraps
from dataclasses import dataclass
from uuid import UUID, uuid4
from collections.abc import Callable
from typing import TypeVar, ParamSpec, cast
from typing import Any

@dataclass
class DAGPromise:
    """
    A promise of a future DAG result
    """
    id: UUID

    function_name: str

    # Can include static values and other DAGPromises
    # Technically these should not be "Any" but should be any object type that
    # can be pickled / json encoded over the wire
    # We should add a validation step to make sure this is true at call time
    calltime_args: list["DAGPromise" | Any] = None
    calltime_kwargs: dict[str, "DAGPromise" | Any] = None


RUN_LOOP_PROMISES: list[DAGPromise] = []


class DAGDefinition(ABC):
    def __call__(self, *args, **kwargs) -> DAGPromise:
        result_promise = self.entrypoint(*args, **kwargs)
        # Cast as an actual result promise since this is what clients expect
        return cast(DAGPromise, result_promise)

    @abstractmethod
    def entrypoint(self, *args, **kwargs):
        pass


T = TypeVar('T')
P = ParamSpec('P')


def dagorama(
    bind_runners: list[str] = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    The actual return type of functions wrapped with @dagorama() will be a DAGPromise. This is not what we want during
    development because this is a typeless type. Instead, we want to program the graph as if all promises are instantly
    fulfilled and the values are passed downstream. A decorator gives us this behavior because we're only performing the
    wrap at runtime, so the type hinting will correctly recommend the full-fledged type.

    :param bind_runners: Specified runner names that are allowed to perform this function. This is
        used in cases where there are specific compute resources that should own one phase of the pipeline.

    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        #@wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Determine if first argument is the class itself - if so we
            # should ignore this within the DAG
            if args and isinstance(args[0], DAGDefinition):
                args = args[1:]

            # This function will have a result
            # Queue in the DAG backend
            promise = DAGPromise(uuid4(), func.__name__, args, kwargs)
            RUN_LOOP_PROMISES.append(promise)
            #return func(*args, **kwargs)
            return cast(
                # Wrong cast of types but we want the static typechecker to believe that the function
                # is returning the actual value as specified by the client caller
                # https://docs.python.org/3/library/typing.html#typing.ParamSpec
                T, promise,
            )
        wrapper.original_fn = func
        return wrapper
    return decorator
