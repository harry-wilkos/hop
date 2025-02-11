from hop.hou.shot_management import Shot
from hop.util import get_collection
from hop.hou.util.helpers import error_dialog, confirmation_dialog

try:
    import hou
except ImportError:
    from hop.hou.util import import_hou

    hou = import_hou()


def load_frame_range(uievent) -> None:
    node = uievent.selected.item
    if node.evalParm("load_shot") != -1:
        padding = node.evalParm("padding")
        start = node.evalParm("frame_rangex") - padding
        end = node.evalParm("frame_rangey") + padding
        hou.playbar.setFrameRange(start, end)
        hou.playbar.setPlaybackRange(start, end)
    return


def load_shot_menu() -> list:
    collection = get_collection("shots", "active_shots")
    shots = [int(-1), "Create New Shot..."]
    for shot in collection.find({}).sort("shot_number", 1):
        shots.append(shot["shot_number"])
        shots.append(f"Shot {shot['shot_number']:02}")
    return shots


def load(kwargs: dict) -> None:
    node = kwargs["node"]
    collection = get_collection("shots", "active_shots")
    shot = collection.find_one({"shot_number": node.evalParm("load_shot")})
    if shot:
        shot["frame_rangex"] = shot["start_frame"]
        shot["frame_rangey"] = shot["end_frame"]
        hou.setFrame(1001)
        node.parm("render_version").set(len(shot["render_versions"]) + 1)
        for key, value in shot.items():
            parm = node.parm(key)
            if parm:
                parm.set(value)
    else:
        for parm in node.parms():
            try:
                if parm.name() not in ["loaded_shot", "shot_backend"]:
                        parm.revertToDefaults()
            except hou.ObjectWasDeleted:
                continue
    padding = node.evalParm("padding")
    start = node.evalParm("frame_rangex") - padding
    end = node.evalParm("frame_rangey") + padding
    finish = end - start
    hou.playbar.setFrameRange(1001, 1001 + finish)
    hou.playbar.setPlaybackRange(1001 , 1001 + finish)


def publish(kwargs: dict) -> None:
    node = kwargs["node"]
    loaded_shot = node.evalParm("load_shot")
    start_frame = node.evalParm("frame_rangex")
    end_frame = node.evalParm("frame_rangey")
    cam = node.parm("cam").rawValue()
    st_map = node.parm("st_map").rawValue()
    padding = node.evalParm("padding")
    plate = node.parm("plate").rawValue()
    description = node.evalParm("description")

    if loaded_shot == -1:
        shot = Shot(start_frame, end_frame, padding, cam, plate, st_map, description)
    else:
        shot = Shot(shot_number=loaded_shot)
        if shot is None:
            error_dialog("Publish Shot", "Cannot find shot")
            return
        else:
            padding_check = False
            if shot.shot_data is not None and (
                shot.shot_data["start_frame"] != start_frame
                or shot.shot_data["end_frame"] != end_frame
            ):
                shot.update.frame_range(start_frame, end_frame)
                padding_check = True
            if shot.shot_data is not None and shot.shot_data["cam"] != cam:
                shot.update.camera(cam)
                padding_check = True
            if shot.shot_data is not None and shot.shot_data["plate"] != plate:
                shot.update.plate(plate)
                padding_check = True
            if (
                shot.shot_data is not None
                and not padding_check
                and shot.shot_data["padding"] != padding
            ):
                shot.update.padding(padding)
            if shot.shot_data is not None and shot.shot_data["st_map"] != st_map:
                shot.update.st_map(st_map)
            if (
                shot.shot_data is not None
                and shot.shot_data["description"] != description
            ):
                shot.update.description(description)

    shot.publish()
    if shot.shot_data is not None:
        node.parm("load_shot").set(shot.shot_data["shot_number"])
        load(kwargs)


def delete(kwargs: dict) -> None:
    node = kwargs["node"]
    loaded_shot = node.evalParm("load_shot")
    if loaded_shot != -1 and confirmation_dialog(
        "Delete Shot", f"Delete shot {loaded_shot}?"
    ):
        if Shot(shot_number=loaded_shot).delete():
            node.parm("load_shot").set(-1)
            load(kwargs)
