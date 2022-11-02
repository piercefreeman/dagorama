from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class DAGPromise:
    """
    A promise of a future DAG result. These promises values are not directly
    usable locally but can be passed to other DAG functions. The runner will ensure
    that they are fully realized before the DAG function is called.

    """
    identifier: UUID

    function_name: str | None = None

    arguments: Optional["DAGArguments"] = None
