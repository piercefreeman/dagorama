from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast
from uuid import UUID, uuid4

from dagorama.serializer import function_to_name


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
    calltime_args: list["DAGPromise" | Any]
    calltime_kwargs: dict[str, "DAGPromise" | Any]


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
    taint_name: list[str] = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    The actual return type of functions wrapped with @dagorama() will be a DAGPromise. This is not what we want during
    development because this is a typeless type. Instead, we want to program the graph as if all promises are instantly
    fulfilled and the values are passed downstream. A decorator gives us this behavior because we're only performing the
    wrap at runtime, so the type hinting will correctly recommend the full-fledged type.

    :param taint: When a taint is provided, workers will need to explicitly provide a toleration to execute. This is used
        in cases where there are specific compute resources that should own one phase of the pipeline.

    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        #@wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Can't be provided as an explicit keyword parameter because of a mypy constraint with P.kwargs having
            # to capture everything
            # https://github.com/python/typing/discussions/1191
            greedy_execution = kwargs.pop("greedy_execution", False)
            if greedy_execution:
                return func(*args, **kwargs)

            # Determine if first argument is the class itself - if so we
            # should ignore this within the DAG
            cache_args = list(args[1:]) if args and isinstance(args[0], DAGDefinition) else list(args)
            cached_kwargs = kwargs

            # This function will have a result
            # Queue in the DAG backend
            promise = DAGPromise(uuid4(), function_to_name(func), cache_args, cached_kwargs)
            RUN_LOOP_PROMISES.append(promise)
            #return func(*args, **kwargs)
            return cast(
                # Wrong cast of types but we want the static typechecker to believe that the function
                # is returning the actual value as specified by the client caller
                # https://docs.python.org/3/library/typing.html#typing.ParamSpec
                T, promise,
            )
        return wrapper
    return decorator
