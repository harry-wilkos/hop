from hop.util import get_collection
import os
from pathlib import Path
from sys import argv
from datetime import datetime
from hop.util.api_helpers import post


def backup(start_folder: str, ignore_folders: list = []):
    collection = get_collection("backups", "files")
    ignore_paths = [
        os.path.abspath(os.path.join(start_folder, ignore)) for ignore in ignore_folders
    ]
    for walk in os.walk(start_folder):
        folder = walk[0]
        if any(
            skip_string.lower() in [part.lower() for part in Path(folder).parts]
            for skip_string in ["__pycache__", "cache", "tmp", ".git", "backup", "temp"]
        ):
            continue

        for file in walk[2]:
            path = os.path.abspath(os.path.join(folder, file))
            if any(
                path == ignore or path.startswith(ignore) for ignore in ignore_paths
            ):
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
                file_parts.insert(0, "external_drive")
                print("upload", {"location": file_parts, "uuid": False}, path)
                post("upload", {"location": file_parts, "uuid": False}, path)


if __name__ == "__main__":
    backup("/home/Harry/Downloads")
