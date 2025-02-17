import os
from hop.hou.util.usd_helpers import compare_scene
from hop.util import post
from hop.dl import create_job, call_deadline, submit_decode, file_name
import hou
from hop.hou.util import confirmation_dialog
from tempfile import NamedTemporaryFile


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
    if type(node) is str:
        node = hou.node(node)
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
    node.parm("export_scene").pressButton()
    node.parm("reload").pressButton()
    node.parm("export_render").pressButton()


def local_render(kwargs: dict):
    node = kwargs["node"]
    node.parm("rendering").set(True)
    node.parm("targettopnetwork").set("Local_Render")
    export(kwargs)
    discord = node.evalParm("discord")
    if discord:
        file = file_name(hou.hipFile.path())
        post(
            "discord",
            {
                "message": f":green_circle: **{node.path()}** in **{file}** started rendering :green_circle:"
            },
        )
    node.parm("dirty").pressButton()
    node.parm("cook").pressButton()


def farm_render(kwargs: dict):
    node = kwargs["node"]
    file = hou.hipFile
    discord = bool(node.evalParm("discord"))
    if bool(node.evalParm("frame_type")):
        start = node.evalParm("frame_rangex")
        end = node.evalParm("frame_rangey")
    else:
        frame = int(hou.frame())
        start, end = frame, frame
    step = node.evalParm("frame_rangez")
    if file.hasUnsavedChanges():
        if confirmation_dialog(
            "Karma ROP",
            "The scene must be saved before submission",
            default_choice=0,
        ):
            file.save()
        else:
            return

    job_enter, job_name = hou.ui.readInput(
        "Job name",
        ("OK", "Cancel"),
        title="Farm Cache",
        default_choice=0,
        close_choice=1,
        initial_contents=node.evalParm("job_name"),
    )
    if job_enter:
        return
    if job_name:
        node.parm("job_name").set(job_name)
    else:
        job_name = file.basename().split(".")[0]

    job = create_job(
        job_name,
        node.path(),
        start,
        end,
        step,
        1,
        "farm_rop",
        "main",
        None,
        True,
        discord,
    )
    plugin = NamedTemporaryFile(
        delete=False, mode="w", encoding="utf-16", suffix=".job"
    )
    plugin.write(f"hip_file={file.path()}\n")
    plugin.write(f"node_path={node.path()}\n")
    plugin.write(f"discord={discord}\n")
    plugin.write(f"usd_file={node.node('Set_Path3').evalParm('savepath')}\n")
    plugin.close()

    deadline_return = submit_decode(str(call_deadline([job, plugin.name])))[0]
    if deadline_return:
        node.parm("farm_id").set(deadline_return)
        hou.ui.displayMessage(f"{node.path()} submitted to the farm", title="Karm ROP")


def cancel(kwargs):
    node = kwargs["node"]
    node.parm("cancel").pressButton()
    node.parm("targettopnetwork").set("")
    farm_id = node.parm("farm_id")
    call_deadline(["FailJob", id]) if (id := farm_id.eval()) else None
    if node.evalParm("discord") and (node.evalParm("rendering") or id):
        file = file_name(hou.hipFile.path())
        post(
            "discord",
            {
                "message": f":orange_circle: **{node.path()}** in **{file}** was cancelled :orange_circle:"
            },
        )
    if farm_id:
        hou.ui.displayMessage("Job cancelled", title="Karma ROP")
    farm_id.set("")
    node.parm("rendering").set(False)


def clear_cache(kwargs: dict):
    cancel(kwargs)
    node = kwargs["node"]
    for i in range(1, 4):
        path = node.node(f"Set_Path{i}").evalParm("savepath")
        if os.path.exists(path):
            os.remove(path)
