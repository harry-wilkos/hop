import os
from pathlib import Path
import subprocess


def __main__(*args):
    deadlinePlugin = args[0]
    job = deadlinePlugin.GetJob()
    env = os.environ.copy()
    env_keys = job.GetJobEnvironmentKeys()
    for key in env_keys:
        env[key] = job.GetJobEnvironmentKeyValue(key)

    start_frame = f"{deadlinePlugin.GetStartFrame():04d}"
    output_dir = Path(deadlinePlugin.GetPluginInfoEntry("output"))
    exrs = [
        os.path.join(path, f"{start_frame}.exr")
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

