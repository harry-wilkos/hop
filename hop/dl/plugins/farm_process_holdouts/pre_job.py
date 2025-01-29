from pathlib import Path


def __main__(*args):
    deadlinePlugin = args[0]
    output = Path(deadlinePlugin.GetPluginInfoEntry("output"))
    output.mkdir(exist_ok=True)
