from ..util import expand_path
import os
from shutil import copy2, move
from pathlib import Path


def copy_file(file: str, target: list) -> None | str:
    target[-1] = f"{target[-1]}{Path(file).suffix}"
    path = expand_path(file)
    root = os.environ["HOP"]
    if path is not None and root is not None:
        save_dir = os.path.join(root, *target[:-1])
        save_path = os.path.join(save_dir, target[-1])
        try:
            os.remove(save_path)
        except FileNotFoundError:
            pass
        os.makedirs(save_dir, exist_ok=True)
        return copy2(path, save_path)


def move_folder(folder: str, target: list) -> None | str:
    path = expand_path(folder)
    root = os.environ["HOP"]
    if path is not None and root is not None:
        save_path = os.path.join(root, *target)
        os.makedirs(save_path, exist_ok=True)
        return move(path, save_path)
