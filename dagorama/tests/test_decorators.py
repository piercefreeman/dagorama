from dagorama.decorators import dagorama
from dagorama.definition import DAGDefinition, resolve
from dagorama.runner import execute, CodeMismatchException
import pytest
from contextlib import contextmanager


class CustomNameDag(DAGDefinition):
    @dagorama(queue_name="test_queue")
    def entrypoint(self):
        return 10


class CustomTaintDag(DAGDefinition):
    @dagorama(taint_name="test_taint")
    def entrypoint(self):
        return 10


def test_custom_name(broker):
    dag = CustomNameDag()
    dag_result = dag()

    # Should run this queue
    execute(
        include_queues=["test_queue"],
        infinite_loop=False
    )
    assert resolve(dag, dag_result) == 10

    dag = CustomNameDag()
    dag_result = dag()

    # Should not run this queue
    execute(
        include_queues=["test_queue_2"],
        infinite_loop=False
    )
    assert resolve(dag, dag_result) == None

def test_taint_name(broker):
    dag = CustomTaintDag()
    dag_result = dag()

    # Should not run a tained queue by default
    execute(infinite_loop=False)
    assert resolve(dag, dag_result) == None

    # Require specific allowance
    execute(queue_tolerations=["test_taint"], infinite_loop=False)
    assert resolve(dag, dag_result) == 10
