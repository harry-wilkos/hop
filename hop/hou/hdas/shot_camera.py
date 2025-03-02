from hop.util import get_collection
from pymongo.collection import ObjectId
import hou
import os

collection = get_collection("shots", "active_shots")


def load_shot_menu() -> list:
    shots = ["", "Select Shot..."]
    for shot in collection.find({}).sort("shot_number", 1):
        shots.append(str(shot["_id"]))
        shots.append(f"Shot {shot['shot_number']:02}")
    return shots


def load_camera(kwargs):
    node = kwargs["node"]
    shot = (
        kwargs["script_value"]
        if kwargs["script_value"] != "0"
        else node.evalParm("shot")
    )
    cam = ""
    cam_path = ""
    back_plate = ""
    if shot and (shot_dict := collection.find_one({"_id": ObjectId(shot)})):
        cam = shot_dict["cam"]
        cam_path = shot_dict["cam_path"]
        back_plate = shot_dict["back_plate"]
        finish = shot_dict["end_frame"] - shot_dict["start_frame"]
        hou.setFps(int(os.environ.get("FPS")), False, True, True)
        hou.playbar.setFrameRange(1001, 1001 + finish)
        hou.playbar.setPlaybackRange(1001, 1001 + finish)
        hou.setFrame(1001)

    node.parm("cam").set(cam)
    node.parm("cam_path").set(cam_path)
    node.parm("back_plate").set(back_plate)
