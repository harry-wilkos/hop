import os
from hop.dl import discord

def __main__(*args):
    deadlinePlugin = args[0]
    output = os.path.dirname(deadlinePlugin.GetPluginInfoEntry("output"))
    os.makedirs(output, exist_ok=True)
    if deadlinePlugin.GetBooleanPluginInfoEntry("discord"):
        job = deadlinePlugin.GetJob()
        name = job.JobName
        node = deadlinePlugin.GetPluginInfoEntry("node_path")
        message = (
            f":art: **{node}** in **{name}** started rendering :art:"
        )
        discord(deadlinePlugin, message)

