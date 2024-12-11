from pxr.Usd import Stage, Prim


def expand_stage(stage: Stage) -> Prim:
    prims_stack = [stage.GetPrimAtPath("/")]
    while prims_stack:
        current_prim = prims_stack.pop()
        yield current_prim
        prims_stack.extend(current_prim.GetChildren())
