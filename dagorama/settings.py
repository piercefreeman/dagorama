from os import environ

# Flag that dagorama should run in testing mode; ie. run promises inline
# when initially called
INLINE_ENVIRONMENT_FLAG = "DAGORAMA_INLINE"


def should_run_inline():
    return environ.get(INLINE_ENVIRONMENT_FLAG, "false").lower().strip() == "true"
