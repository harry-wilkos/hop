from typing import TYPE_CHECKING
from ..util.hou_helpers import expand_path, confirmation_dialog, error_dialog
from ..util import alembic_helpers
import os

try:
    import hou
except ModuleNotFoundError:
    from ..util.hou_helpers import import_hou

    hou = import_hou()

if TYPE_CHECKING:
    from .shot_class import Shot


def update_camera(shot: "Shot", cam: str) -> bool:
    if shot.shot_data is None:
        return False

    cam_file = expand_path(cam)
    if cam_file is None or cam_file.split(".")[-1] != "abc":
        error_dialog("Update Camera", "Invalid Camera")
        return False

    alembic_info = alembic_helpers.frame_info(cam_file, int(os.environ["FPS"]))
    if alembic_info and (
        alembic_info[0] != shot.shot_data["start_frame"]
        or alembic_info[1] != shot.shot_data["end_frame"]
    ):
        if not confirmation_dialog(
            title="Update Camera",
            text=f"The camera's frame range {alembic_info[0]} - {alembic_info[1]} doesn't match the input frame range",
        ):
            return False

    ripped_cam_path = ["shots", "active_shots", str(shot.shot_data["_id"]), "camera"]
    shot.shot_data["cam_path"] = alembic_helpers.find_cam_paths(cam_file)[0]
    shot.shot_data["cam"] = f"{os.path.join('$HOP', *ripped_cam_path)}.abc"
    shot.rip_files.append((cam_file, ripped_cam_path))
    return True