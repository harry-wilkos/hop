import OpenEXR as exr
import os
from pathlib import Path
from argparse import ArgumentParser


def change_fps(start_folder: str, fps: int | None = None):
    fps = fps if type(fps) is int else int(os.environ["FPS"])

    for walk in os.walk(start_folder):
        folder = Path(walk[0])
        files = walk[2]
        for file in files:
            path = folder / file
            if not exr.isOpenExrFile(str(path)):
                continue
            with exr.File(str(path), separate_channels=True) as buffer:
                parts = []
                for part in buffer.parts:
                    header = dict(part.header)
                    if "framesPerSecond" in header.keys() and header["framesPerSecond"] == fps:
                        continue
                    header["framesPerSecond"] = fps
                    channels = {
                        name: ch.pixels.copy() for name, ch in part.channels.items()
                    }

                    parts.append(exr.Part(header, channels))

                if len(parts) > 0:
                    dir = Path(folder) / f"{fps}_FPS"
                    os.makedirs(str(dir), exist_ok=True)
                    output = str(dir / file)
                    if len(parts) == 1:
                        with exr.File(parts[0].header, parts[0].channels) as outfile:
                            outfile.write(output)
                    else:
                        with exr.File(parts) as outfile:
                            outfile.write(output)
                    print(f"{path} -> {output}")


if __name__ == "__main__":
    parser = ArgumentParser(description="Recursivly convert exr files fps value")
    parser.add_argument(
        "start_folder", help="The root folder to start searching for exrs"
    )
    parser.add_argument(
        "--fps",
        nargs=1,
        default=os.environ["FPS"],
        help="The desired FPS to convert to, default uses the 'FPS' environment variable",
    )
    args = parser.parse_args()
    change_fps(args.start_folder, args.fps)
