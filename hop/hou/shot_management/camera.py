from typing import TYPE_CHECKING
from hop.hou.util import expand_path, confirmation_dialog, error_dialog, alembic_helpers
import os
import random
import string

if TYPE_CHECKING:
    from hop.hou.shot_management import Shot


def update_camera(shot: "Shot", cam: str) -> bool:
    if shot.shot_data is None:
        return False

    cam_file = expand_path(cam)
    if cam_file is None or cam_file.split(".")[-1] != "abc":
        error_dialog("Update Camera", "Invalid Camera")
        return False

    alembic_info = alembic_helpers.frame_info(cam_file, int(os.environ["FPS"]))
    if alembic_info[0] != 1001:
        error_dialog("Update Camera", "Camera doesn't start at 1001")
        return False

    if alembic_info and (
        (camera_len := alembic_info[1] - alembic_info[0])
        < (shot_len := shot.shot_data["end_frame"] - shot.shot_data["start_frame"])
    ):
        if not confirmation_dialog(
            title="Update Camera",
            text=f"The camera's frame length {camera_len} doesn't match the input frame range with padding {shot_len}",
        ):
            return False
        shot.cam_checked = True

    ripped_cam_path = ["shots", "active_shots", str(shot.shot_data["_id"]), ''.join(random.choices(string.ascii_letters + string.digits, k=4))]
    shot.shot_data["cam_path"] = alembic_helpers.find_cam_paths(cam_file)[0]
    shot.shot_data["geo_paths"] = alembic_helpers.find_geo_paths(cam_file)
    shot.shot_data["cam"] = f"{os.path.join('$HOP', *ripped_cam_path)}.abc"
    shot.rip_files.append((cam_file, ripped_cam_path))
    return True
