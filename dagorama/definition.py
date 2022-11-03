from abc import ABC, abstractmethod
from contextlib import contextmanager
from pickle import loads
from typing import cast
from uuid import UUID, uuid4

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


class DAGDefinition(ABC):
    def __init__(self):
        self.instance_id : UUID | None = None

    def __call__(self, *args, **kwargs) -> DAGPromise:
        if self.instance_id is not None:
            raise ValueError("Can only spawn one instance of a DAGDefinition")

        # Calling indicates that we should spin off a new DAG instance
        with dagorama_context() as context:
            self.instance_id = uuid4()
            context.CreateInstance(
                pb2.InstanceConfigurationMessage(
                    identifier=str(self.instance_id)
                )
            )

        result_promise = self.entrypoint(*args, **kwargs)
        # Cast as an actual result promise since this is what clients expect
        return cast(DAGPromise, result_promise)

    @abstractmethod
    def entrypoint(self, *args, **kwargs):
        pass


def resolve(dag: DAGDefinition, promise: DAGPromise):
    """
    Given a promise (typically of the initial_entrypoint), will recursively resolve
    promises in a return value chain.

    ie. Promise A -> Promise B -> Promise C will shortcut to Promise C, which will
    then return the true value.

    """
    # TODO: Remove the DAGDefinition, we should be able to infer
    # the instance ID from the promise

    with dagorama_context() as context:
        current_return_value = promise

        while isinstance(current_return_value, DAGPromise):
            node = context.GetNode(
                pb2.NodeRetrieveMessage(
                    instanceId=str(dag.instance_id),
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
