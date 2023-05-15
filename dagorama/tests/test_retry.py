import pytest

from dagorama.retry import ExponentialRetry, RetryConfiguration, StaticRetry


@pytest.mark.parametrize(
    "policy",
    [
        StaticRetry(max_attempts=2, interval=1),
        ExponentialRetry(max_attempts=2, base_interval=2),
    ],
)
def test_convert_message(policy: RetryConfiguration):
    """
    Ensure we can serialize a policy into a protobuf message
    """
    policy.as_message()
