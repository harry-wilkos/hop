from pathlib import Path
from hop.dl import discord
import os
import subprocess

def __main__(*args):
    deadlinePlugin = args[0]
    job = deadlinePlugin.GetJob()
    shot = job.JobName
    holdout = job.JobComment
    message = (
        f":frame_photo:  **{holdout}** for **{shot}** finished rendering :frame_photo:"
    )
    discord(deadlinePlugin, message)

    env = os.environ.copy()
    env_keys = job.GetJobEnvironmentKeys()
    for key in env_keys:
        env[key] = job.GetJobEnvironmentKeyValue(key)
    file = deadlinePlugin.GetPluginInfoEntry("output")
    script = f"from hop.util import get_collection; from pymongo.collection import ObjectId; get_collection('shots', 'active_shots').update({{'_id': ObjectID('{Path(file).parts[-3]}'}}), {{'$push': '{file}'}})"
    cmd = [os.environ["PYTHON"], "-c", script]
    deadlinePlugin.LogInfo(f"Subprocess Command: {cmd}")

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    deadlinePlugin.LogInfo(f"Subprocess Output: {result.stdout.strip()}")
    error = result.stderr.strip()
    if error:
        deadlinePlugin.LogWarning(f"Subprocess Error: {error}")

