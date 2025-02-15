import os
from hop.hou.util.usd_helpers import compare_scene
from time import sleep


def find_aovs(kwargs: dict):
    node = kwargs["node"]
    node.parm("rendervars").set(0)
    for folder in [
        "Colour",
        "Diffuse",
        "Reflections & Refractions",
        "Lights & Emission",
        "Volume",
        "BSDF Labels",
        "Ray",
        "Crypto",
    ]:
        parms = node.parmsInFolder(("Settings", "AOVs", folder))
        for parm in parms:
            yield parm


def clear_aov(kwargs: dict) -> None:
    for parm in find_aovs(kwargs):
        parm.set(0)
    kwargs["node"].parm("beauty").set(1)


def export(kwargs: dict):
    node = kwargs["node"]
    tags = node.node("LPE_Tag")
    tags.parm("manualtags").set(0)
    if node.evalParm("preprocess") != 0:
        tags.parm("populate").pressButton()

    settings_export = node.node("Set_Path2")
    settings_path = settings_export.evalParm("savepath")
    settings_stage = settings_export.stage()
    if not (os.path.exists(settings_path)) or not (
        compare_scene(settings_stage, settings_path)
    ):
        node.parm("export_settings").pressButton()

    scene_export = node.node("Set_Path1")
    scene_path = scene_export.evalParm("savepath")
    scene_stage = scene_export.stage()
    if not (os.path.exists(scene_path)) or not (compare_scene(scene_stage, scene_path)):
        node.parm("export_scene").pressButton()

    node.parm("reload").pressButton()
    node.parm("export_render").pressButton()


def local_render(kwargs: dict):
    node = kwargs["node"]
    node.parm("targettopnetwork").set("Local_Render")
    export(kwargs)
    node.parm("dirty").pressButton()
    node.parm("cook").pressButton()


def clear_cache(kwargs: dict):
    node = kwargs["node"]
    node.parm("cancel").pressButton()
    node.parm("targettopnetwork").set("")
    for i in range(1, 4):
        path = node.node(f"Set_Path{i}").evalParm("savepath")
        if os.path.exists(path):
            os.remove(path)
