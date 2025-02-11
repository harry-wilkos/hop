from hop.nk.interfaces.load_render_ui import RenderLoadUI
import nuke
from hop.nk.gizmos.shot import reload as shot_reload
from hop.nk.gizmos.camera import reload as cam_reload
from hop.util import get_collection, custom_dialogue
from pymongo.collection import ObjectId


def find_shot(node):
    while node:
        parent = node.input(0)
        if parent and parent.knob("HOP") and parent.knob("HOP").value() == "shot":
            return parent
        else:
            node = parent


def reload(filename=None):
    hop_nodes = []
    render_dicts = []
    update_renders = None
    for node in nuke.allNodes():
        if knob := node.knob("HOP"):
            value = knob.value()
            if knob.value() == "shot":
                hop_nodes.insert(0, node)
                continue
            hop_nodes.append(node)
            if value == "render":
                if (shot := find_shot(node)) and (id := shot.knob("store_id").value()):
                    shot_dict = get_collection("shots", "active_shots").find_one({
                        "_id": ObjectId(id)
                    })

                    if (
                        shot_dict
                        and (len(shot_dict["render_versions"]))
                        > node.knob("version").value()
                    ):
                        render_dicts.append(shot_dict)
                        if update_renders is None:
                            update_renders = bool(
                                custom_dialogue(
                                    "Shot Renders",
                                    "A newer render version is available. Update to latest?",
                                    ["No", "Yes"],
                                    1,
                                )
                            )
    for node in hop_nodes:
        value = node.knob("HOP").value()
        node.hideControlPanel()
        if value == "shot":
            shot_reload(node)
        elif value == "render":
            node.removeKnob(node.knob("loadUI"))
            if update_renders:
                versions = render_dicts[0]["render_versions"]
                holdout = node.knob("holdout")
                if (new_holdout := len(versions[-1]) - 1) >= node.knob(
                    "holdout"
                ).value():
                    holdout.setValue(new_holdout)
                else:
                    holdout.setValue(0)
                node.knob("version").setValue(len(versions))
                render_dicts.pop(0)

            load = nuke.PyCustom_Knob(
                "loadUI",
                "Load Render",
                "RenderLoadUI(nuke.thisNode()) if 'RenderLoadUI' in globals() else type('Dummy', (), {'makeUI': classmethod(lambda self: None)})",
            )
            node.addKnob(load)
            RenderLoadUI(node)

        elif value == "camera":
            cam_reload(node)
        node.setSelected(True)
    print("reloaded")
    return filename
