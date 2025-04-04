import os
import subprocess
from pathlib import Path
from hop.dl.util import discord
import string
import random


def __main__(*args):
    deadlinePlugin = args[0]
    job = deadlinePlugin.GetJob()
    name = job.JobName

    env = os.environ.copy()
    env_keys = job.GetJobEnvironmentKeys()
    for key in env_keys:
        env[key] = job.GetJobEnvironmentKeyValue(key)

    output_dir = deadlinePlugin.GetPluginInfoEntry("output")

    mp4 = str(
        Path(env["HOP_TEMP"])
        / f"{''.join(random.choices(string.ascii_letters + string.digits, k=4))}.mp4"
    )
    cmd = [
        "ffmpeg",
        "-framerate",
        env["FPS"],
        "-start_number",
        str(job.JobFramesList[0]),
        "-i",
        output_dir.replace("####", "%04d"),
        "-vf",
        "scale=-1:720,format=yuv420p",
        "-c:v",
        "libx264",
        mp4,
    ]

    deadlinePlugin.LogInfo(f"Subprocess Command: {cmd}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    deadlinePlugin.LogInfo(f"Subprocess Output: {result.stdout.strip()}")
    error = result.stderr.strip()
    if error:
        deadlinePlugin.LogWarning(f"Subprocess Error: {error}")

    node = deadlinePlugin.GetPluginInfoEntry("node_path")
    discord(
        deadlinePlugin, f":tada: **{node}** in **{name}** finished rendering :tada:"
    )
    discord(deadlinePlugin, f":eyes: **{name}** preview :eyes:", mp4.replace("\\", "/"))

