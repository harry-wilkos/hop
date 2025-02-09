from hop.dl import discord


def __main__(*args):
    deadlinePlugin = args[0]
    job = deadlinePlugin.GetJob()
    name = job.JobName
    node = deadlinePlugin.GetPluginInfoEntry("node_path")
    message = f":tada: **{node}** in **{name}** finished caching :tada:"
    discord(deadlinePlugin, message)

