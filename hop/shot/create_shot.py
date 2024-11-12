import copy
from pymongo.collection import Collection
from ..interfaces import ShotMerge
from ..util import get_collection

try:
    import hou
except ModuleNotFoundError:
    from ..util.import_hou import import_hou

    hou = import_hou()


# Updates the shot number for the new shot based on frame position
def update_shot_num(
    start_frame: int, end_frame: int, shots_collection: Collection
) -> int:
    shots_ahead = shots_collection.find({"start_frame": {"$gt": end_frame}}).sort(
        "shot_number", 1
    )
    shot_number = None
    for count, ahead_shot in enumerate(shots_ahead):
        ahead_shot_num = ahead_shot["shot_number"]
        if count == 0:
            shot_number = ahead_shot_num
        shots_collection.update_one(
            {"_id": ahead_shot["_id"]}, {"$set": {"shot_number": ahead_shot_num + 1}}
        )

    if shot_number is None:
        shot_behind_cursor = (
            shots_collection.find({"end_frame": {"$lt": start_frame}})
            .sort("shot_number", -1)
            .limit(1)
        )
        shot_behind = next(shot_behind_cursor, None)
        shot_number = shot_behind["shot_number"] + 1 if shot_behind else 1
    return shot_number


# Handles the trimming of overlapping shots based on the start and end frames
def shot_trim(shots_collection: Collection, overlapping_shots: list) -> bool:
    if not overlapping_shots:
        return True

    overlapping_shot_numbers = ", ".join(
        str(shot["trimmed_shot"]["shot_number"]) for shot in overlapping_shots
    )
    overlapping_shot_frames = ", ".join(
        f"{shot['overlap_start']} - {shot['overlap_end']}" for shot in overlapping_shots
    )
    confirm_trim = hou.ui.displayMessage(
        text=f"Change the frame range of the following shots: {overlapping_shot_numbers}?",
        buttons=["OK", "Cancel"],
        severity=hou.severityType.Warning,
        default_choice=1,
        close_choice=1,
        title="Trim Shot",
        help=(
            f"The entered frame range overlaps with existing shots frames: {overlapping_shot_frames}"
        ),
        details=(
            "Either cancel and change the frame ranges to avoid intersecting "
            "with existing shots, or continue and the mentioned shots will be trimmed."
        ),
    )
    if confirm_trim != 0:
        return False

    for shot in overlapping_shots:
        if shot["trim_direction"] == 1:
            shots_collection.update_one(
                {"_id": shot["trimmed_shot"]["_id"]},
                {"$set": {"start_frame": shot["overlap_end"] + 1}},
            )
        else:
            shots_collection.update_one(
                {"_id": shot["trimmed_shot"]["_id"]},
                {"$set": {"end_frame": shot["overlap_start"] - 1}},
            )
    return True


# Handles the merging of new shots with existing shots if there are conflicts
def shot_merge(
    new_shot: dict, shot_attributes: dict, overlapping_shot_numbers: list
) -> bool:
    if not any(shot_attributes[attr] for attr in shot_attributes):
        return True

    empty_keys = []
    for key, values in shot_attributes.items():
        input_value = new_shot[key]
        if (isinstance(input_value, list) and not input_value) or (
            isinstance(input_value, str) and input_value == ""
        ):
            if not values:
                empty_keys.append(key)
            else:
                shot_attributes[key].insert(0, None)
        else:
            shot_attributes[key].insert(0, new_shot[key])

    overlapping_shot_numbers.insert(0, "New Shot")
    for key in empty_keys:
        del shot_attributes[key]

    shot_check = copy.deepcopy(shot_attributes)
    [shot_check[attr].pop(0) for attr in shot_check]
    if any(value != [None] for value in shot_check.values()):
        merge_results = ShotMerge(shot_attributes, overlapping_shot_numbers)
        if merge_results is None:
            return False
        else:
            merge_result_flat = flattern_dict(merge_results)
            for attribute in merge_result_flat:
                new_shot[attribute] = merge_result_flat[attribute]
    return True


# Deletes shots that overlap entirely with the new shot being created
def shot_delete(overlapping_shot_ids: list, shots_collection: Collection):
    for shot_id in overlapping_shot_ids:
        shots_collection.update_one({"_id": shot_id}, {"$set": {"shot_number": None}})
        retired_shots = get_collection("shots", "retired_shots")
        retired_shots.insert_one(shots_collection.find_one({"_id": shot_id}))
        shots_collection.delete_one({"_id": shot_id})

    shots_ahead = shots_collection.find({
        "shot_number": {"$gt": max(overlapping_shot_ids)}
    }).sort("shot_number", 1)
    for ahead_shot in shots_ahead:
        shots_collection.update_one(
            {"_id": ahead_shot["_id"]},
            {"$set": {"shot_number": max(overlapping_shot_ids)}},
        )


# Helper to find overlapping frame ranges
def find_frame_intersects(
    shots_collection: Collection, start_frame: int, end_frame: int
) -> tuple:
    frame_range = range(start_frame, end_frame)
    overlapping_ranges = []
    overlapping_docs = []
    for shot_doc in shots_collection.find({}):
        shot_range = range(shot_doc["start_frame"], shot_doc["end_frame"])
        intersecting_range = range(
            max(frame_range[0], shot_range[0]), min(frame_range[-1], shot_range[-1]) + 1
        )
        if intersecting_range.start <= intersecting_range.stop:
            overlapping_ranges.append([
                intersecting_range.start,
                intersecting_range.stop,
            ])
            overlapping_docs.append(shot_doc)
    return overlapping_ranges, overlapping_docs


def flattern_dict(attribute_dict) -> dict:
    result = {}
    for key, values in attribute_dict.items():
        non_none_values = [value for value in values if value is not None]
        if not non_none_values:
            result[key] = [] if key == "assets" else ""
        elif len(non_none_values) == 1:
            result[key] = non_none_values[0]
    return result


# Main function to create a shot
def create_shot(start_frame: int, end_frame: int, cam: str = "", plate: str = ""):
    if start_frame >= end_frame:
        hou.ui.displayMessage(
            text="Invalid Frame Range",
            severity=hou.severityType.Error,
            title="Create Shot",
        )
        return None

    new_shot = {
        "shot_number": None,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "plate": plate,
        "cam": cam,
        "lights": "",
        "assets": [],
    }
    shots_collection = get_collection("shots", "active_shots")
    overlapping_ranges, overlapping_docs = find_frame_intersects(
        shots_collection, start_frame, end_frame
    )

    if overlapping_ranges:
        shot_attributes = {"cam": [], "plate": [], "lights": [], "assets": []}
        overlapping_shot_numbers = []
        overlapping_shots = []
        overlapping_shot_ids = []

        for index, overlap in enumerate(overlapping_ranges):
            overlap_start, overlap_end = overlap
            trimmed_shot = overlapping_docs[index]
            trim_direction = 0

            if (
                overlap_start == start_frame
                and overlap_end < end_frame
                and trimmed_shot["start_frame"] != start_frame
            ):
                trim_direction = -1  # Clip beginning of frame range
            elif (
                overlap_end == end_frame
                and overlap_start > start_frame
                and trimmed_shot["end_frame"] != end_frame
            ):
                trim_direction = 1  # Clip end of frame range
            elif (
                trimmed_shot["start_frame"] < start_frame
                and trimmed_shot["end_frame"] > end_frame
            ):
                hou.ui.displayMessage(
                    text="Frame range is nested within an existing shot",
                    severity=hou.severityType.Error,
                    title="Create Shot",
                )
                return None
            else:
                overlapping_shot_numbers.append(trimmed_shot["shot_number"])
                overlapping_shot_ids.append(trimmed_shot["_id"])
                for key in shot_attributes:
                    trim_value = trimmed_shot[key]
                    if (isinstance(trim_value, list) and trim_value) or (
                        isinstance(trim_value, str) and trim_value
                    ):
                        shot_attributes[key].append(trim_value)
                    else:
                        shot_attributes[key].append(None)

            if trim_direction != 0:
                overlapping_shots.append({
                    "overlap_start": overlap_start,
                    "overlap_end": overlap_end,
                    "trimmed_shot": trimmed_shot,
                    "trim_direction": trim_direction,
                })
                overlapping_shot_numbers.append(trimmed_shot["shot_number"])
                overlapping_shot_ids.append(trimmed_shot["_id"])

        if not shot_trim(shots_collection, overlapping_shots):
            return None
        if not shot_merge(new_shot, shot_attributes, overlapping_shot_numbers):
            return None
        shot_delete(overlapping_shot_ids, shots_collection)

    new_shot["shot_number"] = update_shot_num(start_frame, end_frame, shots_collection)
    shots_collection.insert_one(new_shot)
    return new_shot


if __name__ == "__main__":
    create_shot(90, 100, "camera1", "back_plate.hdr")

