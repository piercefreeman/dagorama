from abc import ABC, abstractmethod
from functools import wraps
from dataclasses import dataclass
from uuid import UUID, uuid4
from collections.abc import Callable
from typing import TypeVar, ParamSpec, cast

class DAGDefinition(ABC):
    def __call__(self, *args, **kwargs):
        self.entrypoint(*args, **kwargs)
        # TODO: Return a promise of the entire dag being completed
        return None

    @abstractmethod
    def entrypoint(self, *args, **kwargs):
        pass

@dataclass
class DAGPromise:
    """
    A promise of a future DAG result
    """
    id: UUID


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
            print("Call wrapper", args, kwargs)
            # This function will have a result
            # TODO: Queue in the DAG backend
            #return func(*args, **kwargs)
            return cast(
                # Wrong cast of types but we want the static typechecker to believe that the function
                # is returning the actual value as specified by the client caller
                # https://docs.python.org/3/library/typing.html#typing.ParamSpec
                T, DAGPromise(uuid4())
            )
        return wrapper
    return decorator
