from abc import ABC, abstractmethod
from dataclasses import dataclass

import dagorama.api.api_pb2 as pb2


class RetryConfiguration(ABC):
    @abstractmethod
    def as_message(self) -> pb2.RetryMessage:
        """
        Map the retry configuration to a protobuf message

        """
        pass


@dataclass
class StaticRetry(RetryConfiguration):
    """
    Constant retry uses a static amount of seconds, up until
    the max attempt count.

    """
    max_attempts: int
    interval: int

    def as_message(self):
        return pb2.RetryMessage(
            maxAttempts=self.max_attempts,
            staticInterval=self.interval,
        )

@dataclass
class ExponentialRetry(RetryConfiguration):
    """
    Expontential retry uses the formula base_interval^t where t is the current
    attempt of the retry. When `max_attempts` has occurred will result in a permanent failure.

    """
    max_attempts: int
    base_interval: int = 2

    def as_message(self):
        return pb2.RetryMessage(
            maxAttempts=self.max_attempts,
            exponentialBase=self.base_interval,
        )
