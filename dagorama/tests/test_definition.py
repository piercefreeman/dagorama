import pytest

from dagorama.decorators import dagorama
from dagorama.definition import DAGDefinition, DAGInstance, generate_instance_id
from dagorama.runner import execute_worker


class SampleDefinition(DAGDefinition):
    @dagorama().syncfn
    def entrypoint(self, test_argument=None):
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

    execute_worker(infinite_loop=False, catch_exceptions=False)


def test_raises_invalid_arguments(broker):
    definition = SampleDefinition()

    # Normal invocations should succeed
    definition()

    # Make sure we mirror the error that a normal function throws if we
    # pass in an invalid argument
    with pytest.raises(TypeError):
        definition(fake_argument=1)
