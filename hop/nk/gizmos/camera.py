import nuke
import os


def reload():
    group = nuke.thisNode()
    with group.begin():
        cam = nuke.toNode("Camera1")
        file = cam.knob("file")
        file.setValue("")
        file.setValue("[value input.cam]")


def create_camera():
    group = nuke.createNode("Group")
    group.setName("Shot Cam")
    reload = nuke.PyScript_Knob(
        "reload", "Reload", "from hop.nk.gizmos.camera import reload; reload()"
    )
    group.knob("label").setValue("[value input.label]")
    group.addKnob(reload)
    with group.begin():
        cam = nuke.createNode("Camera3")
        cam.knob("read_from_file").setValue(True)
        cam.knob("frame_rate").setValue(int(os.environ["FPS"]))
        cam.knob("use_frame_rate").setValue(True)
        cam.knob("suppress_dialog").setValue(True)
        cam.knob("file").setValue("[value input.cam]")
        cam.knob("file_link").setValue("[value input.cam]")
        cam.knob("read_from_file_link").setValue(True)
        cam.hideControlPanel()

        out = nuke.createNode("Output")
        out.setInput(0, cam)
        out.hideControlPanel()

        input = nuke.createNode("Input")
        input.hideControlPanel()
