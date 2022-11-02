import pytest
from dagorama_broker.launch import launch_broker

@pytest.fixture
def broker():
    with launch_broker():
        yield
