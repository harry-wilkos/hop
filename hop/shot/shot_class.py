from pymongo.collection import ObjectId, Collection
from ..util.api_helpers import get_collection
from ..util.helpers import copy_file, move_folder
from .frame_range import update_frame_range, update_shot_num
from .camera import update_camera
from .plate import update_plate, generate_back_plate
from ..util.hou_helpers import error_dialog, expand_path
import os

try:
    import hou
except ModuleNotFoundError:
    from ..util.hou_helpers import import_hou

    hou = import_hou()


def shot_delete(shot_ids: ObjectId | list, shots_collection: Collection) -> bool:
    if isinstance(shot_ids, ObjectId):
        shot_ids = [shot_ids]

    if not shot_ids:
        return True

    retired_shots_collection = get_collection("shots", "retired_shots")
    shot_number_min = None

    for shot_id in shot_ids:
        existing_shot_path = os.path.join(
            os.environ["HOP"], "shots", "active_shots", str(shot_id)
        )
        try:
            move_folder(existing_shot_path, ["shots", "retired_shots"])
        except Exception:
            return False

        shot_data = shots_collection.find_one({"_id": shot_id})
        if not shot_data:
            print(f"Shot ID {shot_id} not found in active shots collection.")
            continue  # Skip this shot since we can't find it

        if shot_number_min is None or (
            shot_data.get("shot_number") is not None
            and shot_data["shot_number"] < shot_number_min
        ):
            shot_number_min = shot_data["shot_number"]

        retired_shots_collection.insert_one(shot_data)

        shots_collection.delete_one({"_id": shot_id})

    if shot_number_min is not None:
        shots_ahead = shots_collection.find({
            "shot_number": {"$gt": shot_number_min}
        }).sort("shot_number", 1)

        for count, ahead_shot in enumerate(shots_ahead):
            new_shot_number = shot_number_min + count
            shots_collection.update_one(
                {"_id": ahead_shot["_id"]},
                {"$set": {"shot_number": new_shot_number}},
            )
    return True


class Shot:
    def __init__(
        self,
        start_frame: int,
        end_frame: int,
        cam: str = "",
        plate: str = "",
        shot_number: int | None = None,
    ):
        self.collection = get_collection("shots", "active_shots")
        self.delete_shots, self.rip_files = [], []
        self.new_plate = False
        if shot_number is not None:
            retrieve_shot = self.collection.find_one({"shot_number": shot_number})
            if retrieve_shot is not None:
                self.shot_data = retrieve_shot
            else:
                raise LookupError("Cannot find shot")
        else:
            self.shot_data = {
                "_id": ObjectId(),
                "shot_number": None,
                "start_frame": None,
                "end_frame": None,
                "plate": plate,
                "back_plate": "",
                "cam": cam,
                "cam_path": "",
                "lights": "",
                "assets": [],
            }
            if not update_frame_range(self, start_frame, end_frame):
                self.shot_data = None
            if self.shot_data is not None and self.shot_data["cam"] != "":
                if not update_camera(self, self.shot_data["cam"]):
                    self.shot_data = None
            if self.shot_data is not None and self.shot_data["plate"] != "":
                if not update_plate(self, self.shot_data["plate"]):
                    self.shot_data = None

    def delete(self):
        if self.shot_data is not None:
            if shot_delete(self.shot_data["_id"], self.collection):
                self.shot_data = None
        return self.shot_data

    def publish(self):
        def perform_step(step_function, *args, **kwargs):
            nonlocal status
            if status:
                status = step_function(*args, **kwargs)
            if not status:
                error_dialog("Publish Shot", "Error Publishing Shot")
                if self.shot_data:
                    shot_dir = expand_path(
                        os.path.join("$HOP", "shots", str(self.shot_data["_id"]))
                    )
                    if shot_dir:
                        os.remove(shot_dir)

        if self.shot_data is None:
            return self.shot_data
        status = True

        perform_step(
            lambda: all(copy_file(*file) is not None for file in self.rip_files)
        )

        if self.shot_data["plate"] and self.new_plate:
            perform_step(generate_back_plate, self)
            self.new_plate = False

        if self.delete_shots:
            perform_step(shot_delete, self.delete_shots, self.collection)

        perform_step(update_shot_num, self)
        self.collection.insert_one(self.shot_data)

        hou.ui.displayMessage(
            f"Shot published as shot {self.shot_data['shot_number']}!"
        )
        return self.shot_data
