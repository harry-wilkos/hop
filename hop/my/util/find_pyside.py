import sys
import importlib


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
