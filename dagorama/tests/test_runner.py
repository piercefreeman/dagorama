from dagorama.runner import execute, execute_async
from dagorama.definition import DAGDefinition, resolve
from dagorama.decorators import dagorama
from dagorama.serializer import register_definition
from inspect import getfullargspec

class CustomDAG(DAGDefinition):
    def __init__(self, number: int):
        self.number = number

    @dagorama()
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
    execute(infinite_loop=False, catch_exceptions=False)

    assert resolve(dag_instance, dag_result) == 10


def test_sync_async_parity():
    """
    Ensure the sync and async runner functions have the same API.

    """
    sync_spec = getfullargspec(execute)
    async_spec = getfullargspec(execute_async)
    assert sync_spec.args == async_spec.args
