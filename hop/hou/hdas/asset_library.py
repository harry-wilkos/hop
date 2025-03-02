from pathlib import Path
from pxr.Usd import Stage
from pxr import UsdShade, UsdGeom, Sdf
from hop.hou.util import usd_helpers
import hou
from hop.hou.asset_management import resolve_texture, create_hash
from hop.util import get_collection
from hop.hou.asset_management import Asset

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



def publish(kwargs):
    node = kwargs["node"]
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
        root = Path(mat_path).parent if (mat_path := asset.get_path("mat")) else None
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
    asset.publish(node)

def load_frame_range(kwargs: dict):
    node = kwargs["node"]
    value = kwargs["script_value"]
    print(value)
