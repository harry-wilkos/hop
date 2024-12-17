from pymongo.collection import ObjectId
import nuke
import nuke.rotopaint as rp
import _curvelib
import re
from hop.util import get_collection, custom_dialogue

global shots
shots = []
collection = get_collection("shots", "active_shots")


# Adapted from https://www.andreageremia.it/tutorial_timeoffset.html
def offset_frames_in_curve(curve_str, offset):
    def offset_replace(m):
        if "." in m.group(1):  # Float preservation
            return "x%0.3f" % (float(m.group(1)) + offset)
        else:  # Integer preservation
            return "x%d" % (int(m.group(1)) + offset)

    return re.sub(r"x([-+]?\d*\.\d+|\d+)", offset_replace, curve_str)


def shift_keyframes(offset):
    for node in nuke.allNodes():
        for knob_name in node.knobs():
            knob = node[knob_name]
            if knob.isAnimated():
                knob.fromScript(offset_frames_in_curve(knob.toScript(), offset))

        # Offset lifetime knobs if present
        if node.knob("useLifetime") and node["useLifetime"].getValue() == 1:
            node["lifetimeStart"].setValue(node["lifetimeStart"].getValue() + offset)
            node["lifetimeEnd"].setValue(node["lifetimeEnd"].getValue() + offset)

        # Offset lifetime for shapes and strokes in Roto or RotoPaint nodes
        if node.Class() in ["Roto", "RotoPaint"]:
            cKnob = node["curves"]
            rootLayer = cKnob.rootLayer

            for shape in rootLayer:
                if isinstance(shape, rp.Shape) or isinstance(shape, rp.Stroke):
                    attribs = shape.getAttributes()
                    start = int(
                        attribs.getValue(
                            0, _curvelib.AnimAttributes.kLifeTimeNAttribute
                        )
                    )
                    end = int(
                        attribs.getValue(
                            0, _curvelib.AnimAttributes.kLifeTimeMAttribute
                        )
                    )

                    attribs.set(
                        0, _curvelib.AnimAttributes.kLifeTimeNAttribute, start + offset
                    )
                    attribs.set(
                        0, _curvelib.AnimAttributes.kLifeTimeMAttribute, end + offset
                    )


def recreate_shots():
    _shots = []
    for node in nuke.allNodes():
        if node.knob("HOP_Shot") and node["HOP_Shot"].value():
            _shots.append(node)
    global shots
    shots = _shots


def handle_change(node):
    id = node.knob("store_id").value()
    off_pipe = node.knob("off_pipe").value()
    if id and not off_pipe:
        shot_data = collection.find_one({"_id": ObjectId(id)})
        start = node.knob("start").value()
        end = node.knob("end").value()
        shot_number = node.knob("label").value()

        if not shot_data:
            with node.begin():
                file = nuke.toNode("Read1").knob("file")
                value = file.value()
                file.setValue(value.replace("active_shots", "retired_shots"))

            node.knob("off_pipe").setValue(True)
            nuke.message(f"Shot {shot_number} has been deleted, you are now off pipe")

        elif end <= shot_data["start_frame"] or start >= shot_data["end_frame"]:
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
            if result == 0:
                shift_keyframes(shot_data["start_frame"] - start)
                node.knob("start").setValue(shot_data["start_frame"])
                node.knob("end").setValue(shot_data["end_frame"])

            elif result == 1:
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

            elif result == 2:
                node.knob("off_pipe").setValue(True)

        elif start != shot_data["start_frame"]:
            shift_keyframes(shot_data["start_frame"] - start)
            node.knob("start").setValue(shot_data["start_frame"])
            node.knob("end").setValue(shot_data["end_frame"])


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

    off_pipe = nuke.Boolean_Knob("off_pipe", None)
    shot_tag.setValue(False)
    off_pipe.setVisible(False)
    node.addKnob(off_pipe)

    start = nuke.Int_Knob("start", None)
    end = nuke.Int_Knob("end", None)
    start.setVisible(False)
    end.setVisible(False)
    node.addKnob(start)
    node.addKnob(end)

    auto_alpha = nuke.Boolean_Knob("auto_alpha", None)
    auto_alpha.setValue(True)
    auto_alpha.setVisible(False)
    node.addKnob(auto_alpha)

    with node.begin():
        read = nuke.createNode("Read")
        read.hideControlPanel()

        read.knob("auto_alpha").setExpression("parent.auto_alpha")
        read.knob("raw").setValue(True)

        offset = nuke.Int_Knob("offset", None)
        read.addKnob(offset)

        out = nuke.createNode("Output")
        out.hideControlPanel()

        out.setInput(0, read)

    shots.append(node)
