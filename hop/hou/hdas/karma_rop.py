import os
from hop.hou.util.usd_helpers import compare_scene

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

    settings_export = node.node("set_Path2")
    settings_path = settings_export.evalParm("savepath")
    settings_stage = settings_export.stage()
    if os.path.exists(settings_path) and compare_scene(settings_stage, settings_path):
        node.parm("")


    render_export = node.node("Import_Layers")
    settings_path = render_export.evalParm("filepath1")


def local_render(kwargs:dict):
    export(kwargs) 

