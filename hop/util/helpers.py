import loptoolutils

try:
    import hou
except ModuleNotFoundError:
    from .import_hou import import_hou

    hou = import_hou()
from hou import ObjNode


def pop_dict(data: dict, key_to_split: str) -> tuple:
    dict_1 = {key_to_split: data[key_to_split]} if key_to_split in data else {}
    dict_2 = {k: v for k, v in data.items() if k != key_to_split}
    return dict_1, dict_2


def place_node(
    kwargs: dict, pane_type: str | list, node_type: str, node_name: None | str = None
) -> ObjNode | None:
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
