import os
from glob import glob
from typing import TYPE_CHECKING
import clique
import OpenEXR
import OpenImageIO as oiio
from pathlib import Path
from hop.hou.util import error_dialog, expand_path, alembic_helpers, confirmation_dialog
from hop.hou.util import convert_exr
from hop.util import MultiProcess

if TYPE_CHECKING:
    from hop.hou.shot_management import Shot


def generate_back_plate(progress, shot: "Shot") -> bool:
    if shot.shot_data is None:
        return False

    shot_plate = shot.shot_data["plate"]
    plate_dir = expand_path(os.path.dirname(shot_plate))
    if plate_dir is None:
        return False

    plate = os.path.join(plate_dir, os.path.basename(shot_plate))
    exrs = sorted(glob(plate.replace("####", "*")))
    back_plate_path = os.path.join(
        os.environ["HOP"],
        "shots",
        "active_shots",
        str(shot.shot_data["_id"]),
        "back_plate",
    )
    os.makedirs(back_plate_path, exist_ok=True)
    args = []
    frame = 1001
    for count, exr in enumerate(exrs):
        output = os.path.join(back_plate_path, f"bp.{(frame + count):04d}.png")
        if os.path.exists(output):
            os.remove(output)
        args.append((exr, output))
        if not convert_exr(exr, output):
            return False
        progress.updateProgress(((count + 1) / len(exrs)) * 0.5)

    if False in MultiProcess(convert_exr, args).execute().retrieve():
        return False
    shot.shot_data["back_plate"] = os.path.join(back_plate_path, "bp.$F.png").replace(
        os.environ["HOP"], "$HOP"
    )
    return True


def update_padding(shot: "Shot", padding: int):
    if shot.shot_data:
        if shot.shot_data["plate"]:
            plate_dir = expand_path(os.path.dirname(shot.shot_data["plate"]))
            if plate_dir:
                name = os.path.basename(shot.shot_data["plate"])
                search = name.replace("$F", "*").replace("####", "*")
                files = os.path.join(plate_dir, search)
                exrs = sorted(glob(files))
                if len(exrs) < shot.shot_data["end_frame"] - shot.shot_data[
                    "start_frame"
                ] + (2 * padding):
                    error_dialog(
                        "Update Plate",
                        "Not enough frames in plate for given frame range",
                    )
                    return False
            # if shot.shot_data["back_plate"]:
            #     back_plates = shot.shot_data["back_plate"].replace(
            #         "$HOP", os.environ["HOP"]
            #     )
            #     pngs = sorted(glob(back_plates.replace("$F", "*")))
            #     back_plate_dir = os.path.dirname(pngs[0])
            #     for count, back_plate in enumerate(pngs):
            #         new_name = os.path.join(
            #             back_plate_dir,
            #             f"bp.{shot.shot_data['start_frame'] - padding + count:04d}.png",
            #         )
            #         os.rename(back_plate, new_name)

        if shot.shot_data["cam"] and not shot.cam_checked:
            cam_file = expand_path(shot.shot_data["cam"])
            if cam_file:
                alembic_info = alembic_helpers.frame_info(
                    cam_file, int(os.environ["FPS"])
                )
                if alembic_info and (
                    (camera_len := alembic_info[1] - alembic_info[0])
                    < (
                        shot_len := shot.shot_data["end_frame"]
                        - shot.shot_data["start_frame"]
                    )
                ):
                    if not confirmation_dialog(
                        title="Update Camera",
                        text=f"The camera's frame length {camera_len} doesn't match the input frame range with padding {shot_len}",
                    ):
                        return False
                    shot.cam_checked = True
        shot.shot_data["padding"] = padding
    return True


def update_st_map(shot: "Shot", map: str):
    if shot.shot_data is None:
        return False
    path = expand_path(map)
    if path is None:
        error_dialog("Update ST-Map", "Invalid ST-Map")
        return False
    image = oiio.ImageInput.open(path)
    width = image.spec().width
    height = image.spec().height
    image.close()

    target_res = os.environ["RES"].split()
    if width != int(target_res[0]) and height != int(target_res[1]):
        error_dialog(
            "Update ST-Map", f"ST-Map doesn't match {target_res[0]} x {target_res[1]}"
        )
        return False
    ripped_map_path = ["shots", "active_shots", str(shot.shot_data["_id"])]
    shot.rip_files.append((path, ripped_map_path + ["st_map"]))
    shot.shot_data["st_map"] = os.path.join(
        "$HOP", *ripped_map_path, "st_map" + Path(path).suffix
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
    header = file.header()
    if header["framesPerSecond"].n // header["framesPerSecond"].d != int(
        os.environ["FPS"]
    ):
        error_dialog("Update Plate", f"Plate doesn't match {os.environ['FPS']} fps")
        return False

    resolution = (
        header["dataWindow"].max.x - header["dataWindow"].min.x + 1,
        header["dataWindow"].max.y - header["dataWindow"].min.y + 1,
    )
    target_res = os.environ["RES"].split()
    if resolution[0] != int(target_res[0]) and resolution[1] != int(target_res[1]):
        error_dialog(
            "Update Plate", f"Plate doesn't match {target_res[0]} x {target_res[1]}"
        )
        return False

    assembly = clique.assemble(exrs)[0][0]
    frames = sorted(assembly.indexes)
    if len(frames) < shot.shot_data["end_frame"] - shot.shot_data["start_frame"] + (
        shot.shot_data["padding"] * 2
    ):
        error_dialog(
            "Update Plate",
            "Not enough frames in plate for given frame range with padding",
        )
        return False
    ripped_plate_path = ["shots", "active_shots", str(shot.shot_data["_id"]), "plate"]
    for index, file in enumerate(exrs):
        shot.rip_files.append((file, ripped_plate_path + [f"{frames[index]}"]))

    shot.shot_data["plate"] = os.path.join("$HOP", *ripped_plate_path, "####.exr")
    shot.new_plate = True
    if shot.shot_data["st_map"] and not update_st_map(shot, shot.shot_data["st_map"]):
        return False
    return True
