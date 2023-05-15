import pytest

from dagorama.decorators import dagorama
from dagorama.definition import DAGDefinition, resolve, resolve_async
from dagorama.retry import ExponentialRetry, StaticRetry
from dagorama.runner import execute_worker, execute_worker_async


class CustomNameDag(DAGDefinition):
    @dagorama(queue_name="test_queue").syncfn
    def entrypoint(self):
        return 10


class CustomAsyncDag(DAGDefinition):
    @dagorama(queue_name="test_queue").asyncfn
    async def entrypoint(self):
        return 10


class CustomTaintDag(DAGDefinition):
    @dagorama(taint_name="test_taint").syncfn
    def entrypoint(self):
        return 10


class CustomStaticErroringDag(DAGDefinition):
    @dagorama(retry=StaticRetry(max_attempts=2, interval=1)).syncfn
    def entrypoint(self):
        raise ValueError()


class CustomExponentialErroringDag(DAGDefinition):
    @dagorama(retry=ExponentialRetry(max_attempts=2, base_interval=2)).syncfn
    def entrypoint(self):
        raise ValueError()


class ThirdPartyClass:
    def __init__(self):
        self.constant = 1

    def __call__(self):
        return self.constant

    def other_fn(self):
        return self.constant


class CustomThirdPartyDag(DAGDefinition):
    def __init__(self):
        self.third_party = ThirdPartyClass()
        # self.other_fn = self.third_party.other_fn

    @dagorama().syncfn
    def entrypoint(self):
        return self.third_party()
        # Isn't currently supported
        # self.other_fn()


def test_custom_name(broker):
    dag = CustomNameDag()
    dag_instance, dag_result = dag()

    # Should run this queue
    execute_worker(
        include_queues=["test_queue"],
        infinite_loop=False,
        catch_exceptions=False,
    )
    assert resolve(dag_instance, dag_result, wait_for_results=False) == 10

    dag = CustomNameDag()
    dag_instance, dag_result = dag()

    # Should not run this queue
    execute_worker(
        include_queues=["test_queue_2"],
        infinite_loop=False,
        catch_exceptions=False,
    )
    assert resolve(dag_instance, dag_result, wait_for_results=False) == None


@pytest.mark.asyncio
async def test_async(broker):
    dag = CustomAsyncDag()
    dag_instance, dag_result = await dag()

    # Should run this queue
    await execute_worker_async(
        include_queues=["test_queue"],
        infinite_loop=False,
        catch_exceptions=False,
    )
    assert (await resolve_async(dag_instance, dag_result, wait_for_results=False)) == 10


def test_taint_name(broker):
    dag = CustomTaintDag()
    dag_instance, dag_result = dag()

    # Should not run a tained queue by default
    execute_worker(infinite_loop=False, catch_exceptions=False)
    assert resolve(dag_instance, dag_result, wait_for_results=False) == None

    # Require specific allowance
    execute_worker(
        queue_tolerations=["test_taint"], infinite_loop=False, catch_exceptions=False
    )
    assert resolve(dag_instance, dag_result, wait_for_results=False) == 10


@pytest.mark.parametrize(
    "dag_class", [CustomStaticErroringDag, CustomExponentialErroringDag]
)
def test_erroring_dags(broker, dag_class):
    dag = dag_class()
    dag_instance, dag_result = dag()

    # Should not run a tained queue by default
    execute_worker(infinite_loop=False, catch_exceptions=True)
    assert resolve(dag_instance, dag_result, wait_for_results=False) == None


def test_custom_third_party_dag(broker):
    """
    Ensure that instance variables are callable
    """
    dag = CustomThirdPartyDag()
    dag_instance, dag_result = dag()

    execute_worker(infinite_loop=False, catch_exceptions=True)
    assert resolve(dag_instance, dag_result, wait_for_results=False) == 1
