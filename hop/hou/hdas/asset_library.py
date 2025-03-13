from pathlib import Path
from pxr.Usd import Stage
from pxr import UsdShade, UsdGeom, Sdf
from hop.hou.util import usd_helpers, error_dialog, confirmation_dialog
import hou
from hop.hou.asset_management import resolve_texture, create_hash
from hop.util import get_collection
from hop.hou.asset_management import Asset
from pymongo.collection import ObjectId
from shutil import rmtree
from hop.dl import create_job, call_deadline
from tempfile import NamedTemporaryFile
from hop.util import post
import os

collection = get_collection("assets", "active_assets")
shot_collection = get_collection("shots", "active_shots")


def check_materials(stage: Stage):
    mats = set()
    for prim in stage.Traverse():
        if prim.IsA(UsdShade.Material):
            name = prim.GetName()
            if name in mats:
                return False
            mats.add(name)
            continue
    return True


def check_prims(stage: Stage):
    mats = set()
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Boundable):
            name = prim.GetName()
            if name in mats:
                return False
            mats.add(name)
            continue
    return True


def tag_textures(stage: Stage):
    root = Path(hou.node("../").evalParm("mat_path")).parent
    for prim in stage.Traverse():
        if prim.IsA(UsdShade.Material):
            for node in usd_helpers.expand_stage(stage, start=prim.GetPath()):
                for attr in node.GetAttributes():
                    if attr.HasValue() and isinstance(
                        path := attr.Get(), Sdf.AssetPath
                    ):
                        path = path.path
                        update_path = str(
                            root
                            / "textures"
                            / prim.GetName()
                            / f"{node.GetName()}.<UDIM>.rat"
                        )
                        attr.Set(update_path)
                        hash = create_hash(path)
                        if hash:
                            hash_attr = node.CreateAttribute(
                                "hop:hash", Sdf.ValueTypeNames.String
                            )
                            hash_attr.Set(hash)
                            if texture_path := resolve_texture(hash):
                                attr.Set(texture_path)


def retrieve_assets() -> list:
    assets = ["", "Select Asset..."]
    for asset in collection.find({}).sort("name", 1):
        name = asset["name"]
        assets.append(name)
        assets.append(name.capitalize())
    return assets


def retrieve_overrides() -> list:
    overrides = ["", "Select Shot..."]
    for shot in shot_collection.find({}).sort("shot_number", 1):
        overrides.append(str(shot["_id"]))
        overrides.append(f"Shot {shot['shot_number']:02}")
    return overrides


def check_init(kwargs):
    node = kwargs["node"]
    asset = node.evalParm("name")
    init = node.parm("init")
    if (
        not (asset_dict := collection.find_one({"name": asset}))
        or not asset_dict["init"]
    ):
        init.set(False)
    else:
        init.set(True)
    node.parm("override").set("")
    node.parm("toggle_override").set(0)


def publish(node, farm=False) -> Asset | None:
    stepping = 1 / 2
    store_step = 0
    asset = None

    def call_progress():
        nonlocal store_step
        nonlocal stepping
        store_step += stepping
        overall_progress.updateProgress(store_step)

    try:
        with hou.InterruptableOperation(
            "Pre-Publishing Asset",
            "Pre-Publishing Asset",
            open_interrupt_dialog=True,
        ) as overall_progress:
            name = node.evalParm("name")
            override, branch = "", ""
            if node.evalParm("toggle_override"):
                override = node.evalParm("override")
                branch = node.evalParm("branch")

            asset = Asset(name, override, branch)
            proxy = False if node.evalParm("proxy_type") == 0 else True
            if bool(node.node("INPUT").evalParm("anim_prims")):
                asset.update.anim(proxy)
            if bool(node.node("Geo_Check").evalParm("prims")):
                asset.update.model(proxy)
            if bool(node.node("Mat_Check").evalParm("mats")):
                root = (
                    Path(mat_path).parent
                    if (mat_path := asset.get_path("mat"))
                    else None
                )
                if root:
                    textures = []
                    stage = node.node("Anim_Mat_Check").stage()
                    for prim in node.node("Anim_Mat_Check").stage().Traverse():
                        if prim.IsA(UsdShade.Material):
                            for texture_node in usd_helpers.expand_stage(
                                stage, start=prim.GetPath()
                            ):
                                for attr in texture_node.GetAttributes():
                                    if attr.HasValue() and isinstance(
                                        path := attr.Get(), Sdf.AssetPath
                                    ):
                                        if hash := create_hash(path.path):
                                            if not resolve_texture(hash):
                                                textures.append((
                                                    path.path,
                                                    str(
                                                        root
                                                        / "textures"
                                                        / prim.GetName()
                                                        / f"{texture_node.GetName()}.<UDIM>.rat"
                                                    ),
                                                ))

                    asset.update.mat(textures)
            if not farm:
                call_progress()
                if asset.override == "main":
                    debug = node.node("Debug_Info")
                    debug.cook(force=True)
                    errors = node.node("Debug_Info").warnings()
                    if errors and not confirmation_dialog(
                        "Asset Publisher", "\n".join(errors)
                    ):
                        return
                if not asset.asset_dict:
                    error_dialog("Asset Publisher", "Failed to initalise asset")
                    return
                # Set Parms
                run = False
                for key, path in asset.asset_info.items():
                    node.parm(f"{key}_path").set(path)
                    if path:
                        run = True
                if not run:
                    hou.ui.displayMessage(
                        "Nothing to publish",
                        severity=hou.severityType.ImportantMessage,
                    )
                    return
            call_progress()
            return asset
    except hou.OperationInterrupted:
        try:
            if asset:
                rmtree(str(Path(asset.asset_info["branch_ver"]).parent))
        except FileNotFoundError:
            pass
        try:
            error_dialog("Publish Asset", "Error Publishing Shot")
        except hou.OperationInterrupted:
            pass


def local_publish(kwargs):
    node = kwargs["node"]
    asset = publish(node)
    result = asset.publish(node) if asset else None
    if result:
        hou.ui.displayMessage(
            f" The {(asset.branch if asset.override != 'main' else 'Main').capitalize()} {asset.asset_name} branch was updated to V{asset.store_version:02}!"
        )


def farm_execute(kwargs):
    node = kwargs["node"]
    asset = publish(node, True)
    if asset:
        shot_message = (
            f"in **Shot {asset.shot_dict['shot_number']}** " if asset.shot_dict else ""
        )
        post(
            "discord",
            {
                "message": f":green_circle: **{(asset.branch if asset.override != 'main' else 'Main').capitalize()} {asset.asset_name.capitalize()} V{asset.store_version:02}**  started publishing {shot_message}:green_circle:"
            },
        )

        asset.publish(node)


def farm_publish(kwargs):
    node = kwargs["node"]
    asset = publish(node)
    hip = hou.hipFile
    if hip.hasUnsavedChanges():
        if confirmation_dialog(
            "Farm Cache",
            "The scene must be saved before submission",
            default_choice=0,
        ):
            hip.save()
        else:
            return

    if not asset:
        return
    path = hip.path()
    hip.saveAndIncrementFileName()

    python_file = NamedTemporaryFile(
        delete=False,
        mode="w",
        encoding="utf-8",
        suffix=".py",
        dir=os.path.normpath(os.environ["HOP_TEMP"]),
    )
    python_file.write(f"hou.node('{node.path()}').parm('farm_execute').pressButton()")
    python_file.close()

    job = create_job(
        asset.asset_name.capitalize(),
        "Main" if asset.override == "main" else asset.branch.capitalize(),
        1001,
        1001,
        1,
        1,
        "UHFarmCache",
        "sim",
    )

    plugin = NamedTemporaryFile(
        delete=False, mode="w", encoding="utf-16", suffix=".job"
    )
    plugin.write(f"SceneFile={path}\n")
    plugin.write(f"cacheMeFile={python_file.name}\n")
    plugin.close()
    call_deadline([job, plugin.name])
    hou.ui.displayMessage(
        f"{asset.asset_name.capitalize()} submitted to the farm", title="Asset Publish"
    )
    return


def load_frame_range(kwargs: dict):
    node = kwargs["node"]
    value = kwargs["script_value"]
    start = node.parm("frame_rangex")
    end = node.parm("frame_rangey")
    if not value:
        start.setExpression("$FSTART", replace_expression=True)
        end.setExpression("$FEND", replace_expression=True)
    else:
        shot_dict = shot_collection.find_one({"_id": ObjectId(value)})
        if shot_dict:
            start.deleteAllKeyframes()
            start.set(1001)
            end.deleteAllKeyframes()
            end.set(shot_dict["end_frame"] - shot_dict["start_frame"] + 1001)


def retrieve_shot_assets(kwargs) -> list:
    node = kwargs["node"]
    assets = ["", "Select Asset..."]
    if shot := node.evalParm("shot"):
        shot_dict = shot_collection.find_one({"_id": ObjectId(shot)})
        if shot_dict:
            shot_assets = tuple(shot_dict["assets"])
            for asset in shot_assets:
                asset_dict = collection.find_one({"name": asset})
                if asset_dict:
                    assets.append(asset)
                    assets.append(asset.capitalize())
    return list(assets)


def unload_shot(kwargs):
    node = kwargs["node"]
    node.parm("asset").set("")
    node.parm("load").set(False)
    for parm in ("main", "anim", "fx"):
        node.parm(f"{parm}_ver").set(-1)


def retrieve_asset_versions(kwargs) -> list:
    node = kwargs["node"]
    branch = kwargs["parm"].name().split("_")[0]
    asset = node.evalParm("asset")
    asset = node.evalParm("asset")
    versions = ["-1", "Latest Version"]
    loops = 0
    if asset and (asset_dict := collection.find_one({"name": asset})):
        if branch == "main":
            loops = asset_dict["main"]
        elif (shot := node.evalParm("shot")) and shot in asset_dict["overrides"]:
            shot_override = asset_dict["overrides"][shot]
            loops = (
                shot_override[branch]
                if branch in (shot_override := asset_dict["overrides"][shot])
                else 0
            )
    for ver in range(loops):
        versions.append(str(ver))
        versions.append(f"V{ver + 1:02}")

    return versions


def check_shot_subnet(kwargs):
    node = kwargs["node"]
    parent = node.parent().parent()
    if (
        parent.type().name().split(":")[0] == "Shot"
        and (shot_num := parent.evalParm("load_shot")) > 0
    ):
        shot_dict = shot_collection.find_one({"shot_number": shot_num})
        node.parm("shot").set(str(shot_dict["_id"])) if shot_dict else None
    node.setColor(hou.Color(1, 0.9, 0.6))
