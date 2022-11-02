"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import collections.abc
import google.protobuf.descriptor
import google.protobuf.internal.containers
import google.protobuf.message
import sys

if sys.version_info >= (3, 8):
    import typing as typing_extensions
else:
    import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing_extensions.final
class WorkerConfigurationMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    EXCLUDEQUEUES_FIELD_NUMBER: builtins.int
    INCLUDEQUEUES_FIELD_NUMBER: builtins.int
    QUEUETOLERATIONS_FIELD_NUMBER: builtins.int
    @property
    def excludeQueues(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]: ...
    @property
    def includeQueues(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]: ...
    @property
    def queueTolerations(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]: ...
    def __init__(
        self,
        *,
        excludeQueues: collections.abc.Iterable[builtins.str] | None = ...,
        includeQueues: collections.abc.Iterable[builtins.str] | None = ...,
        queueTolerations: collections.abc.Iterable[builtins.str] | None = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["excludeQueues", b"excludeQueues", "includeQueues", b"includeQueues", "queueTolerations", b"queueTolerations"]) -> None: ...

global___WorkerConfigurationMessage = WorkerConfigurationMessage

@typing_extensions.final
class WorkerMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    IDENTIFIER_FIELD_NUMBER: builtins.int
    identifier: builtins.str
    def __init__(
        self,
        *,
        identifier: builtins.str = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["identifier", b"identifier"]) -> None: ...

global___WorkerMessage = WorkerMessage

@typing_extensions.final
class InstanceConfigurationMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    IDENTIFIER_FIELD_NUMBER: builtins.int
    identifier: builtins.str
    def __init__(
        self,
        *,
        identifier: builtins.str = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["identifier", b"identifier"]) -> None: ...

global___InstanceConfigurationMessage = InstanceConfigurationMessage

@typing_extensions.final
class InstanceMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    IDENTIFIER_FIELD_NUMBER: builtins.int
    identifier: builtins.str
    def __init__(
        self,
        *,
        identifier: builtins.str = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["identifier", b"identifier"]) -> None: ...

global___InstanceMessage = InstanceMessage

@typing_extensions.final
class NodeConfigurationMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    IDENTIFIER_FIELD_NUMBER: builtins.int
    FUNCTIONNAME_FIELD_NUMBER: builtins.int
    ARGUMENTS_FIELD_NUMBER: builtins.int
    SOURCEIDS_FIELD_NUMBER: builtins.int
    INSTANCEID_FIELD_NUMBER: builtins.int
    identifier: builtins.str
    functionName: builtins.str
    arguments: builtins.bytes
    @property
    def sourceIds(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[builtins.str]: ...
    instanceId: builtins.str
    def __init__(
        self,
        *,
        identifier: builtins.str = ...,
        functionName: builtins.str = ...,
        arguments: builtins.bytes = ...,
        sourceIds: collections.abc.Iterable[builtins.str] | None = ...,
        instanceId: builtins.str = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["arguments", b"arguments", "functionName", b"functionName", "identifier", b"identifier", "instanceId", b"instanceId", "sourceIds", b"sourceIds"]) -> None: ...

global___NodeConfigurationMessage = NodeConfigurationMessage

@typing_extensions.final
class NodeMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    IDENTIFIER_FIELD_NUMBER: builtins.int
    FUNCTIONNAME_FIELD_NUMBER: builtins.int
    ARGUMENTS_FIELD_NUMBER: builtins.int
    RESOLVEDVALUE_FIELD_NUMBER: builtins.int
    SOURCES_FIELD_NUMBER: builtins.int
    COMPLETED_FIELD_NUMBER: builtins.int
    INSTANCEID_FIELD_NUMBER: builtins.int
    identifier: builtins.str
    functionName: builtins.str
    arguments: builtins.bytes
    resolvedValue: builtins.bytes
    @property
    def sources(self) -> google.protobuf.internal.containers.RepeatedCompositeFieldContainer[global___NodeMessage]: ...
    completed: builtins.bool
    instanceId: builtins.str
    def __init__(
        self,
        *,
        identifier: builtins.str = ...,
        functionName: builtins.str = ...,
        arguments: builtins.bytes = ...,
        resolvedValue: builtins.bytes = ...,
        sources: collections.abc.Iterable[global___NodeMessage] | None = ...,
        completed: builtins.bool = ...,
        instanceId: builtins.str = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["arguments", b"arguments", "completed", b"completed", "functionName", b"functionName", "identifier", b"identifier", "instanceId", b"instanceId", "resolvedValue", b"resolvedValue", "sources", b"sources"]) -> None: ...

global___NodeMessage = NodeMessage

@typing_extensions.final
class PongMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    LASTPING_FIELD_NUMBER: builtins.int
    lastPing: builtins.int
    def __init__(
        self,
        *,
        lastPing: builtins.int = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["lastPing", b"lastPing"]) -> None: ...

global___PongMessage = PongMessage

@typing_extensions.final
class WorkCompleteMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    INSTANCEID_FIELD_NUMBER: builtins.int
    NODEID_FIELD_NUMBER: builtins.int
    RESULT_FIELD_NUMBER: builtins.int
    instanceId: builtins.str
    nodeId: builtins.str
    result: builtins.bytes
    def __init__(
        self,
        *,
        instanceId: builtins.str = ...,
        nodeId: builtins.str = ...,
        result: builtins.bytes = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["instanceId", b"instanceId", "nodeId", b"nodeId", "result", b"result"]) -> None: ...

global___WorkCompleteMessage = WorkCompleteMessage

@typing_extensions.final
class NodeRetrieveMessage(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    INSTANCEID_FIELD_NUMBER: builtins.int
    IDENTIFIER_FIELD_NUMBER: builtins.int
    instanceId: builtins.str
    identifier: builtins.str
    def __init__(
        self,
        *,
        instanceId: builtins.str = ...,
        identifier: builtins.str = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["identifier", b"identifier", "instanceId", b"instanceId"]) -> None: ...

global___NodeRetrieveMessage = NodeRetrieveMessage