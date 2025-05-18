from pathlib import Path
import os
import subprocess


def __main__(*args):
    deadlinePlugin = args[0]
    job = deadlinePlugin.GetJob()
    output = Path(deadlinePlugin.GetPluginInfoEntry("output"))
    output.mkdir(exist_ok=True)

    env = os.environ.copy()
    env_keys = job.GetJobEnvironmentKeys()
    for key in env_keys:
        env[key] = job.GetJobEnvironmentKeyValue(key)
    files = deadlinePlugin.GetPluginInfoEntry("renders").split(";")
    script = f"from hop.util import get_collection; from pymongo.collection import ObjectId; get_collection('shots', 'active_shots').update_one({{'_id': ObjectId('{Path(files[0]).parts[-4]}')}}, {{'$push': {{'render_versions':{files}}}}})"
    cmd = [os.environ["PYTHON"], "-c", script]
    deadlinePlugin.LogInfo(f"Subprocess Command: {cmd}")

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    deadlinePlugin.LogInfo(f"Subprocess Output: {result.stdout.strip()}")
    error = result.stderr.strip()
    if error:
        deadlinePlugin.LogWarning(f"Subprocess Error: {error}")
