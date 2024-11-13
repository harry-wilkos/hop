import _alembic_hom_extensions as abc
import os


def find_cam_path(path: str) -> str | None:
    h_path = ""
    children = abc.alembicGetSceneHierarchy(path, h_path)[2]
    while children:
        for child in children:
            obj_name, obj_type, children = child
            h_path = f"{h_path}/{obj_name}"
            if obj_type == "camera":
                return h_path
            if type(children) is tuple and len(children) == 3:
                continue
            else:
                break
    return None


def frame_info(path: str, frame_rate: float | None = None) -> tuple | None:
    if not os.path.exists(path):
        return None
    start_time, end_time = abc.alembicTimeRange(path)
    frame_rate = frame_rate or next(
        rate for rate in range(1, 120) if int(start_time * rate) >= 1001
    )
    start_frame = int(start_time * frame_rate)
    end_frame = int(end_time * frame_rate)

    return start_frame, end_frame, frame_rate


if __name__ == "__main__":
    print(find_cam_path("/home/Harry/Twelvefold/pipeline/exports/Shot_060_Track.abc"))
    # print(frame_info("/home/Harry/Twelvefold/pipeline/exports/Shot_060_Track.abc"))
