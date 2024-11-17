import loptoolutils
import math
import numpy as np

try:
    import hou
except ModuleNotFoundError:
    from .import_hou import import_hou

    hou = import_hou()
from hou import ObjNode


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


def place_node(
    kwargs: dict, pane_type: str | list, node_type: str, node_name: None | str = None
) -> ObjNode:
    if node_name is None:
        node_name = node_type

    node = None
    try:
        node = loptoolutils.genericTool(
            kwargs, node_type, node_name, clicktoplace=False
        )
    except AttributeError:
        desktop = hou.ui.curDesktop()
        pane = desktop.paneTabUnderCursor()
        if pane is not None:
            current_context = pane.pwd()
            if current_context.type().name() == pane_type:
                node = current_context.createNode(
                    node_type, node_name, True, True, False, True
                )
                node.moveToGoodPosition()
        else:
            if pane_type[0] != "/":
                pane_type = f"/{pane_type}"
            current_context = hou.node(pane_type)
            if current_context is not None:
                node = current_context.createNode(
                    node_type, node_name, True, True, False, True
                )
                node.moveToGoodPosition()

    return node
