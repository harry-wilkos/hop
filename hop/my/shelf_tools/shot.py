import maya.cmds as cmds
from hop.my.interfaces import load_shot
import os


def create_shot():
    shot = load_shot()
    if shot and shot["cam"] and shot["cam_path"]:
        cam_file_path = os.path.expandvars(shot["cam"])
        if not cmds.pluginInfo("AbcImport", query=True, loaded=True):
            cmds.loadPlugin("AbcImport")
        cmds.AbcImport(cam_file_path, mode="import", filterObjects=shot["cam_path"])
        cmds.playbackOptions(minTime=shot["start_frame"], maxTime=shot["end_frame"])
        cmds.currentTime(shot["start_frame"])
        cam_path = shot["cam_path"].split("/")
        cmds.imagePlane(
            camera=shot["cam_path"].replace("/", "|"),
            name="Plate",
            fileName=shot["back_plate"].replace("$F", "####"),
            showInAllViews=False,
            lookThrough=shot["cam_path"],
        )
        cmds.rename("|".join(cam_path[:-1]), "Camera")
        cmds.rename("|".join(cam_path[:-2]), f"Shot_{shot['shot_number']}")
