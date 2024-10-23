import os
import site
import sys
from importlib import reload


def refresh_modules(ignore_module_paths: str | list = []) -> list:
    if isinstance(ignore_module_paths, str):
        ignore_module_paths = [ignore_module_paths]

    standard_library_paths = [os.path.dirname(os.__file__)]
    ignore_paths = [os.path.abspath(path) for path in ignore_module_paths]
    module_names = list(sys.modules.keys())
    reloads = []

    for module_name in module_names:
        module = sys.modules.get(module_name)

        if module_name == "__main__" or module is None:
            continue

        if hasattr(module, "__file__") and module.__file__ is not None:
            module_file = os.path.abspath(module.__file__)

            if any(
                os.path.commonpath([module_file, os.path.abspath(path)])
                == os.path.abspath(path)
                for path in standard_library_paths + ignore_paths
                if path is not None
            ):
                continue

        try:
            reload(module)
            reloads.append(module_name)
        except Exception:
            continue
    reload(site)
    return reloads
