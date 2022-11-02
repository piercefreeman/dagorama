
from importlib import import_module
from inspect import getmodulename, isclass
from uuid import UUID

from dagorama.definition import DAGDefinition
from typing import cast


def function_to_name(func):
    module_name = func.__globals__["__name__"]
    class_path = func.__qualname__

    return f"{module_name}:{class_path}"


def name_to_function(name: str, instance_id: UUID):
    # Can also try to sniff for function names throughout entire global namespace, but this
    # is still conditioned on name conventions
    package_name, fn_path = name.split(":")
    fn_path_components = fn_path.split(".")

    try:
        mod = import_module(package_name)
    except ModuleNotFoundError:
        raise ValueError(f"Could not import function with path: {name}")

    for component in fn_path_components:
        if not hasattr(mod, component):
            raise ValueError(f"Unable to resolve dagorama function: {name}")

        mod = getattr(mod, component)

        if isclass(mod) and issubclass(mod, DAGDefinition):
            mod = mod() # type: ignore
            mod.instance_id = instance_id  # type: ignore
        elif isclass(mod):
            # Assume we can instantiate classes with no init arguments
            mod = mod()

    return mod
