import os
from hop.dl.util import file_name, discord


def __main__(*args):
    deadlinePlugin = args[0]
    file = file_name(deadlinePlugin.GetPluginInfoEntry("hip_file"))
    node = os.path.dirname(deadlinePlugin.GetPluginInfoEntry("node_path"))
    message = f':checkered_flag: **{node}** in **{file}** finished caching :checkered_flag:'
    discord(deadlinePlugin, message)
