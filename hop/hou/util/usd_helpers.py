from pxr.Usd import Stage, Prim
from pxr import UsdGeom


def expand_stage(stage: Stage, depth: int | None = None) -> Prim:
    queue = [(stage.GetPrimAtPath("/"), 0)]
    while queue:
        current_prim, current_depth = queue.pop(0)
        yield current_prim
        if depth is not None and current_depth >= depth:
            continue
        queue.extend((child, current_depth + 1) for child in current_prim.GetChildren())


def clean_stage(stage: Stage) -> None:
    all_prims = list(expand_stage(stage))
    all_prims.reverse()
    for prim in all_prims:
        if prim.IsPseudoRoot():
            continue
        if prim.GetTypeName() in {"Xform", "Scope", ""}:
            if not prim.GetChildren():
                prim.GetStage().RemovePrim(prim.GetPath())
            elif all(child.IsInstanceProxy() for child in prim.GetChildren()):
                prim.GetStage().RemovePrim(prim.GetPath())
