from pymongo.collection import ObjectId
import maya.cmds as cmds
from hop.my.interfaces import load_shot
from hop.my.util import set_fps, undo_chunk, get_children
from hop.util import get_collection, custom_dialogue, find_shot
import os


def shift_keyframes(offset):
    anim_objects = cmds.ls(type="animCurve")
    unique_objects = set(anim_objects)
    for anim_curve in unique_objects:
        keyframes = cmds.keyframe(anim_curve, query=True, timeChange=True)
        if keyframes:
            cmds.keyframe(anim_curve, edit=True, relative=True, timeChange=offset)


def handle_change():
    with undo_chunk():
        collection = get_collection("shots", "active_shots")
        if cmds.attributeQuery("loadedShot", node="defaultRenderGlobals", exists=True):
            id = cmds.getAttr("defaultRenderGlobals.loadedShot")
            if id and not cmds.getAttr("defaultRenderGlobals.offPipe"):
                shot = collection.find_one({"_id": ObjectId(id)})
                start_frame, end_frame = cmds.getAttr("defaultRenderGlobals.frame")[0]
                if not shot:
                    shot_number = int(cmds.getAttr("defaultRenderGlobals.shotNumber"))
                    result = custom_dialogue(
                        f"Reload Shot {shot_number}",
                        f"Shot {shot_number} has been deleted",
                        ["Adopt new shot", "Work off pipe"],
                        0,
                        [
                            "Work on the new shot that (mostly) occupies this frame range",
                            "Keep working as is (not reccomended)",
                        ],
                    )

                    if result == 0:
                        create_shot(find_shot(collection, start_frame, end_frame))
                    if result == 1:
                        collection = get_collection("shots", "retired_shots")
                        old_shot = collection.find_one({"_id": ObjectId(id)})
                        create_shot(old_shot)
                        cmds.setAttr(
                            "defaultRenderGlobals.offPipe",
                            1,
                        )
                        cmds.setAttr(
                            "defaultRenderGlobals.loadedShot",
                            "",
                            type="string",
                        )

                elif (
                    end_frame <= shot["start_frame"] or start_frame >= shot["end_frame"]
                ):
                    result = custom_dialogue(
                        f"Reload Shot {shot['shot_number']}",
                        f"Shot {shot['shot_number']} has moved",
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
                        create_shot(shot)
                        shift_keyframes(shot["start_frame"] - start_frame)

                    elif result == 1:
                        create_shot(find_shot(collection, start_frame, end_frame))

                    elif result == 2:
                        cmds.setAttr(
                            "defaultRenderGlobals.offPipe",
                            1,
                        )
                        cmds.setAttr(
                            "defaultRenderGlobals.loadedShot",
                            "",
                            type="string",
                        )
                        children = get_children(
                            cmds.getAttr("defaultRenderGlobals.shotPath")
                        )
                        cmds.setAttr(
                            f"{children[-1]}.frameOffset",
                            shot["start_frame"] - start_frame,
                        )

                        for connection in cmds.listConnections(children[1]) or []:
                            if "AlembicNode" in connection:
                                cmds.setAttr(
                                    f"{connection}.offset",
                                    shot["start_frame"] - start_frame,
                                )
                                break

                        cmds.setAttr("defaultRenderGlobals.offPipe", 1)

                elif start_frame != shot["start_frame"]:
                    create_shot(shot)
                    shift_keyframes(shot["start_frame"] - start_frame)


def create_shot(shot: dict | None = None):
    with undo_chunk():
        set_fps()
        if not shot:
            shot = load_shot()
            if cmds.attributeQuery(
                "scriptJob", node="defaultRenderGlobals", exists=True
            ):
                script_job = cmds.getAttr("defaultRenderGlobals.scriptJob")
                if script_job != 0:
                    cmds.scriptJob(kill=script_job)
                    cmds.setAttr("defaultRenderGlobals.scriptJob", 0)

        if cmds.attributeQuery("shotPath", node="defaultRenderGlobals", exists=True):
            cam = cmds.getAttr("defaultRenderGlobals.shotPath")
            pipe = cmds.getAttr("defaultRenderGlobals.offPipe")
            if cam != "" and not pipe:
                try:
                    cmds.delete(cam)
                except ValueError:
                    pass
                cmds.setAttr(
                    "defaultRenderGlobals.shotPath",
                    "",
                    type="string",
                )
                cmds.setAttr("defaultRenderGlobals.loadedShot", "", type="string")

        if shot and shot["cam"] and shot["cam_path"]:
            cam_file_path = os.path.expandvars(shot["cam"])
            if not cmds.pluginInfo("AbcImport", query=True, loaded=True):
                cmds.loadPlugin("AbcImport")
            store_a_cam = cmds.AbcImport(cam_file_path, mode="import", filterObjects=shot["cam_path"])
            [
                cmds.AbcImport(cam_file_path, mode="import", filterObjects=geo)
                for geo in shot["geo_paths"]
            ]
            start = shot["start_frame"] - shot["padding"]
            end = shot["end_frame"] + shot["padding"]
            store_a_cam = cmds.setAttr(f"{store_a_cam}.offset", start - 1001)
            cmds.playbackOptions(
                minTime=start,
                maxTime=end,
                animationStartTime=start,
                animationEndTime=end,
            )
            cmds.currentTime(start)
            cam_path = shot["cam_path"].split("/")
            maya_cam_path = shot['cam_path'].replace('/', '|')
            geo_path = [geo.replace("/", "|") for geo in shot["geo_paths"]]
            plate = cmds.imagePlane(
                camera=maya_cam_path,
                name="Plate",
                fileName=shot["back_plate"].replace("$F", "####"),
                showInAllViews=False,
                lookThrough=shot["cam_path"],
            )

            cmds.setAttr(f"{plate[1]}.useFrameExtension", 1)
            cmds.setAttr(f"{plate[1]}.ignoreColorSpaceFileRules", 1)
            cmds.expression(
                s=f"{plate[1]}.depth = {maya_cam_path}.farClipPlane;",
                name="imagePlaneDepthExpression",
                o="auto",
                ae=True,
                uc="all",
            )
            cmds.setAttr(f"{plate[1]}.colorSpace", os.environ["VIEW"], type="string")
            cmds.setAttr(
                f"{plate[1]}.frameCache",
                shot["end_frame"] - shot["start_frame"] + (2 * shot["padding"]),
            )
            cmds.setAttr(f"{plate[0]}.overrideEnabled", 1)
            cmds.setAttr(f"{plate[0]}.overrideDisplayType", 2)
            cmds.setAttr(f"{maya_cam_path}.overrideEnabled", 1)
            cmds.setAttr(f"{maya_cam_path}.overrideDisplayType", 1)

            if (
                cmds.objExists("Proxy_Geo")
                and cmds.nodeType("Proxy_Geo") == "displayLayer"
            ):
                cmds.editDisplayLayerMembers("Proxy_Geo", geo_path, noRecurse=True)
            else:
                layer = cmds.createDisplayLayer(
                    geo_path, name="Proxy_Geo", noRecurse=True
                )
                cmds.setAttr(f"{layer}.displayType", 2)
                cmds.setAttr(f"{layer}.color", 27)

            shot_path = cmds.group(["|".join(cam_path[:2])] + geo_path, name="Shot")

            cmds.setAttr(f"{shot_path}.hiddenInOutliner", True)

            cmds.rename(f"|{shot_path}{'|'.join(cam_path[:-1])}", "Camera")
            cmds.rename(plate[1], "Plate")
            cmds.select(clear=True)

            if not cmds.attributeQuery(
                "loadedShot", node="defaultRenderGlobals", exists=True
            ):
                cmds.addAttr(
                    "defaultRenderGlobals", longName="loadedShot", dataType="string"
                )
            cmds.setAttr(
                "defaultRenderGlobals.loadedShot", str(shot["_id"]), type="string"
            )

            script_job = cmds.scriptJob(event=["timeChanged", handle_change])
            if not cmds.attributeQuery(
                "scriptJob", node="defaultRenderGlobals", exists=True
            ):
                cmds.addAttr("defaultRenderGlobals", longName="scriptJob")
            cmds.setAttr("defaultRenderGlobals.scriptJob", script_job)

            if not cmds.attributeQuery(
                "shotPath", node="defaultRenderGlobals", exists=True
            ):
                cmds.addAttr(
                    "defaultRenderGlobals", longName="shotPath", dataType="string"
                )
            cmds.setAttr(
                "defaultRenderGlobals.shotPath",
                shot_path,
                type="string",
            )

            if not cmds.attributeQuery(
                "frame", node="defaultRenderGlobals", exists=True
            ):
                cmds.addAttr(
                    "defaultRenderGlobals", longName="frame", dataType="float2"
                )
            cmds.setAttr(
                "defaultRenderGlobals.frame",
                shot["start_frame"],
                shot["end_frame"],
                type="float2",
            )

            if not cmds.attributeQuery(
                "offPipe", node="defaultRenderGlobals", exists=True
            ):
                cmds.addAttr("defaultRenderGlobals", longName="offPipe")
            cmds.setAttr("defaultRenderGlobals.offPipe", 0)

            if not cmds.attributeQuery(
                "shotNumber", node="defaultRenderGlobals", exists=True
            ):
                cmds.addAttr("defaultRenderGlobals", longName="shotNumber")
            cmds.setAttr("defaultRenderGlobals.shotNumber", shot["shot_number"])
