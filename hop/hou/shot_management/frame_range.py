import copy
from typing import TYPE_CHECKING
from glob import glob
import os
from hop.hou.interfaces import merge_shots
from hop.hou.util import confirmation_dialog, error_dialog, alembic_helpers, expand_path

if TYPE_CHECKING:
    from hop.hou.shot_management import Shot


def find_overlapping_shots(
    shot: "Shot", start_frame: int, end_frame: int
) -> tuple | None:
    if shot.shot_data is None:
        return None

    shots_to_trim, shots_to_merge = [], []
    shot_to_merge_data = {
        key: [] for key in ["cam", "plate", "st_map", "assets"]
    }

    for existing_shot in shot.collection.find({}):
        if str(existing_shot["_id"]) == str(shot.shot_data["_id"]):
            continue
        shot_start, shot_end = existing_shot["start_frame"], existing_shot["end_frame"]
        intersection_start, intersection_end = (
            max(start_frame, shot_start),
            min(end_frame, shot_end),
        )

        if intersection_start <= intersection_end:
            existing_shot.update({
                "intersection_start": intersection_start,
                "intersection_end": intersection_end,
            })

            if (
                intersection_start == start_frame
                and intersection_end < end_frame
                and shot_start != start_frame
            ):
                existing_shot["trim_direction"] = -1  # Overlap at start
                shots_to_trim.append(existing_shot)
            elif (
                intersection_end == end_frame
                and intersection_start > start_frame
                and shot_end != end_frame
            ):
                existing_shot["trim_direction"] = 1  # Overlap at end
                shots_to_trim.append(existing_shot)
            elif shot_start < start_frame and shot_end > end_frame:
                error_dialog(
                    "Update Frame Range", "Frame range is nested within existing shot"
                )
                return None
            else:
                shots_to_merge.append(existing_shot["shot_number"])
                for key in shot_to_merge_data:
                    value = existing_shot.get(key)
                    shot_to_merge_data[key].append(value if value else None)

    return shots_to_trim, (shots_to_merge, shot_to_merge_data)


def shot_trim(shot: "Shot", overlapping_shots: list) -> bool:
    if not overlapping_shots:
        return True

    if shot.shot_data is None:
        return False

    overlapping_shot_numbers = ", ".join(
        str(shot["shot_number"]) for shot in overlapping_shots
    )
    overlapping_shot_frames = ", ".join(
        f"{shot['intersection_start']} - {shot['intersection_end']}"
        for shot in overlapping_shots
    )

    if not confirmation_dialog(
        title="Update Frame Range",
        text=f"Change the frame range of the following shots: {overlapping_shot_numbers}?",
        details=(
            f"The entered frame range overlaps with existing shots frames: {overlapping_shot_frames}. "
            "Either cancel and change the frame ranges to avoid intersecting with existing shots, "
            "or continue and the mentioned shots will be trimmed."
        ),
    ):
        return False

    for overlapping_shot in overlapping_shots:
        direction = (
            "start_frame" if overlapping_shot["trim_direction"] == 1 else "end_frame"
        )
        new_value = (
            overlapping_shot["intersection_end"] + 1
            if direction == "start_frame"
            else overlapping_shot["intersection_start"] - 1
        )
        shot.collection.update_one(
            {"_id": overlapping_shot["_id"]}, {"$set": {direction: new_value}}
        )

    return True


def shot_merge(
    shot: "Shot", shot_numbers_to_merge: list, shot_data_to_merge: dict
) -> bool:
    if shot.shot_data is None:
        return False

    if all(
        not values or all(value is None for value in values)
        for values in shot_data_to_merge.values()
    ):
        return True

    empty_keys = [key for key, values in shot_data_to_merge.items() if not values]
    for key, _ in shot_data_to_merge.items():
        input_value = shot.shot_data.get(key) if shot.shot_data else None
        shot_data_to_merge[key].insert(0, input_value if input_value else None)

    shot_numbers_to_merge.insert(0, "New Shot")

    for key in empty_keys:
        del shot_data_to_merge[key]

    if any(value != [None] for value in copy.deepcopy(shot_data_to_merge).values()):
        merge_results = merge_shots(shot_data_to_merge, shot_numbers_to_merge)
        if merge_results is None:
            return False

        merge_result_flat = {
            key: next((value for value in values if value is not None), [])
            for key, values in merge_results.items()
            if any(value is not None for value in values)
        }

        for attribute in merge_result_flat:
            if shot.shot_data is not None:
                shot.shot_data[attribute] = merge_result_flat[attribute]

        for shot_number in shot_numbers_to_merge[1:]:
            get_delete_shot = shot.collection.find_one({"shot_number": shot_number})
            if get_delete_shot is not None:
                shot.delete_shots.append(get_delete_shot["_id"])

    return True


def update_shot_num(shot: "Shot") -> bool:
    if shot.shot_data is None:
        return False
    shots_ahead = shot.collection.find({
        "start_frame": {"$gt": shot.shot_data["end_frame"]}
    }).sort("shot_number", 1)
    shot_number = None
    for count, ahead_shot in enumerate(shots_ahead):
        ahead_shot_num = ahead_shot["shot_number"]
        if count == 0:
            shot_number = ahead_shot_num
        shot.collection.update_one(
            {"_id": ahead_shot["_id"]}, {"$set": {"shot_number": ahead_shot_num + 1}}
        )

    if shot_number is None:
        shot_behind_cursor = (
            shot.collection.find({"end_frame": {"$lt": shot.shot_data["start_frame"]}})
            .sort("shot_number", -1)
            .limit(1)
        )
        shot_behind = next(shot_behind_cursor, None)
        shot_number = shot_behind["shot_number"] + 1 if shot_behind else 1

    shot.shot_data["shot_number"] = shot_number
    return True


def update_frame_range(shot: "Shot", start_frame: int, end_frame: int) -> bool:
    if shot.shot_data is None or start_frame >= end_frame or start_frame < 1001:
        error_dialog("Update Frame Range", "Invalid Frame Range")
        return False

    intersecting_shots = find_overlapping_shots(shot, start_frame, end_frame)
    if intersecting_shots:
        shots_to_trim, (shots_to_merge, shot_data_to_merge) = intersecting_shots
        if shots_to_merge and not shot_merge(shot, shots_to_merge, shot_data_to_merge):
            return False
        if not shot_trim(shot, shots_to_trim):
            return False

    if shot.shot_data["back_plate"]:
        back_plates = shot.shot_data["back_plate"].replace("$HOP", os.environ["HOP"])
        pngs = sorted(glob(back_plates.replace("$F", "*")))
        if len(pngs) < (end_frame - start_frame) + (2 * shot.shot_data["padding"]):
            error_dialog(
                "Update Frame Range",
                "Not enough frames in plate for given frame range and padding",
            )
            return False
        # back_plate_dir = os.path.dirname(pngs[0])
        # temp_names = [
        #     os.path.join(back_plate_dir, f"temp_bp.{i:04d}.png")
        #     for i in range(len(pngs))
        # ]

        # for temp_name, back_plate in zip(temp_names, pngs):
        #     os.rename(back_plate, temp_name)

        # for count, temp_name in enumerate(temp_names):
        #     new_name = os.path.join(
        #         back_plate_dir,
        #         f"bp.{start_frame - shot.shot_data['padding'] + count:04d}.png",
        #     )
        #     os.rename(temp_name, new_name)




    if shot.shot_data["cam"] and not shot.cam_checked:
        cam_file = expand_path(shot.shot_data["cam"])
        if cam_file:
            alembic_info = alembic_helpers.frame_info(cam_file, int(os.environ["FPS"]))
            if alembic_info:
                camera_len = alembic_info[1] - alembic_info[0]
                if camera_len != 0 and camera_len < (shot_len := shot.shot_data["end_frame"] - shot.shot_data["start_frame"])
                    if not confirmation_dialog(
                        title="Update Camera",
                        text=f"The camera's frame length {camera_len} doesn't match the input frame range with padding {shot_len}",
                    ):
                        return False
                    shot.cam_checked = True

    shot.shot_data["start_frame"] = start_frame
    shot.shot_data["end_frame"] = end_frame

    return True
