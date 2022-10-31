from dagorama.definition import DAGDefinition, dagorama


class CustomDag(DAGDefinition):
    """
    This DAG takes an input number and manipulates it arbitrarily.

    obj (1) --> obj2 (2) -->
                          obj3 (2) --> obj5 (4)
                                                 --> obj7 (9)
                          obj4 (3) --> obj6 (5)
    
    """
    def entrypoint(self, number: int):
        self.linear_continue(number)

    @dagorama()
    def linear_continue(self, number: int):
        obj2 = number + 1
        results = [
            self.loop_map(obj2+i)
            for i in range(2)
        ]
        self.loop_consolidate(results)

    @dagorama()
    def loop_map(self, number: int):
        # obj4 or obj5
        return number + 2

    @dagorama()
    def loop_consolidate(self, numbers: list[int]):
        # obj7
        return sum(numbers)


dag = CustomDag()
dag_result = dag(1)

# This should only be used in situations where blocking code on results is really
# desirable, like in testing. In practice there might be errors with the DAG that
# result in this infinite blocking so this is not recommended.
# Add timeout to the resolution
#await dag_result.resolve()

print("Finished")
