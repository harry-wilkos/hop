from hop.dl import discord


def __main__(*args):
    deadlinePlugin = args[0]
    node = deadlinePlugin.GetPluginInfoEntry("node_path")
    name = deadlinePlugin.GetJob().JobName
    message = (
        f":checkered_flag: **{node}** in **{name}** finished rendering :checkered_flag:"
    )
    discord(deadlinePlugin, message)
