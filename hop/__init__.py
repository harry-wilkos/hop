import os
import site
import sys
from importlib import reload


def imports():
    from . import util
    from . import shelf_tools
    from . import shot
    globals().update(locals())


try:
    imports()
except ModuleNotFoundError:
    # Get the current directory where this file (__init__.py) is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    requirements_path = os.path.join(project_root, "requirements.txt")

    # Install the requirements
    import subprocess

    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "-r",
        requirements_path,
    ])

    # Reload site modules and try importing again
    reload(site)
    imports()

__all__ = [
        "shelf_tools",
        "util",
        "shot"
]

