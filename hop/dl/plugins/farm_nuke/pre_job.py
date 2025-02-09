import os
def __main__(*args):
    deadlinePlugin = args[0]
    output = os.path.dirname(deadlinePlugin.GetPluginInfoEntry("output"))
    os.makedirs(output, exist_ok=True)
