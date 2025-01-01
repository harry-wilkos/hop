import _alembic_hom_extensions as abc


def find_cam_paths(path: str) -> list:
    cams = []
    h_path = ""
    children = abc.alembicGetSceneHierarchy(path, h_path)[2]
    while children:
        for child in children:
            obj_name, obj_type, children = child
            h_path = f"{h_path}/{obj_name}"
            if obj_type == "camera":
                cams.append(h_path)
            if type(children) is tuple and len(children) == 3:
                continue
            else:
                break
    return cams


def frame_info(path: str, frame_rate: float | None = None) -> tuple:
    start_time, end_time = abc.alembicTimeRange(path)
    frame_rate = frame_rate or next(
        rate for rate in [24, 25, 48, 50, 60] if int(start_time * rate) >= 1001
    )
    start_frame = int(start_time * frame_rate)
    end_frame = int(end_time * frame_rate)

    return start_frame, end_frame, frame_rate


def find_geo_paths(path: str) -> list:
    geo = []
    stack = [("", abc.alembicGetSceneHierarchy(path, "")[2])]
    while stack:
        parent_path, children = stack.pop()
        for obj_name, obj_type, sub_children in children:
            current_path = f"{parent_path}/{obj_name}"
            if obj_type == "polymesh" and "camera" not in parent_path.lower():
                geo.append(current_path)
            if isinstance(sub_children, (list, tuple)) and sub_children:
                stack.append((current_path, sub_children))

    return geo
