from pxr.Usd import Stage
from hop.hou.util import usd_helpers
from pxr import UsdShade, UsdGeom, Sdf


def check_materials(stage: Stage):
    mats = []
    for prim in usd_helpers.expand_stage(stage):
        if prim.IsA(UsdShade.Material):
            name = prim.GetName()
            if name not in mats:
                mats.append(name)
                continue
            return False
    return True


def reassign_materials(stage: Stage):
    for prim in usd_helpers.expand_stage(stage):
        imageable = UsdGeom.Imageable(prim)
        if not imageable:
            continue
        visibility = imageable.ComputeVisibility()
        if visibility == UsdGeom.Tokens.invisible:
            continue
        binding_api = UsdShade.MaterialBindingAPI(prim)
        material, rel = binding_api.ComputeBoundMaterial()
        if rel:
            print(prim)
            # material_name = material.GetPrim().GetName()
            new_path = Sdf.Path(f"/Asset_Name/mtl/test")
            rel.SetTargets([new_path])
            binding_api.SetMaterialBindingStrength(
                rel, UsdShade.Tokens.strongerThanDescendants
            )
