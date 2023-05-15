"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import abc
import collections.abc
import dagorama.api.api_pb2
import grpc

class DagoramaStub:
    def __init__(self, channel: grpc.Channel) -> None: ...
    CreateWorker: grpc.UnaryUnaryMultiCallable[
        dagorama.api.api_pb2.WorkerConfigurationMessage,
        dagorama.api.api_pb2.WorkerMessage,
    ]
    CreateInstance: grpc.UnaryUnaryMultiCallable[
        dagorama.api.api_pb2.InstanceConfigurationMessage,
        dagorama.api.api_pb2.InstanceMessage,
    ]
    CreateNode: grpc.UnaryUnaryMultiCallable[
        dagorama.api.api_pb2.NodeConfigurationMessage,
        dagorama.api.api_pb2.NodeMessage,
    ]
    Ping: grpc.UnaryUnaryMultiCallable[
        dagorama.api.api_pb2.WorkerMessage,
        dagorama.api.api_pb2.PongMessage,
    ]
    SubscribeResolution: grpc.UnaryStreamMultiCallable[
        dagorama.api.api_pb2.CompleteSubscriptionRequest,
        dagorama.api.api_pb2.NodeMessage,
    ]
    GetNode: grpc.UnaryUnaryMultiCallable[
        dagorama.api.api_pb2.NodeRetrieveMessage,
        dagorama.api.api_pb2.NodeMessage,
    ]
    GetWork: grpc.UnaryUnaryMultiCallable[
        dagorama.api.api_pb2.WorkerMessage,
        dagorama.api.api_pb2.NodeMessage,
    ]
    SubmitWork: grpc.UnaryUnaryMultiCallable[
        dagorama.api.api_pb2.WorkCompleteMessage,
        dagorama.api.api_pb2.NodeMessage,
    ]
    SubmitFailure: grpc.UnaryUnaryMultiCallable[
        dagorama.api.api_pb2.WorkFailedMessage,
        dagorama.api.api_pb2.NodeMessage,
    ]

class DagoramaServicer(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def CreateWorker(
        self,
        request: dagorama.api.api_pb2.WorkerConfigurationMessage,
        context: grpc.ServicerContext,
    ) -> dagorama.api.api_pb2.WorkerMessage: ...
    @abc.abstractmethod
    def CreateInstance(
        self,
        request: dagorama.api.api_pb2.InstanceConfigurationMessage,
        context: grpc.ServicerContext,
    ) -> dagorama.api.api_pb2.InstanceMessage: ...
    @abc.abstractmethod
    def CreateNode(
        self,
        request: dagorama.api.api_pb2.NodeConfigurationMessage,
        context: grpc.ServicerContext,
    ) -> dagorama.api.api_pb2.NodeMessage: ...
    @abc.abstractmethod
    def Ping(
        self,
        request: dagorama.api.api_pb2.WorkerMessage,
        context: grpc.ServicerContext,
    ) -> dagorama.api.api_pb2.PongMessage: ...
    @abc.abstractmethod
    def SubscribeResolution(
        self,
        request: dagorama.api.api_pb2.CompleteSubscriptionRequest,
        context: grpc.ServicerContext,
    ) -> collections.abc.Iterator[dagorama.api.api_pb2.NodeMessage]: ...
    @abc.abstractmethod
    def GetNode(
        self,
        request: dagorama.api.api_pb2.NodeRetrieveMessage,
        context: grpc.ServicerContext,
    ) -> dagorama.api.api_pb2.NodeMessage: ...
    @abc.abstractmethod
    def GetWork(
        self,
        request: dagorama.api.api_pb2.WorkerMessage,
        context: grpc.ServicerContext,
    ) -> dagorama.api.api_pb2.NodeMessage: ...
    @abc.abstractmethod
    def SubmitWork(
        self,
        request: dagorama.api.api_pb2.WorkCompleteMessage,
        context: grpc.ServicerContext,
    ) -> dagorama.api.api_pb2.NodeMessage: ...
    @abc.abstractmethod
    def SubmitFailure(
        self,
        request: dagorama.api.api_pb2.WorkFailedMessage,
        context: grpc.ServicerContext,
    ) -> dagorama.api.api_pb2.NodeMessage: ...

def add_DagoramaServicer_to_server(servicer: DagoramaServicer, server: grpc.Server) -> None: ...
