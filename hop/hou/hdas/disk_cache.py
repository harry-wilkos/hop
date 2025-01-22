from hop.hou.util import expand_path, confirmation_dialog
from shutil import rmtree
import os
import hou
from hop.dl import create_job, call_deadline
from tempfile import NamedTemporaryFile


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


def farm(kwargs):
    node = kwargs["node"]
    start = node.evalParm("frame_rangex")
    end = node.evalParm("frame_rangey")
    step = node.evalParm("frame_rangez")
    sim = node.evalParm("simulation")
    chunk = 1 + end - start if sim else 1
    geo_rop = node.node("OUT").path()
    file = hou.hipFile

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
    job_name = job_name or file.basename().split(".")[0]
    job = create_job(
        job_name, node.path(), start, end, step, chunk, "farm_cache", "sim", None
    )

    plugin = NamedTemporaryFile(
        delete=False, mode="w", encoding="utf-16", suffix=".job"
    )
    plugin.write(f"hip_file={file.path()}\n")
    plugin.write(f"simulation={bool(sim)}\n")
    plugin.write(f"node_path={geo_rop}\n")
    plugin.close()

    call_deadline([job, plugin.name])
