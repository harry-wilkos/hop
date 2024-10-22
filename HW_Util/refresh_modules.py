import sys
from importlib import reload
import site
import os


def refresh_modules(ignore_module_paths: str | list = []):
    if isinstance(ignore_module_paths, str):
        ignore_module_paths = [ignore_module_paths]

    standard_library_paths = [os.path.dirname(os.__file__)]
    ignore_paths = [os.path.abspath(path) for path in ignore_module_paths]
    module_names = list(sys.modules.keys())
    reloads = []

    for module_name in module_names:
        module = sys.modules.get(module_name)

        # Skip __main__ and standard modules
        if module_name == "__main__" or module is None:
            continue

        if hasattr(module, "__file__"):
            module_file = os.path.abspath(module.__file__)

            # Skip standard library modules or ignored module paths
            if any(
                os.path.commonpath([module_file, os.path.abspath(path)])
                == os.path.abspath(path)
                for path in standard_library_paths + ignore_paths
                if path is not None
            ):
                continue

        # Try reloading the module if it's not in ignored paths
        try:
            reload(module)
            reloads.append(module_name)
        except Exception:
            continue
    reload(site)
    return reloads

