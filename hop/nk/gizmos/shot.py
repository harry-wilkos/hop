from pymongo.collection import ObjectId
import nuke
from hop.util import get_collection

global shots
shots = []


def recreate_shots():
    _shots = []
    for node in nuke.allNodes():
        if node.knob("HOP_Shot") and node["HOP_Shot"].value():
            _shots.append(node)
    global shots
    shots = _shots


def reload_shots(filename=None):
    for node in shots:
        id = node.knob("store_id").value()
        if id:
            collection = get_collection("shots", "active_shots")
            shot_data = collection.find_one({"_id": ObjectId(id)})
            start = node.knob("start").value()
            end = node.knob("end").value()
            print("working!")
            if shot_data and (
                start != shot_data["start_frame"] or end != shot_data["end_frame"]
            ):
                print("way")
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

    reload = nuke.PyScript_Knob("reload", "Reload")
    reload.setValue("shot.reload_shots()")
    node.addKnob(reload)

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
