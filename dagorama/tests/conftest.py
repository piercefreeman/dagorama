from os import environ

import pytest
from dagorama_broker.launch import launch_broker

from dagorama.settings import INLINE_ENVIRONMENT_FLAG


# Scope to the current unit test so we don't share results across tests
@pytest.fixture(scope="function")
def broker():
    with launch_broker():
        yield


@pytest.fixture()
def inline_dag():
    """
    When a pytest is run in this context, will run all dag instances inline
    within the test harness.

    """
    previous_value = environ.get(INLINE_ENVIRONMENT_FLAG, None)
    environ[INLINE_ENVIRONMENT_FLAG] = "true"
    try:
        yield
    finally:
        if previous_value is None:
            del environ[INLINE_ENVIRONMENT_FLAG]
        else:
            environ[INLINE_ENVIRONMENT_FLAG] = previous_value
