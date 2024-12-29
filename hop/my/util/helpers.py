import sys
import importlib
import os
import maya.cmds as cmds


def set_fps():
    fps = int(os.environ["FPS"])
    fps_mapping = {
        15: "game",
        24: "film",
        25: "pal",
        30: "ntsc",
        48: "show",
        60: "ntscf",
    }
    if fps in fps_mapping:
        cmds.currentUnit(time=fps_mapping[fps])
        cmds.playbackOptions(edit=True, playbackSpeed=0, maxPlaybackSpeed=1)
    else:
        raise ValueError(
            f"Unsupported FPS: {fps}. Supported values are: {list(fps_mapping.keys())}"
        )


def find_pyside():
    pyside_versions = ["PySide6", "PySide2"]

    for version in pyside_versions:
        try:
            sys.modules["PySide"] = importlib.import_module(version)
            sys.modules["PySide.QtCore"] = importlib.import_module(f"{version}.QtCore")
            sys.modules["PySide.QtWidgets"] = importlib.import_module(
                f"{version}.QtWidgets"
            )
            sys.modules["PySide.QtGui"] = importlib.import_module(f"{version}.QtGui")
            shiboken = importlib.import_module(f"shiboken{version[-1]}")

            break
        except ModuleNotFoundError:
            continue
    else:
        raise ModuleNotFoundError("No PySide module found.")

    return sys.modules["PySide"]
