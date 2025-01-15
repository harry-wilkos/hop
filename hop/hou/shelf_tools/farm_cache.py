import os
import hou
import itertools
from hop.hou.util import error_dialog


def check_node(node, accepted_paths: list) -> bool:
    definition = node.type().definition()
    if definition:
        library_path = os.path.normpath(definition.libraryFilePath())
        if library_path and not any(
            library_path.startswith(accept) for accept in accepted_paths
        ):
            return False
    return True


def farm_cache():
    accepter_vars = [
        os.environ[var].split(os.pathsep)
        for var in ["SIDEFXLABS", "HIS"]
        if var in os.environ
    ]
    accepted_paths = [
        os.path.normpath(path) for path in itertools.chain.from_iterable(accepter_vars)
    ]

    selected_nodes = hou.selectedNodes()
    cache_nodes = []
    for node in selected_nodes:
        if node.parm("execute"):
            inputs = list(node.inputs()) + [node]
            while inputs:
                for input in inputs:
                    if not check_node(input, accepted_paths):
                        error_dialog(
                            "Farm Cache", f"{input} is not a node available to the farm"
                        )
                        return
                    inputs.pop(0)
                    inputs.extend(input.inputs())

            cache_nodes.append(node)

    cache_nodes = hou.sortedNodes(tuple(cache_nodes))
    
    print(cache_nodes)
