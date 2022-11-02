from dataclasses import dataclass, asdict
from pickle import dumps, loads
from typing import Any
from uuid import UUID

@dataclass
class DAGArguments:
    """
    Local python arguments that a DAG function should be run with. These only have to be serialized
    in the python runtime and therefore contain a full copy of DAGPromises or other local elements.

    To be queued in the DAG, these objects need to be pickle serializable.

    """
    # Can include static values and other DAGPromises
    # Technically these should not be "Any" but should be any object type that
    # can be pickled / json encoded over the wire
    # We should add a validation step to make sure this is true at call time
    calltime_args: list["DAGPromise" | Any]
    calltime_kwargs: dict[str, "DAGPromise" | Any]

    def to_bytes(self) -> bytes:
        # TODO: When serializing other DAGPromises, just include the kwargs since we don't need to
        # cache their parameters as well
        return dumps(asdict(self))

    @classmethod
    def from_bytes(cls, b: bytes) -> "DAGArguments":
        return cls(**loads(b))


@dataclass
class DAGPromise:
    """
    A promise of a future DAG result. These promises values are not directly
    usable locally but can be passed to other DAG functions. The runner will ensure
    that they are fully realized before the DAG function is called.

    """
    identifier: UUID

    function_name: str

    arguments: DAGArguments
