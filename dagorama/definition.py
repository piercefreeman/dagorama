from abc import ABC, abstractmethod
from contextlib import contextmanager
from pickle import loads
from typing import cast, Any
from uuid import UUID, uuid4
from inspect import isfunction, ismethod
from functools import wraps

import grpc

import dagorama.api.api_pb2 as pb2
import dagorama.api.api_pb2_grpc as pb2_grpc
from dagorama.models.promise import DAGPromise

RUN_LOOP_PROMISES: list[DAGPromise] = []


@contextmanager
def dagorama_context():
    # TODO: Get global context otherwise creates it

    with grpc.insecure_channel("localhost:50051") as channel:
        yield pb2_grpc.DagoramaStub(channel)


def generate_instance_id() -> UUID:
    # Calling indicates that we should spin off a new DAG instance
    with dagorama_context() as context:
        instance_id = uuid4()
        context.CreateInstance(
            pb2.InstanceConfigurationMessage(
                identifier=str(instance_id)
            )
        )
    return instance_id


class DAGDefinition(ABC):
    def __call__(self, *args, **kwargs) -> tuple["DAGInstance", DAGPromise]:
        # We don't have an instance ID yet for this invocation
        instance_id = generate_instance_id()
        instance = DAGInstance(instance_id, self)

        # We want to run the first function (entrypoint) as part of the
        # broader instance context
        result_promise = instance.entrypoint(*args, **kwargs)

        # Cast as an actual result promise since this is what clients expect
        result_promise = cast(DAGPromise, result_promise)

        return instance, result_promise

    @abstractmethod
    def entrypoint(self, *args, **kwargs):
        pass


def inject_instance(instance):
    def decorator(func):
        # Deal with instance methods that inject their own "self" into the
        # function as part of the call execution
        if ismethod(func):
            func = getattr(func, "__func__")

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(instance, *args, **kwargs)
        return wrapper
    return decorator


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


def resolve(instance: DAGInstance, promise: DAGPromise):
    """
    Given a promise (typically of the initial_entrypoint), will recursively resolve
    promises in a return value chain.

    ie. Promise A -> Promise B -> Promise C will shortcut to Promise C, which will
    then return the true value.

    """
    with dagorama_context() as context:
        current_return_value = promise

        while isinstance(current_return_value, DAGPromise):
            node = context.GetNode(
                pb2.NodeRetrieveMessage(
                    instanceId=str(instance.instance_id),
                    identifier=str(current_return_value.identifier),
                )
            )

            if not len(node.resolvedValue):
                return None

            resolved = loads(node.resolvedValue)
            if resolved is None:
                return None

            current_return_value = resolved

        return current_return_value
