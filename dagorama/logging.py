from logging import (CRITICAL, DEBUG, ERROR, INFO, WARNING, basicConfig,
                     getLogger)
from os import getenv


def get_log_level():
   """
   More explicit implementation to `logging.getLevelName`. We would
   rather raise an error if the log level is not recognized than default to the
   string value that getLevelName does.

   """
   level = getenv("DAGORAMA_LOG_LEVEL", "WARNING")
   if level == "DEBUG":
      return DEBUG
   elif level == "INFO":
      return INFO
   elif level == "WARNING":
      return WARNING
   elif level == "ERROR":
      return ERROR
   elif level == "CRITICAL":
      return CRITICAL
   raise ValueError(f"Unknown log level: {level}")


basicConfig(
    level=get_log_level(),
    format="{asctime} - {name} - [{levelname}] - {message}",
)

LOGGER = getLogger("Dagorama")

def get_default_console_width(default_value: int = 80):
   try:
      from os import get_terminal_size
      return get_terminal_size().columns
   except Exception:
      # Likely not running in a terminal
      return default_value
