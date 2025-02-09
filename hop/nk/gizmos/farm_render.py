import nuke
from pathlib import Path
import random
import string
from hop.dl import create_job, submit_decode, call_deadline
from tempfile import NamedTemporaryFile


def farm_render():
    write_nodes = nuke.selectedNodes("Write")
    root = nuke.root()
    if not write_nodes:
        return
    if root.modified() or root.name() == "Root":
        if not nuke.ask("The scene must be saved before submission"):
            return
        elif not nuke.scriptSave():
            return

    job_name = nuke.getInput("Job name")
    if not job_name:
        if type(job_name) is str:
            job_name = Path(root.name()).name.split(".")[0]
        else:
            return

    discord = nuke.ask("Send job updates to the Discord?")

    batch = None
    if len(write_nodes) > 1 or discord:
        batch = f"{job_name} ({''.join(random.choices(string.ascii_letters + string.digits, k=4))})"

    stored_args = []
    start = nuke.Root().knob("first_frame").value()
    end = nuke.Root().knob("last_frame").value()
    for node in write_nodes:
        path = node.name()
        job = create_job(
            job_name,
            path,
            start,
            end,
            1,
            1,
            "farm_nuke",
            "main",
            batch,
            discord,
            discord,
        )
        plugin = NamedTemporaryFile(
            delete=False, mode="w", encoding="utf-16", suffix=".job"
        )
        plugin.write(f"nk_file={root.name()}\n")
        plugin.write(f"node_path={path}\n")
        plugin.write(f"discord={discord}\n")
        plugin.close()
        if not batch:
            deadline_return = submit_decode(str(call_deadline([job, plugin.name])))
            if deadline_return:
                nuke.message(f"{path} submitted to the farm")
            return
        stored_args.extend(["job", job, plugin.name])
    deadline_return = submit_decode(
        str(call_deadline(["submitmultiplejobs", "dependent", *stored_args]))
    )
    if deadline_return:
        nuke.message(f"{len(write_nodes)} nodes submitted to the farm")
