from .create_shot_entry import create_shot_entry


def create_shot_structure(lights: str, camera: str, plate: str) -> tuple:
    return lights, camera, plate


if __name__ == "__main__":
    shot_entry = create_shot_structure("lights", "camera1", "back_plate.hdr")
