from logging import getLogger, basicConfig
from os import getenv

LOGGER = getLogger("Dagorama")

basicConfig(
    level=getenv("DAGORAMA_LOG_LEVEL", "WARNING"),
    format="{asctime} - {name} - [{levelname}] - {message}",
)

def get_default_console_width(default_value: int = 80):
   try:
      from os import get_terminal_size
      return get_terminal_size().columns
   except Exception:
      # Likely not running in a terminal
      return default_value
