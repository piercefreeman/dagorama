from dataclasses import dataclass
from pickle import dumps, loads
from typing import Any

from dagorama.inspection import extract_promise_identifiers

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dagorama.models.promise import DAGPromise


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

    def to_server_bytes(self) -> bytes:
        # When serializing other DAGPromises, just include the identifiers since we don't need to
        # cache their parameters as well
        return dumps(
            DAGArguments(
                calltime_args=extract_promise_identifiers(self.calltime_args),
                calltime_kwargs=extract_promise_identifiers(self.calltime_kwargs),
            )
        )

    @classmethod
    def from_server_bytes(cls, b: bytes) -> "DAGArguments":
        return loads(b)
