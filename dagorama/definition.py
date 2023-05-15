from abc import ABC, abstractmethod
from contextlib import contextmanager, asynccontextmanager
from functools import wraps
from inspect import isawaitable, ismethod
from os import getenv
from pickle import loads
from typing import Any, Awaitable, cast
from uuid import UUID, uuid4

from grpc import aio as grpc_aio
import grpc
from asyncio import run

import dagorama.api.api_pb2 as pb2
import dagorama.api.api_pb2_grpc as pb2_grpc
from dagorama.models.promise import DAGPromise
from dagorama.settings import should_run_inline

LAUNCH_RETURN = tuple["DAGInstance", DAGPromise]


class DAGDefinition(ABC):
    def __call__(self, *args, **kwargs) -> LAUNCH_RETURN | Awaitable[LAUNCH_RETURN]:
        """
        If entrypoint is an async function, will return an awaitable value. If it is a sync
        function will return immediately.

        """
        # We don't have an instance ID yet for this invocation
        instance_id = generate_instance_id()
        instance = DAGInstance(instance_id, self)

        # We want to run the first function (entrypoint) as part of the
        # broader instance context
        result_promise = instance.entrypoint(*args, **kwargs)

        if isawaitable(result_promise):
            return self.call_async(instance, result_promise)
        return self.call_sync(instance, result_promise)

    def call_sync(self, instance: "DAGInstance", result_promise: DAGPromise):
        # Cast as an actual result promise since this is what clients expect
        result_promise = cast(DAGPromise, result_promise)

        return instance, result_promise

    async def call_async(self, instance: "DAGInstance", promise: Awaitable[DAGPromise]):
        result_promise = await promise

        # Cast as an actual result promise since this is what clients expect
        result_promise = cast(DAGPromise, result_promise)

        return instance, result_promise

    @abstractmethod
    def entrypoint(self, *args, **kwargs):
        pass


class DAGInstance:
    def __init__(self, instance_id: UUID, definition: DAGDefinition):
        self.instance_id = instance_id
        self.definition = definition

    def __getattr__(self, name: str) -> Any:
        value = getattr(self.definition, name)
        if callable(value):
            value = inject_instance(self)(value)
            return value
        return getattr(self.definition, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ["instance_id", "definition"]:
            return super().__setattr__(name, value)
        return setattr(self.definition, name, value)

    def __delattr__(self, name: str) -> None:
        if name in ["instance_id", "definition"]:
            return super().__delattr__(name)
        return delattr(self.definition, name)


@contextmanager
def dagorama_context():
    host = getenv("DAGORAMA_HOST", "localhost")
    port = getenv("DAGORAMA_PORT", "50051")

    # TODO: Get global context otherwise creates it
    with grpc.insecure_channel(f"{host}:{port}") as channel:
        yield pb2_grpc.DagoramaStub(channel)


@asynccontextmanager
async def dagorama_context_async():
    host = getenv("DAGORAMA_HOST", "localhost")
    port = getenv("DAGORAMA_PORT", "50051")

    # TODO: Get global context otherwise creates it
    async with grpc_aio.insecure_channel(f"{host}:{port}") as channel:
        yield pb2_grpc.DagoramaStub(channel)


def generate_instance_id() -> UUID:
    # If we are calling locally, create a fake identifier that doesn't require
    # a broker connection
    if should_run_inline():
        return f"local_{uuid4()}"

    # Calling indicates that we should spin off a new DAG instance
    with dagorama_context() as context:
        instance_id = uuid4()
        context.CreateInstance(
            pb2.InstanceConfigurationMessage(identifier=str(instance_id))
        )
    return instance_id


def inject_instance(instance):
    def decorator(func):
        # Deal with instance methods that inject their own "self" into the
        # function as part of the call execution
        if ismethod(func):
            func = getattr(func, "__func__")

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(instance, *args, **kwargs)

        else:
            # We only want to inject the instance into functions of this main DAG
            return func
        return wrapper

    return decorator


async def wait_for_resolution(
    context: pb2_grpc.DagoramaStub,
    instance_id: str,
    identifier: str
) -> pb2.NodeMessage:
    """
    This function will block until a DAGPromise result is ready.

    """
    request = pb2.CompleteSubscriptionRequest(instanceId=instance_id, identifier=identifier)

    # Wait for the first result to come back from the stream
    async for response in context.SubscribeResolution(request):
        return response


async def resolve_async(
    instance: DAGInstance,
    promise: DAGPromise,
    wait_for_results: bool = True,
):
    """
    Given a promise (typically of the initial_entrypoint), will recursively resolve
    promises in a return value chain. This allows you to recover a "final" value after
    a lot of intermediate processing stages.

    ie. Promise A -> Promise B -> Promise C will shortcut to Promise C, which will
    then return the true value.

    """
    async with dagorama_context_async() as context:
        current_return_value = promise

        while isinstance(current_return_value, DAGPromise):
            node = await context.GetNode(
                pb2.NodeRetrieveMessage(
                    instanceId=str(instance.instance_id),
                    identifier=str(current_return_value.identifier),
                )
            )

            if not len(node.resolvedValue):
                if not wait_for_results:
                    return None
                else:
                    node = await wait_for_resolution(
                        context=context,
                        instance_id=str(instance.instance_id),
                        identifier=str(current_return_value.identifier),
                    )

            resolved = loads(node.resolvedValue)
            if resolved is None:
                return None

            current_return_value = resolved

        return current_return_value

def resolve(
    instance: DAGInstance,
    promise: DAGPromise,
    wait_for_results: bool = True,
):
    return run(resolve_async(instance, promise, wait_for_results))
