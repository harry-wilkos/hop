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
    node = os.path.dirname(deadlinePlugin.GetPluginInfoEntry("node_path"))


    script = f"from hop.util import post; post('discord', {{'message': ':checkered_flag: **{node}** in **{file}** finished caching :checkered_flag:'}})"
    cmd = [os.environ["PYTHON"], "-c", script]

    deadlinePlugin.LogInfo(f"Subprocess Command: {cmd}")

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    deadlinePlugin.LogInfo(f"Subprocess Output: {result.stdout.strip()}")
    error = result.stderr.strip()
    if error:
        deadlinePlugin.LogWarning(f"Subprocess Error: {error}")
