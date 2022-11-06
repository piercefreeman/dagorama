
from importlib import import_module
from inspect import isclass
from uuid import UUID

from dagorama.definition import DAGDefinition, DAGInstance


def function_to_name(func):
    if isclass(func):
        module_name = getattr(func, "__module__")
        class_path = getattr(func, "__name__")
    elif isinstance(func, (DAGDefinition, DAGInstance)):
        return function_to_name(func.__class__)
    else:
        module_name = func.__globals__["__name__"]
        class_path = func.__qualname__

    return f"{module_name}:{class_path}"


FUNCTION_CACHE = {}


def register_function(func):
    global FUNCTION_CACHE
    FUNCTION_CACHE[function_to_name(func)] = func


def name_to_function(name: str, instance_id: UUID):
    """
    Takes a function name and attempts to convert it into a local callable.
    If the function is part of a class that hasn't already been registered as
    via `register_function`, will attempt to instantiate it with no initial
    parameters.

    If your class needs to be instantiated with runtime variables, make sure you
    register it before the worker begins executing.

    """
    global FUNCTION_CACHE
    if name in FUNCTION_CACHE:
        return FUNCTION_CACHE[name]

    # Can also try to sniff for function names throughout entire global namespace, but this
    # is still conditioned on name conventions
    package_name, fn_path = name.split(":")
    fn_path_components = fn_path.split(".")

    try:
        mod = import_module(package_name)
    except ModuleNotFoundError:
        raise ValueError(f"Could not import function with path: {name}")

    for i, component in enumerate(fn_path_components):
        # Get class from cached globals, if possible
        component_name = f"{package_name}:{'.'.join(fn_path_components[:i+1])}"
        if component_name in FUNCTION_CACHE:
            mod = FUNCTION_CACHE[component_name]
            continue

        if not hasattr(mod, component):
            raise ValueError(f"Unable to resolve dagorama function: {name}")

        mod = getattr(mod, component)

        if isclass(mod) and issubclass(mod, DAGDefinition):
            definition = mod()
            mod = DAGInstance(instance_id, definition) # type: ignore
        elif isclass(mod):
            # Assume we can instantiate classes with no init arguments
            mod = mod()

        register_function(mod)

    return mod
