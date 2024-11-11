from pymongo.collection import Collection

from ..util.api_ping import get_collection
from ..interfaces import ShotMerge

try:
    import hou
except ModuleNotFoundError:
    from ..util.import_hou import import_hou

    hou = import_hou()


def update_shot_num(start_frame: int, end_frame: int, shots: Collection) -> int:
    docs_ahead = shots.find({"start_frame": {"$gt": end_frame}}).sort("shot_number", 1)
    shot_number = None
    for count, ahead in enumerate(docs_ahead):
        ahead_sn = ahead["shot_number"]
        if count == 0:
            shot_number = ahead_sn
        shots.update_one({"_id": ahead["_id"]}, {"$set": {"shot_number": ahead_sn + 1}})
    if shot_number is None:
        doc_behind_cursor = (
            shots.find({"end_frame": {"$lt": start_frame}})
            .sort("shot_number", -1)
            .limit(1)
        )
        doc_behind = next(doc_behind_cursor, None)
        if doc_behind is not None:
            shot_number = doc_behind["shot_number"] + 1
        else:
            shot_number = 1
    return shot_number


def create_shot(start_frame: int, end_frame: int, cam: str = "", plate: str = ""):
    if start_frame >= end_frame:
        hou.ui.displayMessage(
            text="Invalid Frame Range",
            severity=hou.severityType.Error,
            title="Create Shot",
        )
        return None

    insert_shot = {
        "shot_number": None,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "plate": plate,
        "cam": cam,
        "lights": "",
        "assets": [],
    }

    shots = get_collection("hop", "shots")

    # Find intersections
    frame_range = range(start_frame, end_frame)
    intersections = []
    docs = []
    for doc in shots.find({}):
        doc_range = range(doc["start_frame"], doc["end_frame"])
        intersect = range(
            max(frame_range[0], doc_range[0]), min(frame_range[-1], doc_range[-1]) + 1
        )
        if len(intersect) != 0 or intersect.start == intersect.stop:
            intersections.append([intersect.start, intersect.stop])
            docs.append(doc)

    if len(intersections) == 0:
        shot_number = update_shot_num(start_frame, end_frame, shots)
        insert_shot["shot_number"] = shot_number
    else:
        keys = {"cam": [], "plate": [], "lights": [], "assets": []}
        compare_shots = []
        trim_shots = []
        for index, inter in enumerate(intersections):
            inter_start = inter[0]
            inter_end = inter[1]
            trim_doc = docs[index]
            trim = 0
            if (
                inter_start == start_frame
                and inter_end < end_frame
                and trim_doc["start_frame"] != start_frame
            ):
                trim = -1
                # clip beginning of frame range
            elif (
                inter_end == end_frame
                and inter_start > start_frame
                and trim_doc["end_frame"] != end_frame
            ):
                trim = 1
                # clip end of frame range
            elif (
                trim_doc["start_frame"] < start_frame
                and trim_doc["end_frame"] > end_frame
            ):
                print("shot is nested within existing shot")
            else:
                compare_shots.append(trim_doc["shot_number"])
                for key in keys:
                    trim_element = trim_doc[key]
                    if (type(trim_element) is list and len(trim_element) != 0) or (
                        type(trim_element) is str and trim_element != ""
                    ):
                        keys[key].append(trim_element)
                    else:
                        keys[key].append(None)

            if trim != 0:
                trim_shots.append({
                    "inter_start": inter_start,
                    "inter_end": inter_end,
                    "trim_doc": trim_doc,
                    "trim": trim,
                })
                compare_shots.append(trim_doc["shot_number"])

        if len(trim_shots) != 0:
            trim_shot_numbers = ", ".join(
                str(trim["trim_doc"]["shot_number"]) for trim in trim_shots
            )
            trim_shot_frames = ", ".join(
                f"{trim['inter_start']} - {trim['inter_end']}" for trim in trim_shots
            )
            confirm_trim = hou.ui.displayMessage(
                text=f"Change the frame range of the following shots: {trim_shot_numbers}?",
                buttons=["OK", "Cancel"],
                severity=hou.severityType.Warning,
                default_choice=1,
                close_choice=1,
                title="Trime Shot",
                help=(
                    f"The entered frame range overlaps with existing shots frames: {trim_shot_frames}"
                ),
                details=(
                    "Either cancel and change the frame ranges to avoid intersecting "
                    "with existing shots, or continue and the mentioned shots will be trimmed."
                ),
            )
            if confirm_trim == 0:
                for trim in trim_shots:
                    if trim["trim"] == 1:
                        shots.update_one(
                            {"_id": trim["trim_doc"]["_id"]},
                            {
                                "$set": {
                                    "start_frame": trim["inter_end"] + 1,
                                }
                            },
                        )
                    else:
                        shots.update_one(
                            {"_id": trim["trim_doc"]["_id"]},
                            {
                                "$set": {
                                    "end_frame": trim["inter_start"] - 1,
                                }
                            },
                        )

            else:
                return None

        # Merge Shots
        if any(keys[key] for key in keys):
            del_keys = []
            for key, items in keys.items():
                input_value = insert_shot[key]
                if (isinstance(input_value, list) and not input_value) or (
                    isinstance(input_value, str) and input_value == ""
                ):
                    if not items:
                        del_keys.append(key)
                    else:
                        keys[key].insert(0, None)
                else:
                    keys[key].insert(0, insert_shot[key])
            compare_shots.insert(0, "New Shot")
            for key in del_keys:
                del keys[key]

            merge_results = ShotMerge(keys, compare_shots)
            print(merge_results)
            

if __name__ == "__main__":
    create_shot(1, 100, "camera1", "back_plate.hdr")
