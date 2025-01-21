import os
import hou
import itertools
from hop.hou.util import error_dialog, confirmation_dialog
from hop.dl import set_env, call_deadline
from tempfile import TemporaryFile


def check_node(node, accepted_paths: list) -> bool:
    definition = node.type().definition()
    if definition:
        library_path = os.path.normpath(definition.libraryFilePath())
        if library_path and not any(
            library_path.startswith(accept) for accept in accepted_paths
        ):
            return False
    return True


def farm_cache(accepted_paths: list = []):
    accepter_vars = [
        os.environ[var].split(os.pathsep)
        for var in [
            "SIDEFXLABS",
            "HH",
            "HOUDINI_OTLSCAN_PATH",
        ]
        if var in os.environ
    ] + accepted_paths

    accepted_paths = [
        os.path.normpath(path) for path in itertools.chain.from_iterable(accepter_vars)
    ]

    selected_nodes = hou.selectedNodes()
    cache_nodes = []
    unique_nodes = []
    for node in selected_nodes:
        if node.parm("execute"):
            cache_nodes.append(node)
            inputs = list(node.inputAncestors())
            while inputs:
                for input in inputs:
                    inputs.pop(0)
                    inputs.extend(input.inputs())
                    if input not in unique_nodes:
                        unique_nodes.append(input)

    for check in unique_nodes:
        if not check_node(check, accepted_paths):
            error_dialog(
                "Farm Cache",
                f"{check} is not a node available to the farm in {accepted_paths[-1]}",
            )
            return

    cache_paths = [node.path() for node in hou.sortedNodes(tuple(cache_nodes))]

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

        job_name = (
            hou.ui.readInput("Job name", title="Farm Cache")[1]
            or file.basename().split(".")[0]
        )

        stored_args = []
        for cache in cache_paths:
            python_file = TemporaryFile(
                delete=False,
                mode="w",
                encoding="utf-8",
                suffix=".py",
                dir=os.path.normpath(os.environ["HOP_TEMP"]),
            )
            python_file.write(f"hou.node('{cache}').parm('execute').pressButton()")
            python_file.close()

            job_file = TemporaryFile(
                delete=False, mode="w", encoding="utf-16", suffix=".job"
            )
            job_file.write("Plugin=UHFarmCache\n")
            job_file.write(f"Name={job_name}\n")
            job_file.write(f"Comment={cache}\n")
            for var in set_env([
                "TWELVEFOLD_ROOT",
                "PYTHON",
                "PYTHONPATH",
                "HOUDINI_USER_PREF_DIR",
                "OCIO",
                "MONGO_ADDRESS",
                "API_ADDRESS",
                "FPS",
                "RES",
                "HOP",
                "HOP_TEMP",
            ]):
                job_file.write(var)
            job_file.close()

            plugin_file = TemporaryFile(
                delete=False, mode="w", encoding="utf-16", suffix=".job"
            )
            plugin_file.write(f"SceneFile={file.path()}\n")
            plugin_file.write(f"cacheMeFile={python_file.name}\n")
            plugin_file.close()

            if len(cache_paths) == 1:
                call_deadline([job_file.name, plugin_file.name])
                return
            stored_args.extend(["job", job_file.name, plugin_file.name])
        call_deadline(["submitmultiplejobs", "dependent", *stored_args])
