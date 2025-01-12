from pxr.Usd import Stage, Prim
from pxr import Sdf


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


def normalize_path(prim: Prim, path: str):
    if path.startswith("@") and path.endswith("@"):
        path = path[1:-1]
    path = Sdf.ComputeAssetPathRelativeToLayer(prim.GetStage().GetRootLayer(), path)
    return path


def compare_scene(stage: Stage, file: str, time_check: bool = False) -> bool:
    store = Stage.Open(file)

    for prim in stage.Traverse():
        if prim.GetName() == "HoudiniLayerInfo":
            continue

        st_prim = store.GetPrimAtPath(prim.GetPath())
        if not st_prim:
            return False

        st_prim_relationships = {rel.GetName() for rel in st_prim.GetRelationships()}
        for rel in prim.GetRelationships():
            rel_name = rel.GetName()
            if rel_name not in st_prim_relationships:
                return False
            st_prim_relationships.remove(rel_name)

            st_rel = st_prim.GetRelationship(rel_name)
            if rel.GetTargets() != st_rel.GetTargets():
                return False

        if st_prim_relationships:
            return False

        st_prim_attributes = {attr.GetName() for attr in st_prim.GetAttributes()}
        for attr in prim.GetAttributes():
            attr_name = attr.GetName()
            if attr_name not in st_prim_attributes:
                return False
            st_prim_attributes.remove(attr_name)

            st_attr = st_prim.GetAttribute(attr_name)
            if not st_attr:
                return False

            st_time_samples = st_attr.GetTimeSamples()
            attr_time_samples = attr.GetTimeSamples()

            if st_time_samples and attr_time_samples:
                samples = attr_time_samples
                if time_check:
                    samples = st_time_samples
                    if st_time_samples != attr_time_samples:
                        return False

                for time in samples:
                    st_value = st_attr.Get(time)
                    attr_value = attr.Get(time)
                    if type(st_value) is Sdf.AssetPath:
                        st_value = st_value.resolvedPath
                    if type(attr_value) is Sdf.AssetPath:
                        attr_value = attr_value.resolvedPath

                    if st_value != attr_value:
                        return False
            else:
                st_default_value = st_attr.Get()
                attr_default_value = attr.Get()

                if type(st_default_value) is Sdf.AssetPath:
                    st_default_value = st_default_value.resolvedPath
                if type(attr_default_value) is Sdf.AssetPath:
                    attr_default_value = attr_default_value.resolvedPath

                if st_default_value != attr_default_value:
                    return False

        if st_prim_attributes:
            return False

    return True
