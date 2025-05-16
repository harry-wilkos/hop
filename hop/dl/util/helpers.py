import os
import subprocess
import sys
from tempfile import NamedTemporaryFile
import re
from pathlib import Path


def set_env(vars: list):
    for index, var in enumerate(vars):
        yield f"EnvironmentKeyValue{index}={var}={os.environ[var]}\n"


def submit_decode(command: str) -> list:
    return re.findall(r"JobID=([a-f0-9]+)", command)


def file_name(path: str):
    name = os.path.basename(path)
    index = name.index(".")
    return name[:index]


def create_job(
    name: str,
    comment: str,
    start: int,
    end: int,
    stepping: int,
    chunk: int,
    plugin: str,
    pool: str,
    batch_name: str | None = None,
    pre_script: bool = False,
    post_script: bool = False,
    job_dependencies: list = [],
    pre_task: bool = False,
    post_task: bool = False,
):
    job_file = NamedTemporaryFile(
        delete=False, mode="w", encoding="utf-16", suffix=".job"
    )
    job_file.write(f"Plugin={plugin}\n")
    if batch_name:
        job_file.write(f"BatchName={batch_name}\n")
    job_file.write(f"Name={name}\n")
    job_file.write(f"Comment={comment}\n")
    job_file.write(f"Frames={start}-{end}:{stepping}\n")
    job_file.write(f"ChunkSize={chunk}\n")
    job_file.write(f"Pool={pool}\n")
    job_file.write(
        f"CustomPluginDirectory={os.path.join(os.environ['DEADLINE_CUSTOM_PATH'], 'plugins')}\n"
    )
    job_file.write("EnableAutoTimeout=False\n")
    job_file.write("TaskTimeoutMinutes=0\n")
    job_file.write("OverrideJobFailureDetection=True\n")
    job_file.write("OverrideTaskFailureDetection=True\n")
    job_file.write("FailureDetectionJobErrors=1\n")
    job_file.write("FailureDetectionTaskErrors=1\n")
    job_file.write("Priority=100\n")
    scripts_path = os.path.join(
        str(Path(__file__).parents[2]),
        "dl",
        "plugins",
        plugin,
    )
    if job_dependencies:
        job_file.write(f"JobDependencies={','.join(job_dependencies)}\n")

    if pre_script:
        job_file.write(f"PreJobScript={os.path.join(scripts_path, 'pre_job.py')}\n")

    if post_script:
        job_file.write(f"PostJobScript={os.path.join(scripts_path, 'post_job.py')}\n")

    if pre_task:
        job_file.write(f"PreTaskScript={os.path.join(scripts_path, 'pre_task.py')}\n")

    if post_task:
        job_file.write(f"PostTaskScript={os.path.join(scripts_path, 'post_task.py')}\n")

    for var in set_env([
        "TWELVEFOLD_ROOT",
        "PYTHON",
        "PYTHONPATH",
        "NUKE_PATH",
        "MAYA_APP_DIR",
        "XBMLANGPATH",
        "MARI_USER_PATH",
        "MAYA_PLUG_IN_PATH",
        "HOUDINI_USER_PREF_DIR",
        "OCIO",
        "MONGO_ADDRESS",
        "API_ADDRESS",
        "FPS",
        "RES",
        "HOP",
        "PATH",
        "HOP_TEMP",
        "CAM",
        "VIEW",
    ]):
        job_file.write(var)
    job_file.close()
    return job_file.name


def discord(deadlinePlugin, message: str, file_path: str | None = None):
    job = deadlinePlugin.GetJob()
    env = os.environ.copy()
    env_keys = job.GetJobEnvironmentKeys()
    for key in env_keys:
        env[key] = job.GetJobEnvironmentKeyValue(key)
    file = f"'{file_path}'" if type(file_path) is str else file_path
    script = f"from hop.util import post; post('discord', {{'message': '{message}'}}, {file})"
    cmd = [os.environ["PYTHON"], "-c", script]

    deadlinePlugin.LogInfo(f"Subprocess Command: {cmd}")

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    deadlinePlugin.LogInfo(f"Subprocess Output: {result.stdout.strip()}")
    error = result.stderr.strip()
    if error:
        deadlinePlugin.LogWarning(f"Subprocess Error: {error}")


# From official Thinkbox repo
def get_deadline():
    deadlineBin = ""
    try:
        deadlineBin = os.environ["DEADLINE_PATH"]
    except KeyError:
        pass
    if deadlineBin == "" and os.path.exists("/Users/Shared/Thinkbox/DEADLINE_PATH"):
        with open("/Users/Shared/Thinkbox/DEADLINE_PATH") as f:
            deadlineBin = f.read().strip()
    deadlineCommand = os.path.join(deadlineBin, "deadlinecommand")
    return deadlineCommand


# From official Thinkbox repo
def call_deadline(arguments, hideWindow=True, readStdout=True):
    deadlineCommand = get_deadline()
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        if hideWindow:
            if hasattr(subprocess, "_subprocess") and hasattr(
                subprocess._subprocess, "STARTF_USESHOWWINDOW"
            ):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
            elif hasattr(subprocess, "STARTF_USESHOWWINDOW"):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            CREATE_NO_WINDOW = 0x08000000
            creationflags = CREATE_NO_WINDOW

    arguments.insert(0, deadlineCommand)
    proc = subprocess.Popen(
        arguments,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )
    output = ""
    if readStdout:
        output = proc.communicate()[0]
    output = output.strip()
    if sys.version_info[0] > 2 and type(output) is bytes:
        output = output.decode()
    return output
