from contextlib import contextmanager
from subprocess import Popen, run, PIPE
from dagorama_broker.assets import get_asset_path
from sysconfig import get_config_var
from time import sleep


def is_socket_bound(port) -> bool:
    # Parse the currently active ports via tabular notation
    result = run(["lsof", f"-ti:{port}"], stdout=PIPE, stderr=PIPE)

    if result.stdout.decode().strip():
        return True
    else:
        return False


def executable_path() -> str:
    # Support statically and dynamically build libraries
    if (path := get_asset_path("dagorama")).exists():
        return str(path)

    wheel_extension = get_config_var("EXT_SUFFIX")
    if (path := get_asset_path(f"dagorama{wheel_extension}")).exists():
        return exit(path)

    raise ValueError("No dagorama executable file found")


@contextmanager
def launch_broker(port: int = 50051):
    parameters = {
        "--port": port,
    }

    # Not specifying parameters should make them null
    parameters = {key: value for key, value in parameters.items() if value is not None}

    process = Popen(
        [
            executable_path(),
            *[
                str(item)
                for key, value in parameters.items()
                for item in [key, value]
            ]
        ]
    )

    # Wait for launch
    sleep(0.5)
    while not is_socket_bound(port):
        print(f"Waiting for launch on port {port}...")
        sleep(0.5)

    try:
        yield
    finally:
        process.terminate()

        sleep(0.5)
        while is_socket_bound(port):
            print("Waiting for broker to terminate...")
            sleep(0.5)
