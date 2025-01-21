import os
import subprocess
import sys
from tempfile import NamedTemporaryFile


def set_env(vars: list):
    for index, var in enumerate(vars):
        yield f"EnvironmentKeyValue{index}={var}={os.environ[var]}\n"


def create_job(
    name: str,
    comment: str,
    start: int,
    end: int,
    stepping: int,
    chunk: int,
    plugin: str,
    path: str,
    pool: str,
    batch_name: str | None,
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
    job_file.write(f"CustomPluginDirectory={path}")
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
    ]):
        job_file.write(var)
    job_file.close()
    return job_file.name


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
