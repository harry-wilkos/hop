import os
from hop.dl.util import file_name, discord


def __main__(*args):
    deadlinePlugin = args[0]
    file = file_name(deadlinePlugin.GetPluginInfoEntry("hip_file"))
    node = os.path.dirname(deadlinePlugin.GetPluginInfoEntry("node_path"))
    message = f':green_circle: **{node}** in **{file}** started caching :green_circle:'
    discord(deadlinePlugin, message)
