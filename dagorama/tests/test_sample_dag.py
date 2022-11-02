from dagorama.decorators import dagorama
from dagorama.definition import DAGDefinition, resolve
from dagorama.runner import execute


class CustomDag(DAGDefinition):
    """
    This DAG takes an input number and manipulates it arbitrarily.

    obj (1) --> obj2 (2) -->
                          obj3 (2) --> obj5 (4)
                                                 --> obj7 (9)
                          obj4 (3) --> obj6 (5)
    
    """
    @dagorama()
    def entrypoint(self, number: int):
        return self.linear_continue(number)

    @dagorama()
    def linear_continue(self, number: int):
        obj2 = number + 1
        results = [
            self.loop_map(obj2+i)
            for i in range(2)
        ]
        return self.loop_consolidate(results)

    @dagorama()
    def loop_map(self, number: int):
        # obj4 or obj5
        return number + 2

    @dagorama()
    def loop_consolidate(self, numbers: list[int]):
        # obj7
        return sum(numbers)


def test_sample_dag(broker):
    dag = CustomDag()
    dag_result = dag(1)

    execute(infinite_loop=False)

    assert resolve(dag, dag_result) == 9
