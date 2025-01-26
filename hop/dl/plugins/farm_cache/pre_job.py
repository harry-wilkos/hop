import os
from hop.dl import discord


def __main__(*args):
    deadlinePlugin = args[0]
    node = os.path.dirname(deadlinePlugin.GetPluginInfoEntry("node_path"))
    name = deadlinePlugin.GetJob().JobName
    message = f":green_circle: **{node}** in **{name}** started caching :green_circle:"
    discord(deadlinePlugin, message)
