from inspect import getfullargspec

from dagorama.decorators import dagorama
from dagorama.definition import DAGDefinition, resolve
from dagorama.runner import execute_worker, execute_worker_async
from dagorama.serializer import register_definition


class CustomDAG(DAGDefinition):
    def __init__(self, number: int):
        self.number = number

    @dagorama().syncfn
    def entrypoint(self):
        return self.number


def test_runner_custom_init(broker):
    """
    Ensure that we are able to register a custom version
    of the local DAGDefinition that we want to leverage

    """

    dag = CustomDAG(number=10)
    dag_instance, dag_result = dag()

    register_definition(dag)
    execute_worker(infinite_loop=False, catch_exceptions=False)

    assert resolve(dag_instance, dag_result) == 10


def test_sync_async_parity():
    """
    Ensure the sync and async runner functions have the same API.

    """
    sync_spec = getfullargspec(execute_worker)
    async_spec = getfullargspec(execute_worker_async)
    assert sync_spec.args == async_spec.args
