from pymongo.collection import ObjectId
import nuke
from hop.util import get_collection, custom_dialogue

global shots
shots = []
collection = get_collection("shots", "active_shots")


def recreate_shots():
    _shots = []
    for node in nuke.allNodes():
        if node.knob("HOP_Shot") and node["HOP_Shot"].value():
            _shots.append(node)
    global shots
    shots = _shots


def handle_change(node):
    id = node.knob("store_id").value()
    if id:
        shot_data = collection.find_one({"_id": ObjectId(id)})
        start = node.knob("start").value()
        end = node.knob("end").value()

        if not shot_data:
            print("fix it")

        elif end <= shot_data["start_frame"] or start >= shot_data["end_frame"]:
            shot_number = node.knob("label").value()
            result = custom_dialogue(
                f"Reload Shot {shot_number}",
                f"Shot {shot_number} has moved",
                [
                    "Adopt new range",
                    "Adopt new shot",
                    "Work off pipe",
                ],
                0,
                [
                    "Keep working on this shot but use the new frame range",
                    "Work on the new shot that (mostly) occupies this frame range",
                    "Keep working as is (not reccomended)",
                ],
            )

            if result == 1:
                new_data = list(
                    collection.aggregate([
                        {
                            "$addFields": {
                                "start_diff": {
                                    "$abs": {"$subtract": ["$start_frame", start]}
                                },
                                "end_diff": {
                                    "$abs": {"$subtract": ["$end_frame", end]}
                                },
                                "range_diff": {
                                    "$abs": {
                                        "$subtract": [
                                            {
                                                "$subtract": [
                                                    "$end_frame",
                                                    "$start_frame",
                                                ]
                                            },
                                            {"$subtract": [end, start]},
                                        ]
                                    }
                                },
                                "proximity_score": {
                                    "$add": [
                                        {
                                            "$abs": {
                                                "$subtract": ["$start_frame", start]
                                            }
                                        },
                                        {"$abs": {"$subtract": ["$end_frame", end]}},
                                    ]
                                },
                            }
                        },
                        {"$sort": {"proximity_score": 1, "range_diff": 1}},
                        {"$limit": 1},
                        {
                            "$project": {
                                "_id": 1,
                                "start_frame": 1,
                                "end_frame": 1,
                                "start_diff": 1,
                                "end_diff": 1,
                                "range_diff": 1,
                            }
                        },
                    ])
                )[0]
                node.knob("store_id").setValue(str(new_data["_id"]))

            if result == 2:
                pass


def reload_shots(filename=None):
    for node in shots:
        handle_change(node)
    return filename


def create_shot():
    node = nuke.createNode("Group")
    node.setName("Shot")

    load = nuke.PyCustom_Knob(
        "loadUI",
        "Load Shot",
        "ShotLoadUI(nuke.thisNode()) if 'ShotLoadUI' in globals() else type('Dummy', (), {'makeUI': classmethod(lambda self: None)})",
    )
    node.addKnob(load)

    shot_tag = nuke.Boolean_Knob("HOP_Shot", None)
    shot_tag.setValue(True)
    shot_tag.setVisible(False)
    node.addKnob(shot_tag)

    store_shot_id = nuke.String_Knob("store_id", None)
    store_shot_id.setVisible(False)
    node.addKnob(store_shot_id)

    start = nuke.Int_Knob("start", None)
    end = nuke.Int_Knob("end", None)
    start.setVisible(False)
    end.setVisible(False)
    node.addKnob(start)
    node.addKnob(end)

    with node.begin():
        read = nuke.createNode("Read")
        read.hideControlPanel()

        offset = nuke.Int_Knob("offset", None)
        read.addKnob(offset)

        out = nuke.createNode("Output")
        out.hideControlPanel()

        out.setInput(0, read)

    shots.append(node)
