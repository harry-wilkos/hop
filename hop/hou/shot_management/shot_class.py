import os
from sys import exit
from shutil import rmtree
from typing import Callable

from pymongo.collection import Collection, ObjectId

from hop.hou.shot_management.camera import update_camera
from hop.hou.shot_management.frame_range import update_frame_range, update_shot_num
from hop.hou.shot_management.plate import (
    generate_back_plate,
    update_plate,
    update_st_map,
    update_padding,
)
from hop.hou.util.helpers import expand_path
from hop.util import MultiProcess, copy_file, get_collection, move_folder, post
from hop.hou.util import error_dialog

try:
    import hou
except ModuleNotFoundError:
    from hop.hou.util import import_hou

    hou = import_hou()


def shot_delete(
    shot_ids: ObjectId | list, shots_collection: Collection, retire: bool = True
) -> bool:
    if type(shot_ids) is not list:
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
            paths_to_move = expand_path(existing_shot_path)
            if paths_to_move is not None:
                move_folder(paths_to_move, ["shots", "retired_shots"])
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

        if retire:
            for key, value in shot_data.items():
                if type(value) is str:
                    shot_data[key] = value.replace("active_shots", "retired_shots")
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
    class Update:
        def __init__(self, shot: "Shot") -> None:
            self.shot = shot

        def frame_range(self, start_frame: int, end_frame: int):
            if self.shot.shot_data is None or not update_frame_range(
                self.shot,
                start_frame,
                end_frame,
            ):
                self.shot.shot_data = None
            return self.shot

        def camera(self, cam: str):
            if cam == "":
                pass
            elif self.shot.shot_data is None or not update_camera(self.shot, cam):
                self.shot.shot_data = None
            return self.shot

        def plate(self, plate: str):
            if plate == "":
                pass
            elif self.shot.shot_data is None or not update_plate(self.shot, plate):
                self.shot.shot_data = None
            return self.shot

        def st_map(self, map: str):
            if map == "":
                pass
            elif self.shot.shot_data is None or not update_st_map(self.shot, map):
                self.shot.shot_data = None
            return self.shot

        def padding(self, padding: int):
            if self.shot.shot_data is None or not update_padding(self.shot, padding):
                self.shot.shot_data = None
            return self.shot

        def description(self, description: str):
            if self.shot.shot_data:
                self.shot.shot_data["description"] = description
            return self.shot

    def __init__(
        self,
        start_frame: int | None = None,
        end_frame: int | None = None,
        padding: int = 0,
        cam: str = "",
        plate: str = "",
        st_map: str = "",
        description: str = "",
        shot_number: int | None = None,
    ):
        self.collection = get_collection("shots", "active_shots")
        self.delete_shots, self.rip_files = [], []
        self.new_plate, self.cam_checked = False, False
        self.update = self.Update(self)

        if shot_number is not None:
            retrieve_shot = self.collection.find_one({"shot_number": shot_number})
            if retrieve_shot is not None:
                self.shot_data = retrieve_shot
            else:
                raise LookupError("Cannot find shot")
        else:
            id = ObjectId()
            self.shot_data = {
                "_id": id,
                "shot_number": None,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "padding": padding,
                "plate": plate,
                "back_plate": "",
                "st_map": st_map,
                "cam": cam,
                "cam_path": "",
                "geo_paths": "",
                "description": description.capitalize(),
                "usd_output": os.path.join(
                    "$HOP", "shots", "active_shots", str(id), "usd"
                ),
                "render_base": os.path.join(
                    "$HOP", "shots", "active_shots", str(id), "renders"
                ),
                "render_versions": [],
                "assets": [],
            }

            self.update.frame_range(
                self.shot_data["start_frame"],
                self.shot_data["end_frame"],
            )
            if self.shot_data is not None:
                self.update.camera(self.shot_data["cam"])
            if self.shot_data is not None:
                self.update.plate(self.shot_data["plate"])

    def delete(self):
        if self.shot_data is not None:
            shot_status = shot_delete(self.shot_data["_id"], self.collection)
            if shot_status:
                self.shot_data = None
            return shot_status
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
                    overall_progress.updateLongProgress(1 / 2)
                else:
                    if self.shot_data:
                        if not shot_dir:
                            rmtree(shot_path)
                    error_dialog("Publish Shot", "Error Publishing Shot")
                    exit(1)

        if self.shot_data is None:
            return self.shot_data

        status = True

        try:
            with hou.InterruptableOperation(
                "Publishing Shot",
                "Publishing Shot",
                open_interrupt_dialog=True,
            ) as overall_progress:
                shot_path = os.path.join(
                    os.environ["HOP"],
                    "shots",
                    "active_shots",
                    str(self.shot_data["_id"]),
                )
                shot_dir = True
                if not os.path.exists(shot_path):
                    os.makedirs(
                        shot_path,
                        exist_ok=True,
                    )
                    os.makedirs(os.path.join(shot_path, "usd"))
                    os.makedirs(os.path.join(shot_path, "renders"))
                    shot_dir = False

                if self.rip_files:
                    perform_step(
                        lambda: MultiProcess(
                            copy_file, self.rip_files, interpreter=os.environ["PYTHON"]
                        )
                        .execute()
                        .retrieve(),
                        "Copying Files",
                    )
                if self.shot_data["plate"] and self.new_plate:
                    perform_step(generate_back_plate, "Generating Back Plate", self)

                if self.delete_shots:
                    perform_step(
                        shot_delete,
                        "Deleting Shots",
                        self.delete_shots,
                        self.collection,
                    )
                description = self.shot_data["description"]
                description = f": {description}" if description else ""
                if self.shot_data["shot_number"] is None:
                    perform_step(update_shot_num, "Updating Shot Numbers", self)
                    self.collection.insert_one(self.shot_data)
                    post(
                        "discord",
                        {
                            "message": f":camera_with_flash: A new **Shot {self.shot_data['shot_number']}** was published at **{self.shot_data['start_frame']} - {self.shot_data['end_frame']}{description}** :camera_with_flash:"
                        },
                    )
                else:
                    self.collection.update_one(
                        {"_id": self.shot_data["_id"]}, {"$set": self.shot_data}
                    )
                    post(
                        "discord",
                        {
                            "message": f":camera: **Shot {self.shot_data['shot_number']}** was updated at *{self.shot_data['start_frame']} - {self.shot_data['end_frame']}{description}** :camera:"
                        },
                    )

                hou.ui.displayMessage(
                    f"Shot published as shot {self.shot_data['shot_number']}!"
                )

        except hou.OperationInterrupted:
            pass

        return self.shot_data
