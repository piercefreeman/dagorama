from collections.abc import Callable
from typing import ParamSpec, TypeVar, cast
from uuid import uuid4
from functools import wraps

import dagorama.api.api_pb2 as pb2
from dagorama.definition import DAGDefinition, dagorama_context
from dagorama.inspection import find_promises
from dagorama.models.arguments import DAGArguments
from dagorama.models.promise import DAGPromise
from dagorama.serializer import function_to_name
from dagorama.code_signature import calculate_function_hash

T = TypeVar('T')
P = ParamSpec('P')


def dagorama(
    queue_name: str | None = None,
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
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if not isinstance(args[0], DAGDefinition):
                raise ValueError("@dagorama can only wrap class methods")

            dag_definition : DAGDefinition = args[0]

            if dag_definition.instance_id is None:
                raise ValueError("DAGDefinition must be instantiated with call() before calling a method")

            # Can't be provided as an explicit keyword parameter because of a mypy constraint with P.kwargs having
            # to capture everything
            # https://github.com/python/typing/discussions/1191
            greedy_execution = kwargs.pop("greedy_execution", False)
            if greedy_execution:
                return func(*args, **kwargs)

            # Strip out the class definition when we store the arguments
            isolated_args = cast(list, args)[1:]

            # This function will have a result
            # Queue in the DAG backend
            promise = DAGPromise(
                uuid4(),
                function_to_name(func),
                DAGArguments(
                    isolated_args,
                    kwargs
                )
            )

            # Find the dependencies
            promise_dependencies = find_promises([isolated_args, kwargs])

            # Add to the remote runloop
            with dagorama_context() as context:
                context.CreateNode(
                    pb2.NodeConfigurationMessage(
                        identifier=str(promise.identifier),
                        functionName=cast(str, promise.function_name),
                        functionHash=calculate_function_hash(func),
                        taintName=taint_name or "",
                        queueName=queue_name or cast(str, promise.function_name),
                        arguments=(
                            cast(
                                # We know this is a valid argument object because we just set it
                                DAGArguments,
                                promise.arguments,
                            )
                            .to_server_bytes()
                        ),
                        sourceIds=[
                            str(dependency.identifier)
                            for dependency in promise_dependencies
                        ],
                        instanceId=str(dag_definition.instance_id),
                    )
                )

            return cast(
                # Wrong cast of types but we want the static typechecker to believe that the function
                # is returning the actual value as specified by the client caller
                # https://docs.python.org/3/library/typing.html#typing.ParamSpec
                T, promise,
            )
        wrapper.original_fn = func  # type: ignore
        return wrapper
    return decorator
