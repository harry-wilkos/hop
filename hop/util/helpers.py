import math
import os
import site
import sys
from importlib import reload
from pathlib import Path
from shutil import copy2, move
import numpy as np


def copy_file(path: str, target: list) -> None | str:
    target[-1] = f"{target[-1]}{Path(path).suffix}"
    root = os.environ["HOP"]
    if path is not None and root is not None:
        save_dir = os.path.join(root, *target[:-1])
        save_path = os.path.join(save_dir, target[-1])
        try:
            os.remove(save_path)
        except FileNotFoundError:
            pass
        os.makedirs(save_dir, exist_ok=True)
        new_location = copy2(path, save_path)
        return new_location.replace(root, "$HOP")


def move_folder(path: str, target: list) -> None | str:
    root = os.environ["HOP"]
    if path is not None and root is not None:
        save_path = os.path.join(root, *target)
        os.makedirs(save_path, exist_ok=True)
        new_location = move(path, save_path)
        return new_location.replace(root, "$HOP")


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


def matrix_to_euler(matrix):
    if not isinstance(matrix, np.ndarray) or matrix.shape != (3, 3):
        raise ValueError("Input must be a 3x3 numpy array.")

    if abs(matrix[0, 2]) != 1:
        y = math.asin(-matrix[0, 2])
        x = math.atan2(matrix[1, 2], matrix[2, 2])
        z = math.atan2(matrix[0, 1], matrix[0, 0])
    else:
        # Gimbal lock case
        z = 0
        if matrix[0, 2] == -1:
            y = np.pi / 2
            x = math.atan2(matrix[1, 0], matrix[1, 1])
        else:
            y = -np.pi / 2
            x = math.atan2(-matrix[1, 0], -matrix[1, 1])

    return [math.degrees(x), math.degrees(y), math.degrees(z)]


def extract_matrix(matrix) -> list:
    matrix4 = np.array(matrix).reshape(4, 4)
    matrix3 = matrix4[:3, :3]
    scale = np.linalg.norm(matrix3, axis=0).tolist()

    rotation_matrix = matrix3 / scale  # Normalize the rotation matrix
    rotation = matrix_to_euler(rotation_matrix)

    translate = matrix4[3, :3].tolist()
    return translate + rotation + scale


def pop_dict(data: dict, key_to_split: str) -> tuple:
    dict_1 = {key_to_split: data[key_to_split]} if key_to_split in data else {}
    dict_2 = {k: v for k, v in data.items() if k != key_to_split}
    return dict_1, dict_2
