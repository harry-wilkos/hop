from pymongo.collection import Collection

from ..util.api_ping import get_collection


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
    insert_shot = {
        "shot_number": None,
        "start_frame": start_frame,
        "end_frame": end_frame,
        "plate": plate,
        "cam": cam,
        "lights": "",
        "assets": [],
    }

    if start_frame > end_frame:
        return None
    shots = get_collection("hop", "shots")
    frame_range = range(start_frame, end_frame)
    intersections = []
    docs = []
    for doc in shots.find({}):
        doc_range = range(doc["start_frame"], doc["end_frame"])
        intersect = range(
            max(frame_range[0], doc_range[0]), min(frame_range[-1], doc_range[-1]) + 1
        )
        if len(intersect) != 0:
            intersections.append([intersect.start, intersect.stop])
            docs.append(doc)
    if len(intersections) == 0:
        # Move to end of shot creation 
        shot_number = update_shot_num(start_frame, end_frame, shots)
        insert_shot["shot_number"] = shot_number
    else:
        keys = {"cam": [], "plate": [], "lights": [], "assets": []}
        compare_shots = []
        for index, inter in enumerate(intersections):
            print(inter)
            inter_start = inter[0]
            inter_end = inter[1]
            trim_doc = docs[index]
            trim = True
            if (
                inter_start == start_frame
                and inter_end < end_frame
                and trim_doc["start_frame"] != start_frame
            ):
                inter_start += -1
                inter_end = trim_doc["start_frame"]
                print("clipping_front")
            elif (
                inter_end == end_frame
                and inter_start > start_frame
                and trim_doc["end_frame"] != end_frame
            ):
                print("clipping_back")
                inter_end += 1
                inter_start = trim_doc["end_frame"]
            elif (
                trim_doc["start_frame"] < start_frame
                and trim_doc["end_frame"] > end_frame
            ):
                print("shot is nested within existing shot")
            else:
                trim = False
                compare_shots.append(trim_doc["shot_number"])
                for key in keys:
                    trim_element = trim_doc[key]
                    if (type(trim_element) is list and len(trim_element) != 0) or (
                        type(trim_element) is str and trim_element != ""
                    ):
                        keys[key].append(trim_element)
                    else:
                        keys[key].append(None)

            if trim:
                # Add confirmation check
                shots.update_one(
                    {"_id": trim_doc["_id"]},
                    {"$set": {"end_frame": inter_start, "start_frame": inter_end}},
                )
        del_keys = []
        new_shot_added = False

        for key in keys:
            input_value = insert_shot[key]
            if (isinstance(input_value, list) and len(input_value) == 0) or (
                isinstance(input_value, str) and input_value == ""
            ):
                if len(keys[key]) == 0:
                    del_keys.append(key)
                else:
                    keys[key].insert(0, None)
            else:
                keys[key].insert(0, insert_shot[key])
                if not new_shot_added and any(
                    shot != "New Shot" for shot in compare_shots
                ):
                    compare_shots.insert(0, "New Shot")
                    new_shot_added = True
        for key in del_keys:
            del keys[key]

        print(keys)
        print(compare_shots)


if __name__ == "__main__":
    create_shot(30, 60, "camera1", "back_plate.hdr")
