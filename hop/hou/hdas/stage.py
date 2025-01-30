import os
import random
import string
from glob import glob
from pathlib import Path
from tempfile import NamedTemporaryFile
import re
import hou

from hop.util import post
from hop.dl import create_job, call_deadline, submit_decode
from hop.hou.util import error_dialog
from hop.hou.util.usd_helpers import compare_scene
from hop.hou.hdas.shot import load


def export(kwargs: dict) -> bool:
    node = kwargs["node"]
    if node.evalParm("load_shot") < 0:
        error_dialog("Export USD's", "No shot selected")
        return False

    node.parm("current_frame").set(hou.frame())
    node.parm("rendering").set(1)

    tags = node.node("LPE_Tag")
    tags.parm("manualtags").set(0)
    if node.evalParm("preprocess") != 0:
        tags.parm("populate").pressButton()

    resources_node = node.node("Shot_Resources_Save")
    resources_path = resources_node.evalParm("savepath")
    resources_stage = resources_node.stage()
    if os.path.exists(resources_path) and compare_scene(
        resources_stage, resources_path
    ):
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

    for file in glob(os.path.join(node.evalParm("usd_output"), "Passes", "*")):
        if "Deep" not in os.path.basename(file):
            os.remove(file)
    node.node("Export_USD").parm("execute").pressButton()
    node.parm("rendering").set(0)
    return True


def mplay(kwargs: dict) -> None:
    node = kwargs["node"]
    if node.evalParm("mplay"):
        node.parm("husk_args").set("--mplay-monitor - --mplay-session `@filename`")
    else:
        node.parm("husk_args").set("")


def local_render(kwargs: dict) -> None:
    node = kwargs["node"]
    location = node.evalParm("render_output")
    if not location or Path(location).suffix:
        error_dialog("Render USD's", "Invalid location")
        return
    export(kwargs)
    mplay(kwargs)
    node.parm("Dirty_Local").pressButton()
    node.parm("Cook_Local").pressButton()


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
        parms = node.parmsInFolder(("Rendering", "AOVs", folder))
        for parm in parms:
            yield parm


def default_aov(kwargs: dict) -> None:
    for parm in find_aovs(kwargs):
        parm.revertToDefaults()


def clear_aov(kwargs: dict) -> None:
    for parm in find_aovs(kwargs):
        parm.set(0)
    kwargs["node"].parm("beauty").set(1)


def farm_render(kwargs: dict) -> None:
    load(kwargs)
    if not export(kwargs):
        return
    node = kwargs["node"]
    job_name = f"Shot {node.evalParm('load_shot')}"
    if node.evalParm("evaluaton_type") == 0:
        start, end = node.evalParm("current_frame"), node.evalParm("current_frame")
    else:
        start = node.evalParm("frame_range2x")
        end = node.evalParm("frame_range2y")

    deep = True if node.evalParm("dcm") and node.evalParm("render_deep") else False
    usds = glob(os.path.join(node.evalParm("usd_output"), "Passes", "*"))
    uuid = "".join(random.choices(string.ascii_letters + string.digits, k=4))
    batch = f"{job_name} ({uuid})"
    output = node.evalParm("render_output")
    stored_args = []
    for file in usds:
        count = os.path.basename(file).split(".")[0]
        if count != "Deep" and (
            (parm := node.parm(f"render_holdout{int(count)}")) is None
            or not parm.eval()
        ):
            continue
        elif count == "Deep" and not deep:
            continue
        comment = f"Holdout {int(count)}" if count != "Deep" else count
        job = create_job(
            job_name,
            comment,
            start,
            end,
            1,
            1,
            "farm_husk",
            "main",
            batch,
            True,
            True,
        )
        plugin = NamedTemporaryFile(
            delete=False, mode="w", encoding="utf-16", suffix=".job"
        )
        plugin.write(f"usd_file={file}\n")
        plugin.write(
            f"output={os.path.join(output, os.path.basename(file).split('.')[0])}\n"
        )
        plugin.close()
        stored_args.extend(["job", job, plugin.name])

    deadline_return = submit_decode(
        str(call_deadline(["submitmultiplejobs", *stored_args]))
    )
    post_job = create_job(
        job_name,
        "Preview generation",
        start,
        end,
        1,
        1,
        "farm_process_holdouts",
        "main",
        batch,
        True,
        True,
        deadline_return[:-1] if deep else deadline_return,
    )
    post_plugin = NamedTemporaryFile(
        delete=False, mode="w", encoding="utf-16", suffix=".job"
    )

    exrs = [
        os.path.join(output, basename)
        for file in usds
        if (basename := os.path.basename(file).split(".")[0]) != "Deep"
    ]
    post_plugin.write(f"exrs={';'.join(exrs)}\n")
    post_plugin.write(f"output={os.path.join(os.environ['HOP_TEMP'], uuid)}\n")
    post_plugin.write(f"back_plate={node.evalParm('back_plate')}\n")
    post_plugin.close()
    deadline_return.append(
        submit_decode(str(call_deadline([post_job, post_plugin.name])))[0]
    )

    if deadline_return:
        node.parm("farm_id").set(" ".join(deadline_return))
    hou.ui.displayMessage(f"{job_name} submitted to the farm", title="Shot")


def farm_cancel(kwargs: dict) -> None:
    node = kwargs["node"]
    ids = node.evalParm("farm_id").split(" ")
    if ids:
        shot = ""
        for id in ids:
            call_deadline(["FailJob", id])
            details = str(call_deadline(["GetJobDetails", id]))
            shot = re.search(r"Name:\s*(.+)", details)
        if shot:
            post(
                "discord",
                {
                    "message": f":orange_circle: **{shot.group(1).strip()}**'s renders were cancelled :orange_circle:"
                },
            )
        hou.ui.displayMessage("Render cancelled", title="Shot")
    node.parm("farm_id").set("")
