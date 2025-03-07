import nuke


def create_render():
    node = nuke.createNode("Group")
    node.setName("Shot_Render")
    load = nuke.PyCustom_Knob(
        "loadUI",
        "Load Render",
        "RenderLoadUI(nuke.thisNode()) if 'RenderLoadUI' in globals() else type('Dummy', (), {'makeUI': classmethod(lambda self: None)})",
    )
    node.addKnob(load)

    holdout = nuke.Int_Knob("holdout", None)
    holdout.setVisible(False)
    node.addKnob(holdout)

    version = nuke.Int_Knob("version", None)
    version.setVisible(False)
    node.addKnob(version)

    shot_tag = nuke.String_Knob("HOP", None)
    shot_tag.setValue("render")
    shot_tag.setVisible(False)
    node.addKnob(shot_tag)

    with node.begin():
        input = nuke.createNode("Input")
        input.hideControlPanel()

        read = nuke.createNode("Read")
        read.hideControlPanel()

        read.knob("raw").setValue(True)
        read.knob("first").setValue(int(nuke.Root().knob("first_frame").value()))
        read.knob("last").setValue(int(nuke.Root().knob("last_frame").value()))
        read.knob("on_error").setValue("checkerboard")

        deep = nuke.createNode("DeepRead")
        deep.knob("file").setValue(".exr")
        deep.hideControlPanel()
        deep.knob("first").setValue(int(nuke.Root().knob("first_frame").value()))
        deep.knob("last").setValue(int(nuke.Root().knob("last_frame").value()))
        deep.knob("on_error").setValue("checkerboard")


        out = nuke.createNode("Output")
        out.hideControlPanel()
