from hop.shot_management import Shot
from hop.util import get_collection
from hop.util.hou_helpers import error_dialog, expand_path

collection = get_collection("shots", "active_shots")


def load_shot_menu() -> list:
    shots = [int(-1), "Create New Shot..."]
    for shot in collection.find({}):
        shots.append(shot["shot_number"])
        shots.append(f"Shot {shot['shot_number']:02}")
    return shots


def load(kwargs: dict) -> None:
    node = kwargs["node"]
    shot = get_collection("shots", "active_shots").find_one({
        "shot_number": node.evalParm("load_shot")
    })
    if shot:
        shot["frame_rangex"] = shot["start_frame"]
        shot["frame_rangey"] = shot["end_frame"]
        for key, value in shot.items():
            parm = node.parm(key)
            if parm:
                parm.set(value)
    else:
        for parm in node.parms():
            if parm.name() not in ["loaded_shot", "shot_backend"]:
                parm.revertToDefaults()


def publish(kwargs: dict) -> None:
    node = kwargs["node"]
    loaded_shot = node.evalParm("load_shot")
    start_frame = node.evalParm("frame_rangex")
    end_frame = node.evalParm("frame_rangey")
    cam = node.evalParm("cam")
    plate = node.parm("plate").rawValue()

    if loaded_shot == -1:
        shot = Shot(start_frame, end_frame, cam, plate)
    else:
        shot = Shot(shot_number=loaded_shot)
        if shot is None:
            error_dialog("Publish Shot", "Cannot find shot")
            return
        elif shot.shot_data is not None:
            if (
                shot.shot_data["start_frame"] != start_frame
                or shot.shot_data["end_frame"] != end_frame
            ):
                shot.update.frame_range(start_frame, end_frame)
            if expand_path(shot.shot_data["cam"]) != cam:
                shot.update.camera(cam)
            if shot.shot_data["plate"] != plate:
                shot.update.plate(plate)
    shot.publish()
    if shot.shot_data is not None:
        node.parm("load_shot").set(shot.shot_data["shot_number"])
        load(kwargs)
