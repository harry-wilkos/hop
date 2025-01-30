import os
import subprocess
from glob import glob
from pathlib import Path
from hop.dl.util import discord


def __main__(*args):
    deadlinePlugin = args[0]
    job = deadlinePlugin.GetJob()
    env = os.environ.copy()
    env_keys = job.GetJobEnvironmentKeys()
    for key in env_keys:
        env[key] = job.GetJobEnvironmentKeyValue(key)

    output_dir = deadlinePlugin.GetPluginInfoEntry("output")

    pngs = sorted(glob(os.path.join(output_dir, "*.png")))
    mp4 = os.path.join(output_dir, "output.mp4")
    cmd = [
        "ffmpeg",
        "-framerate",
        env["FPS"],
        "-start_number",
        Path(pngs[0]).stem,
        "-i",
        os.path.join(output_dir, "%04d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        mp4,
    ]

    deadlinePlugin.LogInfo(f"Subprocess Command: {cmd}")

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    deadlinePlugin.LogInfo(f"Subprocess Output: {result.stdout.strip()}")
    error = result.stderr.strip()
    if error:
        deadlinePlugin.LogWarning(f"Subprocess Error: {error}")

    discord(deadlinePlugin, f":eyes: {job.JobName} preview:eyes:", mp4)

