import os
from glob import glob
from typing import TYPE_CHECKING

import clique
import ffmpeg
import OpenEXR

from hop.util.hou_helpers import error_dialog, expand_path

if TYPE_CHECKING:
    from hop.shot_management.shot_class import Shot


def generate_back_plate(shot: "Shot") -> bool:
    if shot.shot_data is None:
        return False

    shot_plate = shot.shot_data["plate"]
    plate_dir = expand_path(os.path.dirname(shot_plate))
    if plate_dir is None:
        return False

    plate = os.path.join(plate_dir, os.path.basename(shot_plate))
    exrs = sorted(glob(plate.replace("####", "*")))
    assembly = clique.assemble(exrs)[0][0]
    frames = sorted(assembly.indexes)
    back_plate_path = os.path.join(
        os.environ["HOP"],
        "shots",
        "active_shots",
        str(shot.shot_data["_id"]),
        "back_plate",
        "%04d.png",
    )

    os.makedirs(os.path.dirname(back_plate_path), exist_ok=True)
    (
        ffmpeg.input(
            plate.replace("####", "%04d"),
            framerate=os.environ["FPS"],
            start_number=frames[0],
        )
        .filter("scale", 1280, 720)
        .filter("format", "rgb24")
        .filter("curves", r="0.3/0 0.6/1", g="0.3/0 0.6/1", b="0.3/0 0.6/1")
        .output(back_plate_path)
        .run()
    )
    back_plates = sorted(glob(back_plate_path.replace("%04d", "*")))
    frame = shot.shot_data["start_frame"]
    back_plate_dir = os.path.dirname(back_plate_path)
    for back_plate in back_plates:
        new_name = os.path.join(back_plate_dir, f"{frame:04d}.png")
        os.rename(back_plate, new_name)
        frame += 1

    shot.shot_data["back_plate"] = back_plate_path.replace("%04d", "$F").replace(
        os.environ["HOP"], "$HOP"
    )
    return True


def update_plate(shot: "Shot", plate: str) -> bool:
    if shot.shot_data is None:
        return False
    plate_dir = expand_path(os.path.dirname(plate))
    if plate_dir is None or plate.split(".")[-1] != "exr":
        error_dialog("Update Plate", "Invalid Plate")
        return False
    name = os.path.basename(plate)
    search = name.replace("$F", "*").replace("####", "*")
    files = os.path.join(plate_dir, search)
    exrs = sorted(glob(files))

    if not OpenEXR.isOpenExrFile(exrs[0]):
        error_dialog("Update Plate", "Invalid Plate")
        return False

    file = OpenEXR.InputFile(exrs[0])
    rational = file.header()["framesPerSecond"]
    if rational.n // rational.d != int(os.environ["FPS"]):
        error_dialog("Update Plate", f"Plate doesn't match {os.environ['FPS']} fps")
        return False

    assembly = clique.assemble(exrs)[0][0]
    frames = sorted(assembly.indexes)
    if len(frames) < shot.shot_data["end_frame"] - shot.shot_data["start_frame"]:
        error_dialog("Update Plate", "Not enough frames in plate for given frame range")
        return False
    ripped_plate_path = ["shots", "active_shots", str(shot.shot_data["_id"]), "plate"]
    for index, file in enumerate(exrs):
        shot.rip_files.append((file, ripped_plate_path + [f"{frames[index]}"]))

    shot.shot_data["plate"] = os.path.join("$HOP", *ripped_plate_path, "####.exr")
    shot.new_plate = True
    return True
