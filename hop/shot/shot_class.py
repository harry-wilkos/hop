import os
from shutil import rmtree
from typing import Callable

from pymongo.collection import Collection, ObjectId

from hop.util.api_helpers import get_collection
from hop.util.helpers import copy_file, move_folder
from hop.util.hou_helpers import error_dialog, expand_path
from hop.shot.camera import update_camera
from hop.shot.frame_range import update_frame_range, update_shot_num
from hop.shot.plate import generate_back_plate, update_plate
from hop.util import MultiProcess

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
            continue

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
        def perform_step(step_function: Callable, progress_title: str, *args, **kwargs):
            nonlocal status
            nonlocal shot_dir
            if status:
                try:
                    with hou.InterruptableOperation(
                        progress_title, open_interrupt_dialog=False
                    ) as progress:
                        if "progress" in step_function.__code__.co_varnames:
                            status = step_function(progress, *args, **kwargs)
                        else:
                            status = step_function(*args, **kwargs)
                        progress.updateProgress(1.0)
                except hou.OperationInterrupted:
                    status = False
                if status:
                    overall_progress.updateLongProgress(1 / 4)
                else:
                    if self.shot_data:
                        if shot_dir:
                            rmtree(shot_dir)
                    error_dialog("Publish Shot", "Error Publishing Shot")

        if self.shot_data is None:
            return self.shot_data

        status = True

        try:
            with hou.InterruptableOperation(
                "Publishing Shot",
                "Publishing Shot",
                open_interrupt_dialog=True,
            ) as overall_progress:
                shot_dir = os.makedirs(
                    os.path.join(
                        os.environ["HOP"],
                        "shots",
                        "active_shots",
                        str(self.shot_data["_id"]),
                    ),
                    exist_ok=True,
                )

                if self.rip_files:
                    perform_step(
                        lambda: MultiProcess(copy_file, self.rip_files)
                        .execute()
                        .retrieve(),
                        "Copying Files",
                    )

                if self.shot_data["plate"] and self.new_plate:
                    perform_step(generate_back_plate, "Generating Back Plate", self)
                    self.new_plate = False

                if self.delete_shots:
                    perform_step(
                        shot_delete,
                        "Deleting Shots",
                        self.delete_shots,
                        self.collection,
                    )

                perform_step(update_shot_num, "Updating Shot Numbers", self)

                self.collection.insert_one(self.shot_data)

            hou.ui.displayMessage(
                f"Shot published as shot {self.shot_data['shot_number']}!"
            )

        except hou.OperationInterrupted:
            pass

        return self.shot_data
