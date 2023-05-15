from base64 import b64encode
from hashlib import md5
from inspect import getfullargspec
from marshal import dumps
from typing import Any, Callable

import pkg_resources

from dagorama.logging import get_logger


def get_explicit_dependencies():
    """
    Gets one layer of dependencies, does not attempt to recurse down the
    dependency tree.

    """
    return [
        (package.project_name, package.version) for package in pkg_resources.working_set
    ]


def calculate_function_hash(
    fn: Callable[..., Any], include_package_versions: bool = False
) -> str:
    """
    :param include_package_versions: Will also include the package versions
        as part of the hash. This helps ensures there is strict environment
        equality between the deployment and runner but is likely overkill for
        most situations.

    """
    argspec = getfullargspec(fn)
    fn_definition = dict(
        name=fn.__name__,
        code=fn.__code__.co_code,
        constants=fn.__code__.co_consts,
        args=argspec.args,
        kwargs=argspec.kwonlyargs,
    )
    runtime_code_raw = dumps(fn_definition)
    get_logger().debug(f"Hash: Definition: {fn_definition}")

    if include_package_versions:
        dependencies = get_explicit_dependencies()
        dependencies = sorted(dependencies, key=lambda x: x[0])

        runtime_code_raw += dumps(dependencies)

    hash_value = b64encode(md5(runtime_code_raw).digest()).decode()
    get_logger().debug(
        f"Hash: Value: {hash_value} (include_package_versions: {include_package_versions})"
    )

    return hash_value
