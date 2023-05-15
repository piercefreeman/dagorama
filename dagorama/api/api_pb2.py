# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: dagorama/api/api.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x16\x64\x61gorama/api/api.proto\x12\x04main"d\n\x1aWorkerConfigurationMessage\x12\x15\n\rexcludeQueues\x18\x01 \x03(\t\x12\x15\n\rincludeQueues\x18\x02 \x03(\t\x12\x18\n\x10queueTolerations\x18\x03 \x03(\t"#\n\rWorkerMessage\x12\x12\n\nidentifier\x18\x01 \x01(\t"2\n\x1cInstanceConfigurationMessage\x12\x12\n\nidentifier\x18\x01 \x01(\t"%\n\x0fInstanceMessage\x12\x12\n\nidentifier\x18\x01 \x01(\t"\xdd\x01\n\x18NodeConfigurationMessage\x12\x12\n\nidentifier\x18\x01 \x01(\t\x12\x14\n\x0c\x66unctionName\x18\x02 \x01(\t\x12\x14\n\x0c\x66unctionHash\x18\x03 \x01(\t\x12\x11\n\tqueueName\x18\x04 \x01(\t\x12\x11\n\ttaintName\x18\x05 \x01(\t\x12\x11\n\targuments\x18\x06 \x01(\x0c\x12\x11\n\tsourceIds\x18\x07 \x03(\t\x12\x12\n\ninstanceId\x18\x08 \x01(\t\x12!\n\x05retry\x18\t \x01(\x0b\x32\x12.main.RetryMessage"\xe8\x01\n\x0bNodeMessage\x12\x12\n\nidentifier\x18\x01 \x01(\t\x12\x14\n\x0c\x66unctionName\x18\x02 \x01(\t\x12\x14\n\x0c\x66unctionHash\x18\x03 \x01(\t\x12\x11\n\tqueueName\x18\x04 \x01(\t\x12\x11\n\ttaintName\x18\x05 \x01(\t\x12\x11\n\targuments\x18\x06 \x01(\x0c\x12\x15\n\rresolvedValue\x18\x07 \x01(\x0c\x12"\n\x07sources\x18\x08 \x03(\x0b\x32\x11.main.NodeMessage\x12\x11\n\tcompleted\x18\t \x01(\x08\x12\x12\n\ninstanceId\x18\n \x01(\t"T\n\x0cRetryMessage\x12\x13\n\x0bmaxAttempts\x18\x01 \x01(\x05\x12\x16\n\x0estaticInterval\x18\x02 \x01(\x05\x12\x17\n\x0f\x65xponentialBase\x18\x03 \x01(\x05"\x1f\n\x0bPongMessage\x12\x10\n\x08lastPing\x18\x02 \x01(\x03"[\n\x13WorkCompleteMessage\x12\x12\n\ninstanceId\x18\x01 \x01(\t\x12\x0e\n\x06nodeId\x18\x02 \x01(\t\x12\x10\n\x08workerId\x18\x03 \x01(\t\x12\x0e\n\x06result\x18\x04 \x01(\x0c"\\\n\x11WorkFailedMessage\x12\x12\n\ninstanceId\x18\x01 \x01(\t\x12\x0e\n\x06nodeId\x18\x02 \x01(\t\x12\x10\n\x08workerId\x18\x03 \x01(\t\x12\x11\n\ttraceback\x18\x04 \x01(\t"=\n\x13NodeRetrieveMessage\x12\x12\n\ninstanceId\x18\x01 \x01(\t\x12\x12\n\nidentifier\x18\x02 \x01(\t2\x84\x04\n\x08\x44\x61gorama\x12G\n\x0c\x43reateWorker\x12 .main.WorkerConfigurationMessage\x1a\x13.main.WorkerMessage"\x00\x12M\n\x0e\x43reateInstance\x12".main.InstanceConfigurationMessage\x1a\x15.main.InstanceMessage"\x00\x12\x41\n\nCreateNode\x12\x1e.main.NodeConfigurationMessage\x1a\x11.main.NodeMessage"\x00\x12\x30\n\x04Ping\x12\x13.main.WorkerMessage\x1a\x11.main.PongMessage"\x00\x12\x39\n\x07GetNode\x12\x19.main.NodeRetrieveMessage\x1a\x11.main.NodeMessage"\x00\x12\x33\n\x07GetWork\x12\x13.main.WorkerMessage\x1a\x11.main.NodeMessage"\x00\x12<\n\nSubmitWork\x12\x19.main.WorkCompleteMessage\x1a\x11.main.NodeMessage"\x00\x12=\n\rSubmitFailure\x12\x17.main.WorkFailedMessage\x1a\x11.main.NodeMessage"\x00\x42\x0eZ\x0c\x64\x61gorama/apib\x06proto3'
)

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "dagorama.api.api_pb2", globals())
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    DESCRIPTOR._serialized_options = b"Z\014dagorama/api"
    _WORKERCONFIGURATIONMESSAGE._serialized_start = 32
    _WORKERCONFIGURATIONMESSAGE._serialized_end = 132
    _WORKERMESSAGE._serialized_start = 134
    _WORKERMESSAGE._serialized_end = 169
    _INSTANCECONFIGURATIONMESSAGE._serialized_start = 171
    _INSTANCECONFIGURATIONMESSAGE._serialized_end = 221
    _INSTANCEMESSAGE._serialized_start = 223
    _INSTANCEMESSAGE._serialized_end = 260
    _NODECONFIGURATIONMESSAGE._serialized_start = 263
    _NODECONFIGURATIONMESSAGE._serialized_end = 484
    _NODEMESSAGE._serialized_start = 487
    _NODEMESSAGE._serialized_end = 719
    _RETRYMESSAGE._serialized_start = 721
    _RETRYMESSAGE._serialized_end = 805
    _PONGMESSAGE._serialized_start = 807
    _PONGMESSAGE._serialized_end = 838
    _WORKCOMPLETEMESSAGE._serialized_start = 840
    _WORKCOMPLETEMESSAGE._serialized_end = 931
    _WORKFAILEDMESSAGE._serialized_start = 933
    _WORKFAILEDMESSAGE._serialized_end = 1025
    _NODERETRIEVEMESSAGE._serialized_start = 1027
    _NODERETRIEVEMESSAGE._serialized_end = 1088
    _DAGORAMA._serialized_start = 1091
    _DAGORAMA._serialized_end = 1607
# @@protoc_insertion_point(module_scope)
