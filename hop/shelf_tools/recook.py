from ..util import import_hou

try:
    import hou
except ModuleNotFoundError:
    from ..util import import_hou

    hou = import_hou()


def recook():
    nodes = hou.selectedNodes()
    sorted = hou.sortedNodes(nodes)
    for node in sorted:
        parent = node.parent()
        while parent is not None:
            type = parent.type().name()
            if type == "dopnet":
                parent.parm("resimulate").pressButton()
                break
            parent = parent.parent()
        parms = ["resimulate", "reload", "clear", "dirtybutton"]
        for parm in parms:
            find_parm = node.parm(parm)
            if find_parm is not None:
                find_parm.pressButton()
        try:
            node.cook(force=True)
        except hou.OperationFailed:
            print("Error while cooking")
