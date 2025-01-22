import hou
from hop.hou.util import confirmation_dialog
from hop.dl import create_job, submit_decode, call_deadline
from tempfile import NamedTemporaryFile
import os
import random
import string


def farm_cache():
    selected_nodes = hou.selectedNodes()
    cache_nodes = []
    disk_cache_dict = {}
    for node in selected_nodes:
        if "Disk_Cache" in node.type().name():
            cache_nodes.append(node)
            disk_cache_dict[node] = True
        elif node.parm("execute"):
            cache_nodes.append(node)
            disk_cache_dict[node] = False

    cache_nodes = [node for node in hou.sortedNodes(tuple(cache_nodes))]

    if cache_nodes:
        file = hou.hipFile
        if file.hasUnsavedChanges():
            if confirmation_dialog(
                "Farm Cache",
                "The scene must be saved before submission",
                default_choice=0,
            ):
                file.save()
            else:
                return

        job_enter, init_job_name = hou.ui.readInput(
            "Job name",
            ("OK", "Cancel"),
            title="Farm Cache",
            default_choice=0,
            close_choice=1,
        )

        if job_enter:
            return
        if init_job_name:
            job_name = init_job_name
        else:
            job_name = file.basename().split(".")[0]

        batch = None
        if len(cache_nodes) != 1:
            batch = f"{job_name} ({''.join(random.choices(string.ascii_letters + string.digits, k=4))})"

        stored_args = []
        for node in cache_nodes:
            if disk_cache_dict[node]:
                node.parm("job_name").set(init_job_name)
                start = int(node.evalParm("frame_rangex"))
                end = int(node.evalParm("frame_rangey"))
                float_step = node.evalParm("frame_rangez")
                step = int(float_step) if int(float_step) >= 1 else 1
                sim = node.evalParm("simulation")
                chunk = 1 + end - start if sim else 1
                geo_rop = node.node("OUT").path()

                job = create_job(
                    job_name,
                    node.path(),
                    start,
                    end,
                    step,
                    chunk,
                    "farm_cache",
                    "sim",
                    batch,
                )

                plugin = NamedTemporaryFile(
                    delete=False, mode="w", encoding="utf-16", suffix=".job"
                )
                plugin.write(f"hip_file={file.path()}\n")
                plugin.write(f"simulation={bool(sim)}\n")
                plugin.write(f"node_path={geo_rop}\n")
                if float_step <= 1:
                    plugin.write(f"substep={float_step}\n")
                else:
                    plugin.write("substep=1\n")
                plugin.close()

                if not batch:
                    deadline_return = submit_decode(
                        str(call_deadline([job, plugin.name]))
                    )
                    if deadline_return:
                        node.parm("job_id").set(deadline_return)
                        hou.ui.displayMessage(
                            f"{node.path()} submitted to the farm", title="Farm Cache"
                        )
                    return
                stored_args.extend(["job", job, plugin.name])

            else:
                python_file = NamedTemporaryFile(
                    delete=False,
                    mode="w",
                    encoding="utf-8",
                    suffix=".py",
                    dir=os.path.normpath(os.environ["HOP_TEMP"]),
                )
                python_file.write(
                    f"hou.node('{node.path()}').parm('execute').pressButton()"
                )
                python_file.close()

                current = int(hou.frame())
                job = create_job(
                    job_name,
                    node.path(),
                    current,
                    current,
                    1,
                    1,
                    "UHFarmCache",
                    "sim",
                    batch,
                )

                plugin = NamedTemporaryFile(
                    delete=False, mode="w", encoding="utf-16", suffix=".job"
                )
                plugin.write(f"SceneFile={file.path()}\n")
                plugin.write(f"cacheMeFile={python_file.name}\n")
                plugin.close()
                if not batch:
                    call_deadline([job, plugin.name])
                    hou.ui.displayMessage(f"{node.path()} submitted to the farm", title="Farm Cache")
                    return
                stored_args.extend(["job", job, plugin.name])

        call_deadline(["submitmultiplejobs", "dependent", *stored_args])
        hou.ui.displayMessage(f"{len(cache_nodes)} nodes submitted to the farm", title="Farm Cache")
