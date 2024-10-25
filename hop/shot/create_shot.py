from ..util.api_ping import get_collection
from ..util.import_hou import import_hou
from pymongo.collection import Collection

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


def create_shot(start_frame: int, end_frame: int):
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
        shot_number = update_shot_num(start_frame, end_frame, shots)
        shots.insert_one({
            "shot_number": shot_number,
            "start_frame": start_frame,
            "end_frame": end_frame,
        })
    else:
        pass


if __name__ == "__main__":
    create_shot(-20, -11)

