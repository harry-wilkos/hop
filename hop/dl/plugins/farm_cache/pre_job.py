import os
import subprocess
from hop.dl.util import file_name


def __main__(*args):
    deadlinePlugin = args[0]

    job = deadlinePlugin.GetJob()
    env = os.environ.copy()
    env_keys = job.GetJobEnvironmentKeys()
    for key in env_keys:
        env[key] = job.GetJobEnvironmentKeyValue(key)

    file = file_name(deadlinePlugin.GetPluginInfoEntry("hip_file"))
    node = deadlinePlugin.GetPluginInfoEntry("node")

    script = f"from hop.util import post; post('discord', {{'message': ':green_circle: **{node}** in **{file}** started caching :green_circle:'}})"
    cmd = [os.environ["PYTHON"], "-c", script]

    deadlinePlugin.LogInfo(f"Subprocess Command: {cmd}")

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    deadlinePlugin.LogInfo(f"Subprocess Output: {result.stdout.strip()}")
    error = result.stderr.strip()
    if error:
        deadlinePlugin.LogWarning(f"Subprocess Error: {error}")
