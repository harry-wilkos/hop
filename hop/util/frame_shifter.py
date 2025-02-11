import os
from glob import glob
from pathlib import Path
from argparse import ArgumentParser


def shift(start_folder: str, pattern: str, start: int):
    for walk in os.walk(start_folder):
        folder = Path(walk[0])
        files = sorted(glob(str(folder / pattern)))
        if files:
            temp_names = [
                f"tmp_{folder / pattern.replace("*", str(i))}" for i in range(len(files))
            ]

            for temp_name, back_plate in zip(temp_names, files):
                print(f"Temp Renaming: {back_plate} -> {temp_name}")
                os.rename(back_plate, temp_name)

            for count, temp_name in enumerate(temp_names):
                new_name = folder / pattern.replace("*", str(start + count))
                print(f"Renaming: {temp_name} -> {new_name}")
                os.rename(temp_name, new_name)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Recursivly convert shift an file sequences frame number"
    )
    parser.add_argument("start_folder", help="The root folder to start searching")
    parser.add_argument(
        "pattern",
        help="the pattern to match a sequence by",
    )
    parser.add_argument(
        "start",
        type=int,
        help="the new start number of the sequence",
    )

    args = parser.parse_args()
    shift(args.start_folder, args.patthern, args.start)
