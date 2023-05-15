from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps
from inspect import iscoroutinefunction
from logging import warning
from typing import Any, ParamSpec, TypeVar, cast
from uuid import uuid4

import dagorama.api.api_pb2 as pb2
from dagorama.code_signature import calculate_function_hash
from dagorama.definition import DAGDefinition, DAGInstance, dagorama_context
from dagorama.inspection import find_promises, verify_function_call
from dagorama.logging import get_logger
from dagorama.models.arguments import DAGArguments
from dagorama.models.promise import DAGPromise
from dagorama.retry import RetryConfiguration
from dagorama.serializer import function_to_name
from dagorama.settings import should_run_inline

T = TypeVar("T")
P = ParamSpec("P")


@dataclass
class WrapperResults:
    result: Any | None = None
    promise: DAGPromise | None = None


class dagorama:
    """
    The dagorama decorator wraps a distinct piece of work that should be separately
    queued in a background function. It is polymorphic with regard to async or sync functions and there
    are a few different ways to execute it.

    The first and easiest is to use a vanilla `@dagorama` decorator. This will detect if the underlying
    wrapped function is async or sync and will queue it accordingly. This isn't strictly recommended
    because it results in a vaguer typing signature since we can't statically determine whether
    we are dealing with an async or sync function [1].

    ```
    @dagorama()
    def my_function():
        pass
    ```

    For more specific typing, call the `dagorama` decorator with either `dagorama.syncfn` or `dagorama.asyncfn`:

    ```
    @dagorama().syncfn
    def my_function():
        pass

    @dagorama().asyncfn
    async def my_function():
        pass
    ```

    The actual return type of functions wrapped with @dagorama() will be a DAGPromise. This is not what we want during
    development because this is a typeless type. Instead, we want to program the graph as if all promises are instantly
    fulfilled and the values are passed downstream.

    [1] The issue here is one of parity. We want the input type signature to match the output type signature explicitly
    to guarantee that we're correctly mocking the DAGPromise output. Sync functions result in a `T` output type whereas
    async functions result in an `Awaitable[T]` output. It's not currently possible to have the specification of one input
    type result in the determination of the output type.

    :param taint: When a taint is provided, workers will need to explicitly provide a toleration to execute. This is used
        in cases where there are specific compute resources that should own one phase of the pipeline.

    """

    def __init__(
        self,
        queue_name: str | None = None,
        taint_name: str | None = None,
        retry: RetryConfiguration | None = None,
    ):
        self.queue_name = queue_name
        self.taint_name = taint_name
        self.retry = retry

    def __call__(self, func: Callable[P, T | Awaitable[T]]):
        warning(
            "Unknown type signature with `@dagorama` decorator. Use `@dagorama.sync` or `@dagorama.async` for explicit typing."
        )
        if iscoroutinefunction(func):
            return self.syncfn(func)
        else:
            return self.asyncfn(func)

    @property
    def syncfn(self):
        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            if iscoroutinefunction(func):
                raise ValueError("dagorama().async is required for async functions")

            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                payload = self.common_wrapper(func, *args, **kwargs)
                if payload.result:
                    return payload.result

                # Wrong cast of types but we want the static typechecker to believe that the function
                # is returning the actual value as specified by the client caller
                # https://docs.python.org/3/library/typing.html#typing.ParamSpec
                return cast(T, payload.promise)

            wrapper.original_fn = func  # type: ignore
            return wrapper

        return decorator

    @property
    def asyncfn(self):
        def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
            if not iscoroutinefunction(func):
                raise ValueError("dagorama.sync() is required for sync functions")

            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                payload = self.common_wrapper(func, *args, **kwargs)
                if payload.result:
                    return await payload.result

                return cast(
                    T,
                    payload.promise,
                )

            wrapper.original_fn = func  # type: ignore
            return wrapper

        return decorator

    def common_wrapper(self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs):
        # Ignore the first argument, which will be the passed through class definition
        if isinstance(args[0], DAGDefinition):
            raise ValueError(
                "A @dagorama() function should only be called as part of a DAGInstance"
            )

        # We should instead be called on an instance of the DAG, which is injected into
        # the second argument slot
        if isinstance(args[0], DAGInstance):
            instance = args[0]
        else:
            raise ValueError("@dagorama can only be called on DAGInstances")

        # Check that the function support the given runtime parameters
        verify_function_call(func, args, kwargs)

        # Can't be provided as an explicit keyword parameter because of a mypy constraint with P.kwargs having
        # to capture everything
        # https://github.com/python/typing/discussions/1191
        greedy_execution = kwargs.pop("greedy_execution", False) or should_run_inline()
        if greedy_execution:
            result = func(*args, **kwargs)
            return WrapperResults(result=result)

        # Strip out the class definition when we store the arguments
        isolated_args = cast(list, args)[1:]

        # This function will have a result
        # Queue in the DAG backend
        promise = DAGPromise(
            uuid4(), function_to_name(func), DAGArguments(isolated_args, kwargs)
        )

        # Find the dependencies
        promise_dependencies = find_promises([isolated_args, kwargs])

        # Add to the remote runloop
        with dagorama_context() as context:
            get_logger().debug(
                f"Creating node {promise.identifier} for {promise.function_name}"
            )
            context.CreateNode(
                pb2.NodeConfigurationMessage(
                    identifier=str(promise.identifier),
                    functionName=cast(str, promise.function_name),
                    functionHash=calculate_function_hash(func),
                    taintName=self.taint_name or "",
                    queueName=self.queue_name or cast(str, promise.function_name),
                    arguments=(
                        cast(
                            # We know this is a valid argument object because we just set it
                            DAGArguments,
                            promise.arguments,
                        ).to_server_bytes()
                    ),
                    sourceIds=[
                        str(dependency.identifier)
                        for dependency in promise_dependencies
                    ],
                    instanceId=str(instance.instance_id),
                    retry=self.retry.as_message() if self.retry is not None else None,
                )
            )

        return WrapperResults(promise=promise)
