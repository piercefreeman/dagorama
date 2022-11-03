import pytest
from dagorama_broker.launch import launch_broker

# Scope to the current unit test so we don't share results across tests
@pytest.fixture(scope="function")
def broker():
    with launch_broker():
        yield
