import sys
import os
from typing import Any


def import_hou(install_path: str = "") -> Any:
    s_dlopen_flag = False
    old_dlopen_flags = 0

    if hasattr(sys, "setdlopenflags"):
        old_dlopen_flags = sys.getdlopenflags()
        sys.setdlopenflags(old_dlopen_flags | os.RTLD_GLOBAL)
        s_dlopen_flag = True

    if sys.platform == "win32   " and hasattr(os, "add_dll_directory"):
        hfs_path = os.getenv("HFS")
        if hfs_path:
            os.add_dll_directory(f"{hfs_path}/bin")

    try:
        import hou
    except ModuleNotFoundError:
        HHP = os.getenv("HHP")
        PATH = os.getenv("PATH")

        # Attempt to locate hou.py
        if HHP is not None:
            sys.path.append(HHP)
        elif os.path.exists(os.path.join(install_path, "hou.py")):
            sys.path.append(install_path)
        elif PATH is not None:
            paths = PATH.split(":")
            for path in paths:
                if "hfs" in path:
                    houdini_path = os.path.join(
                        os.path.dirname(path),
                        f"houdini/python{sys.version_info[0]}.{sys.version_info[1]}libs",
                    )
                    if os.path.exists(os.path.join(houdini_path, "hou.py")):
                        sys.path.append(houdini_path)
                        break
        else:
            raise ModuleNotFoundError("Couldn't find hou module path")

        import hou

    if s_dlopen_flag:
        sys.setdlopenflags(old_dlopen_flags)

    return hou

