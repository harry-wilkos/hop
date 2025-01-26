import os
from hop.dl.util import file_name, discord


def __main__(*args):
    deadlinePlugin = args[0]
    node = os.path.dirname(deadlinePlugin.GetPluginInfoEntry("node_path"))
    name = deadlinePlugin.GetJob().JobName()
    message = f':checkered_flag: **{node}** in **{name}** finished caching :checkered_flag:'
    discord(deadlinePlugin, message)
