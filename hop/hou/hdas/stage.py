from hop.hou.util import usd_helpers
from pxr import Sdf
import hou


def create_holdouts(skip: int):
    node = hou.pwd()
    shot = node.node("../")
    stage = node.editableStage()
    products = shot.evalParm("products")
    for product in range(products):
        if product  == skip:
            continue
        holdout = shot.evalParm(f"holdout{product + 1}").split(" ")
        if holdout != [""]:
            for prim_path in holdout:
                prim = stage.GetPrimAtPath(prim_path)
                prim.CreateAttribute(
                    "primvars:karma:object:holdoutmode", Sdf.ValueTypeNames.Int
                ).Set(2)
