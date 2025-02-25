from pathlib import Path
from pxr.Usd import Stage
from pxr import UsdShade, UsdGeom, Sdf
from hop.hou.util import usd_helpers
from glob import glob
import clique
import os
import hashlib
import hou
from hop.hou.asset_management import resolve_texture
from hop.util import get_collection


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
    root = Path(hou.node("../").evalParm("mtl_path")).parent
    for prim in stage.Traverse():
        if prim.IsA(UsdShade.Material):
            for node in usd_helpers.expand_stage(stage, start=prim.GetPath()):
                for attr in node.GetAttributes():
                    hash = ""
                    if attr.HasValue() and isinstance(
                        path := attr.Get(), Sdf.AssetPath
                    ):
                        path = path.path
                        files = clique.assemble(glob(path.replace("<UDIM>", "*")))[0][0]
                        for file in files:
                            stat = os.stat(file)
                            hash += f"{file}{stat.st_mtime}{stat.st_size}"
                        update_path = str(
                            root
                            / "textures"
                            / prim.GetName()
                            / f"{node.GetName()}.<UDIM>.rat"
                        )
                        attr.Set(update_path)

                    if hash:
                        hex_hash = hashlib.blake2b(
                            hash.encode("utf-8"), digest_size=12
                        ).hexdigest()
                        hash_attr = node.CreateAttribute(
                            "hop:hash", Sdf.ValueTypeNames.String
                        )
                        hash_attr.Set(hex_hash)
                        if texture_path := resolve_texture(hex_hash):
                            attr.Set(texture_path)


def retrieve_assets() -> list:
    collection = get_collection("assets", "active_assets")
    assets = ["", "Select Asset..."]
    for asset in collection.find({}).sort("name", 1):
        name = asset["name"]
        assets.append(name)
        assets.append(name.capitalize())
    return assets


def check_branches() -> list:
    asset = hou.pwd().evalParm("name")
    collection = get_collection("assets", "active_assets")
    collection.find_one({"name": asset})

    options = ["main", "Main"]
    if (
        not (asset_dict := collection.find_one({"name": asset}))
        or not asset_dict["init"]
    ):
        return options
    return options + ["anim", "Anim", "fx", "FX"]
