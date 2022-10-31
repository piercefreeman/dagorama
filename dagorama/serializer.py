
from importlib import import_module
from inspect import getmodulename, isclass
from typing import Any


def function_to_name(func):
    module_name = getmodulename(func.__globals__["__file__"])
    class_path = func.__qualname__

    return f"{module_name}:{class_path}"

# Global cache of functions, since performing the dependency import and function
# lookup is non-trivial and occurs frequently within each DAG worker
# name -> function
CACHED_FUNCTIONS : dict[str, Any] = {}

def name_to_function(name: str):
    if name in CACHED_FUNCTIONS:
        return CACHED_FUNCTIONS[name]

    # Can also try to sniff for function names throughout entire global namespace, but this
    # is still conditioned on name conventions
    package_name, fn_path = name.split(":")
    fn_path_components = fn_path.split(".")

    mod = import_module(package_name)

    for i, component in enumerate(fn_path_components):
        component_name = f"{package_name}:{'.'.join(fn_path_components[:i+1])}"
        if component_name in CACHED_FUNCTIONS:
            mod = CACHED_FUNCTIONS[component_name]
            continue

        if not hasattr(mod, component):
            raise ValueError(f"Unable to resolve dagorama function: {name}")

        mod = getattr(mod, component)

        if isclass(mod):
            # Assume we can instantiate classes with no init arguments
            mod = mod()
        CACHED_FUNCTIONS[component_name] = mod

    return mod
