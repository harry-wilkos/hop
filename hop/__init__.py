import importlib
import inspect
import os
import subprocess
import sys
from importlib import reload
import site

def setup_lazy_imports(imports, module_globals=None, requirements_path=None):
    # Infer module_globals if not provided
    if module_globals is None:
        frame = inspect.stack()[1]
        module_globals = frame.frame.f_globals

    # Infer requirements_path if not provided
    if requirements_path is None:
        current_dir = os.path.dirname(os.path.abspath(module_globals["__file__"]))
        project_root = os.path.dirname(current_dir)
        requirements_path = os.path.join(project_root, "requirements.txt")

    lazy_import_map = {}
    for module_name, attrs in imports.items():
        if isinstance(attrs, str):  # Single attribute as string
            lazy_import_map[attrs] = (module_name, attrs)
        else:  # Iterable of attributes
            for attr in attrs:
                lazy_import_map[attr] = (module_name, attr)

    def __getattr__(name):
        if name in lazy_import_map:
            module_name, attr_name = lazy_import_map[name]
            try:
                module = importlib.import_module(module_name, module_globals["__package__"])
                return getattr(module, attr_name)
            except ModuleNotFoundError:
                print(f"Module '{module_name}' not found. Installing requirements...")
                subprocess.check_call([
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    requirements_path,
                ])
                reload(site)
                module = importlib.import_module(module_name, module_globals["__package__"])
                return getattr(module, attr_name)
        raise AttributeError(f"module '{module_globals['__name__']}' has no attribute '{name}'")
    
    module_globals["__getattr__"] = __getattr__
    module_globals["__all__"] = list(module_globals.get("__all__", [])) + list(lazy_import_map.keys())


setup_lazy_imports({
    ".": ("hou", "util", "nk")
})
