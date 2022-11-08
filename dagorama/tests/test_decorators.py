from dagorama.decorators import dagorama
from dagorama.definition import DAGDefinition, resolve
from dagorama.runner import execute
from dagorama.retry import StaticRetry, ExponentialRetry
import pytest


class CustomNameDag(DAGDefinition):
    @dagorama(queue_name="test_queue")
    def entrypoint(self):
        return 10


class CustomAsyncDag(DAGDefinition):
    @dagorama(queue_name="test_queue")
    async def entrypoint(self):
        return 10


class CustomTaintDag(DAGDefinition):
    @dagorama(taint_name="test_taint")
    def entrypoint(self):
        return 10


class CustomStaticErroringDag(DAGDefinition):
    @dagorama(retry=StaticRetry(max_attempts=2, interval=1))
    def entrypoint(self):
        raise ValueError()


class CustomExponentialErroringDag(DAGDefinition):
    @dagorama(retry=ExponentialRetry(max_attempts=2, base_interval=2))
    def entrypoint(self):
        raise ValueError()


def test_custom_name(broker):
    dag = CustomNameDag()
    dag_instance, dag_result = dag()

    # Should run this queue
    execute(
        include_queues=["test_queue"],
        infinite_loop=False,
        catch_exceptions=False,
    )
    assert resolve(dag_instance, dag_result) == 10

    dag = CustomNameDag()
    dag_instance, dag_result = dag()

    # Should not run this queue
    execute(
        include_queues=["test_queue_2"],
        infinite_loop=False,
        catch_exceptions=False,
    )
    assert resolve(dag_instance, dag_result) == None


def test_async(broker):
    dag = CustomAsyncDag()
    dag_instance, dag_result = dag()

    # Should run this queue
    execute(
        include_queues=["test_queue"],
        infinite_loop=False,
        catch_exceptions=False,
    )
    assert resolve(dag_instance, dag_result) == 10


def test_taint_name(broker):
    dag = CustomTaintDag()
    dag_instance, dag_result = dag()

    # Should not run a tained queue by default
    execute(infinite_loop=False, catch_exceptions=False)
    assert resolve(dag_instance, dag_result) == None

    # Require specific allowance
    execute(queue_tolerations=["test_taint"], infinite_loop=False, catch_exceptions=False)
    assert resolve(dag_instance, dag_result) == 10


@pytest.mark.parametrize("dag_class", [CustomStaticErroringDag, CustomExponentialErroringDag])
def test_erroring_dags(broker, dag_class):
    dag = dag_class()
    dag_instance, dag_result = dag()

    # Should not run a tained queue by default
    execute(infinite_loop=False, catch_exceptions=True)
    assert resolve(dag_instance, dag_result) == None
