import nuke

global shots
shots = []


def recreate_shots():
    _shots = []
    for node in nuke.allNodes():
        if node.knob("HOP_Shot") and node["HOP_Shot"].value():
            _shots.append(node)
    global shots
    shots = _shots


def reload_shots():
    for node in shots:
        node["loadUI"].getObject()
    pass


def create_shot():
    node = nuke.createNode("Group")

    load = nuke.PyCustom_Knob(
        "loadUI",
        "Load UI",
        "ShotLoadUI(nuke.thisNode()) if 'ShotLoadUI' in globals() else type('Dummy', (), {'makeUI': classmethod(lambda self: None)})",
    )
    node.addKnob(load)

    shot_tag = nuke.Boolean_Knob("HOP_Shot", None)
    shot_tag.setValue(True)
    shot_tag.setVisible(False)
    node.addKnob(shot_tag)

    store_shot_id = nuke.String_Knob("store_id", None)
    node.addKnob(store_shot_id)

    store_plate_path = nuke.File_Knob("plate_path", None)
    node.addKnob(store_plate_path)

    store_start_frame = nuke.Int_Knob("start_frame", None)
    store_end_frame = nuke.Int_Knob("end_frame", None)
    node.addKnob(store_start_frame)
    node.addKnob(store_end_frame)

    node.begin()
    read = nuke.createNode("Read")
    read.hideControlPanel()
    read["file"].setValue("[value [topnode parent].plate_path]")

    out = nuke.createNode("Output")
    out.hideControlPanel()
    out.setInput(0, read)
    node.end()

    shots.append(node)
