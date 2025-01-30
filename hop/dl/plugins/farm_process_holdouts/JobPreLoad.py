import os
from hop.hou.util import convert_exr

def __main__(deadlinePlugin):
        start_frame = f"{deadlinePlugin.GetStartFrame():04d}"
        output_path = deadlinePlugin.GetPluginInfoEntry("output")
        exrs = [
            os.path.join(path, f"{start_frame}.exr")
            for path in deadlinePlugin.GetPluginInfoEntry("exrs").split(";")
        ]
        for exr in exrs:
            convert_exr(exr, os.path.join(output_path, f"{start_frame}.png"))

