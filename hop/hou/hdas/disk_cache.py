from hop.hou.util import confirmation_dialog
from hop.util import post
from shutil import rmtree
import os
import hou
from hop.dl import create_job, call_deadline, submit_decode, file_name
from tempfile import NamedTemporaryFile
import re


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
    start = int(float(kwargs["script_value0"]))
    end = int(float(kwargs["script_value1"]))
    step = float(kwargs["script_value2"])
    node.parm("frame_rangex").set(start)

    if step <= 0:
        node.parm("frame_rangez").set(1)
    elif step > 1:
        node.parm("frame_rangez").set(int(step))

    if end <= start:
        node.parm("frame_rangey").set(start + 1)
    else:
        node.parm("frame_rangey").set(end)


def open_path(kwargs):
    node = kwargs["node"]

    dir = node.evalParm("geopath")
    if dir:
        path = os.path.dirname(dir)
        if os.path.exists(path):
            hou.ui.showInFileBrowser(path)


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
    discord = node.evalParm("discord")
    file = file_name(hou.hipFile.path())
    if discord:
        post(
            "discord",
            {
                "message": f":green_circle: **{node.path()}** in **{file}** started caching :green_circle:"
            },
        )

    with hou.InterruptableOperation("Disk Cache"):
        try:
            node.node("OUT").parm("execute").pressButton()
            reload(kwargs)
        except hou.OperationFailed:
            if discord:
                post(
                    "discord",
                    {
                        "message": f":orange_circle: **{node.path()}** in **{file}** was cancelled :orange_circle:"
                    },
                )
            return

    if discord:
        post(
            "discord",
            {
                "message": f":checkered_flag: **{node.path()}** in **{file}** finished caching :checkered_flag:"
            },
        )


def farm(kwargs):
    node = kwargs["node"]
    start = int(node.evalParm("store_framesx"))
    end = int(node.evalParm("store_framesy"))
    float_step = node.evalParm("store_framesz")
    step = int(float_step) if int(float_step) >= 1 else 1
    sim = node.evalParm("simulation")
    chunk = 1 + end - start if sim else 1
    geo_rop = node.node("OUT").path()
    file = hou.hipFile
    discord = bool(node.evalParm("discord"))

    if file.hasUnsavedChanges():
        if confirmation_dialog(
            "Disk Cache",
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
        chunk,
        "farm_cache",
        "sim",
        None,
        discord,
        discord,
    )

    plugin = NamedTemporaryFile(
        delete=False, mode="w", encoding="utf-16", suffix=".job"
    )
    plugin.write(f"hip_file={file.path()}\n")
    plugin.write(f"simulation={bool(sim)}\n")
    plugin.write(f"node_path={geo_rop}\n")
    plugin.write(f"discord={discord}\n")
    if float_step <= 1:
        plugin.write(f"substep={float_step}\n")
    else:
        plugin.write("substep=1\n")
    plugin.close()

    deadline_return = submit_decode(str(call_deadline([job, plugin.name])))
    if deadline_return:
        node.parm("job_id").set(deadline_return)
        hou.ui.displayMessage(
            f"{node.path()} submitted to the farm", title="Disk Cache"
        )


def cancel(kwargs):
    node = kwargs["node"]
    id = node.evalParm("job_id")
    if id:
        call_deadline(["FailJob", id])
        discord = bool(node.evalParm("discord"))
        if discord:
            job_name = re.search("Name:(.+)", str(call_deadline(["GetJobDetails", id])))
            if job_name:
                post(
                    "discord",
                    {
                        "message": f":orange_circle: **{node.path()}** in **{job_name.group()}** was cancelled :orange_circle:"
                    },
                )
        hou.ui.displayMessage("Job cancelled", title="Disk Cache")
    node.parm("job_id").set("")
