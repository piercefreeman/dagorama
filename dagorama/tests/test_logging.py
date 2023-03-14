from os import environ
from dagorama.logging import get_logger
import pytest


# Logs should occur in ascending order
LOG_PRIORITY = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@pytest.mark.parametrize("log_level", LOG_PRIORITY)
def test_logger(log_level: str, capsys):
    """
    Ensure we can get a logger from the global context
    """
    environ["DAGORAMA_LOG_LEVEL"] = log_level

    logger = get_logger()
    logger.debug("DEBUG_LOG")
    logger.info("INFO_LOG")
    logger.warning("WARNING_LOG")
    logger.error("ERROR_LOG")
    logger.critical("CRITICAL_LOG")

    captured_logs = capsys.readouterr()

    # Ensure that everything >= the specified log level is within the log
    all_logs = captured_logs.out + "\n" + captured_logs.err

    current_log_level = LOG_PRIORITY.index(log_level)

    for level in LOG_PRIORITY[:current_log_level]:
        assert f"{level}_LOG" not in all_logs

    for level in LOG_PRIORITY[current_log_level:]:
        assert f"{level}_LOG" in all_logs
