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

    start_frame = int(deadlinePlugin.GetStartFrame())
    end_frame = int(deadlinePlugin.GetEndFrame())
    output_dir = Path(deadlinePlugin.GetPluginInfoEntry("output"))
    for frame in range(start_frame, end_frame):
        format_frame = f"{frame:04d}"
        exrs = [
            os.path.join(path, f"{format_frame}.exr")
            for path in deadlinePlugin.GetPluginInfoEntry("exrs").split(";")
        ]
        for exr in exrs:
            parts = Path(exr).parts
            folder = output_dir / parts[-2]
            folder.mkdir(parents=True, exist_ok=True)
            cmd = [
                "ocioconvert",
                exr,
                "role_rendering",
                folder / parts[-1],
                env["VIEW"],
            ]

            deadlinePlugin.LogInfo(f"Subprocess Command: {cmd}")

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            deadlinePlugin.LogInfo(f"Subprocess Output: {result.stdout.strip()}")
            error = result.stderr.strip()
            if error:
                deadlinePlugin.LogWarning(f"Subprocess Error: {error}")
