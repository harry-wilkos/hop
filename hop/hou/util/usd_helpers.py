from pxr.Usd import Stage, Prim
from pxr import Sdf
import hou


def expand_stage(stage: Stage, depth: int | None = None, start: str = "/") -> Prim:
    queue = [(stage.GetPrimAtPath(start), 0)]
    while queue:
        current_prim, current_depth = queue.pop(0)
        yield current_prim
        if depth is not None and current_depth >= depth:
            continue
        queue.extend((child, current_depth + 1) for child in current_prim.GetChildren())


def check_default(prim: Prim) -> bool:
    for attr in prim.GetAttributes():
        if attr.GetNumTimeSamples() != 0 or attr.GetConnections():
            return False

        resolved_value = attr.Get()
        if attr.HasAuthoredValue():
            if (
                resolved_value
                != attr.GetPrim()
                .GetPrimDefinition()
                .GetAttributeFallbackValue(attr.GetName())
            ):
                return False

    for rel in prim.GetRelationships():
        if rel.HasAuthoredTargets():
            return False

    return True


def reparent_prim(prim_path: str, destionation_path: str, stage: Stage) -> None:
    prim = Sdf.Path(prim_path)
    destination = Sdf.Path(destionation_path)

    layer = stage.GetEditTarget().GetLayer()
    if not prim.IsAbsolutePath() or not destination.IsAbsolutePath():
        raise ValueError("Source and destination primitive paths must be absolute.")
    new_src_path = destination.AppendChild(prim.name)

    with Sdf.ChangeBlock():
        edit = Sdf.BatchNamespaceEdit()
        edit.Add(prim, new_src_path)
        if layer.CanApply(edit):
            layer.Apply(edit)
        else:
            raise RuntimeError(f"Failed to apply reparenting edit to {prim_path}.")


def clean_stage(stage: Stage, force: bool = False) -> None:
    all_prims = list(expand_stage(stage))
    all_prims.reverse()
    for prim in all_prims:
        if prim.IsPseudoRoot():
            continue
        if check_default(prim):
            children = prim.GetChildren()
            if not force:
                if not children or all(child.IsInstanceProxy() for child in children):
                    stage.RemovePrim(prim.GetPath())
            else:
                parent_path = prim.GetPath().GetParentPath()
                for child in children:
                    reparent_prim(child.GetPath(), parent_path, stage)
                stage.RemovePrim(prim.GetPath())
        else:
            inert = ("Xform", "Scope", "")
            if prim.GetTypeName() in inert:
                children = list(expand_stage(stage, start=prim.GetPath()))
                children.reverse()
                for child in children:
                    if child.GetTypeName() in inert:
                        stage.RemovePrim(child.GetPath())
                    else:
                        break
