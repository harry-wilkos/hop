from hop.dl import discord
import os
import subprocess


def __main__(*args):
    deadlinePlugin = args[0]
    job = deadlinePlugin.GetJob()
    hython = deadlinePlugin.GetConfigEntry("hython")
    node = deadlinePlugin.GetPluginInfoEntry("node_path")
    hip = deadlinePlugin.GetPluginInfoEntry("hip_file")
    if deadlinePlugin.GetBooleanPluginInfoEntry("discord"):
        name = job.JobName
        message = (
            f":green_circle: **{node}** in **{name}** started rendering :green_circle:"
        )
        discord(deadlinePlugin, message)
    env = os.environ.copy()
    env_keys = job.GetJobEnvironmentKeys()
    for key in env_keys:
        env[key] = job.GetJobEnvironmentKeyValue(key)
    script = (
        f"from hop.hou.hdas import karma_rop; karma_rop.export({{'node': '{node}'}})"
    )
    cmd = [hython, hip, "-c", script]
    deadlinePlugin.LogInfo(f"Subprocess Command: {cmd}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    deadlinePlugin.LogInfo(f"Subprocess Output: {result.stdout.strip()}")
    error = result.stderr.strip()
    if error:
        deadlinePlugin.LogWarning(f"Subprocess Error: {error}")
