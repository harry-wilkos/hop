from hop.hou.util.usd_helpers import compare_scene
import os
import hou

def export(kwargs: dict) -> None:
    node = kwargs["node"]
    node.parm("current_frame").set(hou.frame())
    node.parm("rendering").set(1)

    tags = node.node("LPE_Tag")
    tags.parm("manualtags").set(0)
    if node.evalParm("preprocess") != 0:
        tags.parm("populate").pressButton()

    resources_node = node.node("Shot_Resources_Save")
    resources_path = resources_node.evalParm("savepath")
    resources_stage = resources_node.stage()
    if os.path.exists(resources_path) and compare_scene(resources_stage, resources_path):
        node.parm("Reload_Resources").pressButton()
    else:
        node.parm("Export_Resources").pressButton()
    
    settings_node = node.node("Shot_Settings_Save")
    settings_path = settings_node.evalParm("savepath")
    settings_stage = settings_node.stage()
    if os.path.exists(settings_path) and compare_scene(settings_stage, settings_path):
        node.parm("Reload_Settings").pressButton()
    else:
        node.parm("Export_Settings").pressButton()

    assets_node = node.node("Shot_Assets_Save")
    assets_path = assets_node.evalParm("savepath")
    assets_stage = assets_node.stage()
    if os.path.exists(assets_path) and compare_scene(assets_stage, assets_path):
        node.parm("Reload_Assets").pressButton()
    else:
        node.parm("Export_Assets").pressButton()

    node.node("Export_USD").parm("execute").pressButton()
    node.parm("rendering").set(0)


def clear_aov(kwargs: dict) -> None:
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
        parms = node.parmsInFolder(("Rendering", "AOVs", folder))
        for parm in parms:
            parm.revertToDefaults()

