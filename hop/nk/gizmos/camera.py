import nuke
import os


def find_shot(node):
    while node:
        parent = node.input(0)
        if parent and parent.knob("HOP") and parent.knob("HOP").value() == "shot":
            return parent
        else:
            node = parent


def reload(group=None):
    if group is None:
        group = nuke.thisNode()
    shot = find_shot(group)
    stored_cam = ""
    offset = 0
    if shot:
        stored_cam = str(store_id.value()).replace("\\", "/") if (store_id := shot.knob("cam")) else ""
        with shot.begin():
            offset = nuke.toNode("Read1").knob("offset").value()
    with group.begin():
        cam = nuke.toNode("Camera1")
        cam.knob("file").setValue(os.environ["HOP"].replace("\\", "/"))
        shift = nuke.toNode("TimeOffset1").knob("time_offset")
        shift.setValue(0)
        for knob in (
            "translate",
            "rotate",
            "scaling",
            "uniform_scale",
            "skew",
            "pivot_translate",
            "focal",
            "haperture",
            "vaperture",
            "near",
            "far",
            "win_translate",
            "win_scale",
            "focal_point",
            "fstop",
        ):
            knob_class = cam.knob(knob)
            knob_class.clearAnimated()
            knob_class.setValue(knob_class.defaultValue())
        if stored_cam:
            cam.knob("file").setValue(stored_cam)
            cam.knob("reload").execute()
            shift.setValue(offset)


def create_camera():
    group = nuke.createNode("Group")

    scale = nuke.Double_Knob("scale", "Scale")
    scale.setValue(0.01)
    group.addKnob(scale)

    group.setName("Shot Cam")
    reload_knob = nuke.PyScript_Knob(
        "reload",
        "Reload",
        "from hop.nk.gizmos.camera import reload as cam_reload; cam_reload(nuke.thisNode())",
    )
    group.addKnob(reload_knob)

    shot = group.input(0)
    stored_cam = (
        str(store_id.value()).replace("\\", "/")
        if (store_id := shot.knob("cam") if shot else False)
        else ""
    )

    shot_tag = nuke.String_Knob("HOP", None)
    shot_tag.setValue("camera")
    shot_tag.setVisible(False)
    group.addKnob(shot_tag)

    with group.begin():
        axis = nuke.createNode("Axis3")
        axis.knob("uniform_scale").setExpression("parent.scale")
        axis.hideControlPanel()

        cam = nuke.createNode("Camera3")
        cam.knob("frame_rate").setValue(int(os.environ["FPS"]))
        cam.knob("use_frame_rate").setValue(True)
        cam.knob("suppress_dialog").setValue(True)
        cam.knob("file").setValue(stored_cam)
        cam.knob("read_from_file").setValue(True)
        cam.setInput(0, axis)
        cam.hideControlPanel()

        offset = nuke.createNode("TimeOffset")
        offset.setInput(0, cam)
        offset.hideControlPanel()

        out = nuke.createNode("Output")
        out.setInput(0, offset)
        out.hideControlPanel()

        input = nuke.createNode("Input")
        input.hideControlPanel()
