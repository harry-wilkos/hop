from hop.hou.util import expand_path
from shutil import rmtree
import os
import hou


def version_up(kwargs):
    node = kwargs["node"]
    version = node.parm("version")
    version.set(version.eval() + 1)


def version_down(kwargs):
    node = kwargs["node"]
    version = node.parm("version")
    if version.eval() <= 1:
        version.set(1)
        return
    version.set(version.eval() - 1)


def frame_range(kwargs):
    node = kwargs["node"]
    start = int(kwargs["script_value0"])
    end = int(kwargs["script_value1"])
    step = int(kwargs["script_value2"])

    if step < 1:
        node.parm("frame_rangez").set(1)
    if end <= start:
        node.parm("frame_rangey").set(start + 1)


def open_path(kwargs):
    node = kwargs["node"]

    dir = expand_path(node.evalParm("savepath"))
    if dir:
        hou.ui.showInFileBrowser(dir)

def reload(kwargs):
    node = kwargs["node"]
    node.node("Load_Switch").cook(force=True)
    node.node("Reload").cook(force=True)


def delete_cache(kwargs):
    node = kwargs["node"]
    savepath = node.evalParm("savepath")
    version = str(node.evalParm("version")).zfill(2)
    path = f"{savepath}/V{version}"
    if os.path.exists(path):
        rmtree(f"{savepath}/V{version}")
    reload(kwargs)

def local(kwargs):
    node = kwargs["node"]
    node.node("OUT").parm("execute").pressButton()
    reload(kwargs)


