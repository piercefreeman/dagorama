from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar, cast
from uuid import UUID, uuid4

from dagorama.serializer import function_to_name
import grpc
import dagorama.api.api_pb2 as pb2
import dagorama.api.api_pb2_grpc as pb2_grpc
from dagorama.inspection import find_promises
from dagorama.models.promise import DAGPromise
from dagorama.models.arguments import DAGArguments
from dagorama.definition import DAGDefinition, dagorama_context

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
            if not isinstance(args[0], DAGDefinition):
                raise ValueError("@dagorama can only wrap class methods")

            dag_definition : DAGDefinition = args[0]
            args = args[1:]

            if dag_definition.instance_id is None:
                raise ValueError("DAGDefinition must be instantiated with call() before calling a method")

            # Can't be provided as an explicit keyword parameter because of a mypy constraint with P.kwargs having
            # to capture everything
            # https://github.com/python/typing/discussions/1191
            greedy_execution = kwargs.pop("greedy_execution", False)
            if greedy_execution:
                return func(dag_definition, *args, **kwargs)

            # This function will have a result
            # Queue in the DAG backend
            promise = DAGPromise(
                uuid4(),
                function_to_name(func),
                DAGArguments(
                    args,
                    kwargs
                )
            )

            # Find the dependencies
            promise_dependencies = find_promises([args, kwargs])

            # Add to the remote runloop
            with dagorama_context() as context:
                context.CreateNode(
                    pb2.NodeConfigurationMessage(
                        identifier=str(promise.identifier),
                        functionName=promise.function_name,
                        arguments=promise.arguments.to_server_bytes(),
                        sourceIds=[
                            str(dependency.identifier)
                            for dependency in promise_dependencies
                        ],
                        instanceId=str(dag_definition.instance_id),
                    )
                )

            #RUN_LOOP_PROMISES.append(promise)

            #return func(*args, **kwargs)
            return cast(
                # Wrong cast of types but we want the static typechecker to believe that the function
                # is returning the actual value as specified by the client caller
                # https://docs.python.org/3/library/typing.html#typing.ParamSpec
                T, promise,
            )
        return wrapper
    return decorator
