from argparse import ArgumentParser
from hop.util import get_collection
import os
from pathlib import Path
from datetime import datetime
from hop.util.api_helpers import post


def backup(
    start_folder: str,
    ignore_folders: list = [],
    ignore_folder_names: list = [],
    ignore_file_types: list = [],
):
    collection = get_collection("backups", "files")
    ignore_paths = [
        os.path.abspath(os.path.join(start_folder, ignore)) for ignore in ignore_folders
    ]
    for walk in os.walk(start_folder):
        folder = walk[0]
        if any(
            skip_string.lower() in [part.lower() for part in Path(folder).parts]
            for skip_string in ignore_folder_names
        ):
            continue

        for file in walk[2]:
            path = os.path.abspath(os.path.join(folder, file)).replace("\\", "\\\\")
            if any(
                path == ignore or path.startswith(ignore) for ignore in ignore_paths
            ):
                continue

            if any(file.lower().endswith(ext.lower()) for ext in ignore_file_types):
                continue

            file_time = datetime.fromtimestamp(os.stat(path).st_mtime).timestamp()
            doc = collection.find_one({"path": path})
            upload_file = True
            delete = False
            if doc is not None:
                if doc["time"] < file_time:
                    delete = True
                else:
                    upload_file = False

            if upload_file is True:
                file_parts = list(Path(path.replace(start_folder, "")).parts)
                if file_parts[0] == os.sep:
                    file_parts.pop(0)
                file_parts.insert(0, "backup")
                if delete:
                    post("delete", {"location": file_parts})
                post("upload", {"location": file_parts[:-1], "uuid": False}, path)

                if doc is None:
                    collection.insert_one({
                        "path": path,
                        "time": file_time,
                    })
                else:
                    collection.update_one({"path": path}, {"$set": {"time": file_time}})


if __name__ == "__main__":
    parser = ArgumentParser(description="Backup files with ignore options.")
    parser.add_argument(
        "start_folder", help="The root folder to start the backup process."
    )
    parser.add_argument(
        "--ignore-folders",
        nargs="*",
        default=[],
        help="List of specific folder paths to ignore (relative to start_folder).",
    )
    parser.add_argument(
        "--ignore-folder-names",
        nargs="*",
        default=[],
        help="List of folder names to ignore (e.g., '__pycache__', '.git').",
    )
    parser.add_argument(
        "--ignore-file-types",
        nargs="*",
        default=[],
        help="List of file extensions to ignore (e.g., '.tmp', '.log').",
    )

    args = parser.parse_args()
    backup(
        start_folder=args.start_folder,
        ignore_folders=args.ignore_folders,
        ignore_folder_names=args.ignore_folder_names,
        ignore_file_types=args.ignore_file_types,
    )
