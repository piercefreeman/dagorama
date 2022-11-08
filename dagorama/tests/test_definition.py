from dagorama.decorators import dagorama
from dagorama.definition import (DAGDefinition, DAGInstance,
                                 generate_instance_id)
from dagorama.runner import execute


class SampleDefinition(DAGDefinition):
    @dagorama().syncfn
    def entrypoint(self, *args, **kwargs):
        self.standard_function()
        assert isinstance(self, DAGInstance)

    def standard_function(self):
        assert isinstance(self, DAGInstance)
        return 1

def test_instance_injection(broker):
    """
    Ensure the instance is injected into the runtime

    """
    definition = SampleDefinition()
    instance = DAGInstance(generate_instance_id(), definition)
    instance.entrypoint()

    execute(infinite_loop=False, catch_exceptions=False)
