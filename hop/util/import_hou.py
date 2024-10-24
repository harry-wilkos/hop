import sys
import os
from typing import Any


def find_install() -> str | None:
    install_dir = None
    PATH = os.getenv("PATH")
    if PATH is not None:
        paths = PATH.split(":")
        for path in paths:
            if "hfs" in path:
                install_dir = os.path.dirname(path)
                break
    if install_dir is not None:
        return install_dir


def import_hou(install_path: str = "") -> Any:
    install = find_install()

    s_dlopen_flag = False
    old_dlopen_flags = 0
    if install is not None:
        jemalloc = os.path.join(install, "dsolib/libjemalloc.so")
        if os.path.exists(jemalloc):
            os.environ["LD_PRELOAD"] = jemalloc

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

        # Attempt to locate hou.py
        if HHP is not None:
            sys.path.append(HHP)
        elif os.path.exists(os.path.join(install_path, "hou.py")):
            sys.path.append(install_path)
        elif install is not None:
            houdini_path = os.path.join(
                install,
                f"houdini/python{sys.version_info[0]}.{sys.version_info[1]}libs",
            )
            if os.path.exists(os.path.join(houdini_path, "hou.py")):
                sys.path.append(houdini_path)
        else:
            raise ModuleNotFoundError("Couldn't find hou module path")

        import hou

    if s_dlopen_flag:
        sys.setdlopenflags(old_dlopen_flags)

    return hou


find_install()
