from dagorama.runner import execute
from dagorama.definition import DAGDefinition, resolve
from dagorama.decorators import dagorama
from dagorama.serializer import register_definition

class CustomDAG(DAGDefinition):
    def __init__(self, number: int):
        self.number = number

    @dagorama()
    def entrypoint(self):
        return self.number


def test_runner_custom_init(broker):
    # Ensure that we are able to register a custom version
    # of the local DAGDefinition that we want to leverage

    dag = CustomDAG(number=10)
    dag_instance, dag_result = dag()

    register_definition(dag)
    execute(infinite_loop=False, catch_exceptions=False)

    assert resolve(dag_instance, dag_result) == 10
