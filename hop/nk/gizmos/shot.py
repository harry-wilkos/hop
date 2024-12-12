import nuke

def check_shot():
    print("working!")

def create_shot():
    node = nuke.createNode("Group")
    load  = nuke.PyCustom_Knob("todo", "To Do:", "ShotLoadUI() if 'ShotLoadUI' in globals() else type('Dummy', (), {'makeUI': classmethod(lambda self: None)})")
    node.addKnob(load)

    node.knob('updateUI')
    nuke.addUpdateUI(check_shot)
