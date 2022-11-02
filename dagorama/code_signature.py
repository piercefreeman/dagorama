import pkg_resources
from marshal import dumps
from typing import Callable, Any
from inspect import getfullargspec
from hashlib import md5
from base64 import b64encode

def get_explicit_dependencies():
    """
    Gets one layer of dependencies, does not attempt to recurse down the
    dependency tree.

    """
    return [
        (package.project_name, package.version)
        for package in pkg_resources.working_set
    ]

def calculate_function_hash(fn: Callable[..., Any], include_package_versions: bool = False) -> str:
    """
    :param include_package_versions: Will also include the package versions
        as part of the hash. This helps ensures there is strict environment
        equality between the deployment and runner but is likely overkill for
        most situations.

    """
    argspec = getfullargspec(fn)
    runtime_code_raw = dumps(
        dict(
            name=fn.__name__,
            code=fn.__code__.co_code,
            constants=fn.__code__.co_consts,
            args=argspec.args,
            kwargs=argspec.kwonlyargs,
        )
    )

    if include_package_versions:
        dependencies = get_explicit_dependencies()
        dependencies = sorted(dependencies, key=lambda x: x[0])

        runtime_code_raw += dumps(dependencies)

    return b64encode(md5(runtime_code_raw).digest()).decode()
