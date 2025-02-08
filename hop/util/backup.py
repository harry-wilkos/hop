from argparse import ArgumentParser
from hop.util import get_collection
import os
from pathlib import Path
from datetime import datetime
from hop.util.api_helpers import post
import logging


def backup(
    start_folder: str,
    ignore_folders: list = [],
    ignore_folder_names: list = [],
    ignore_file_types: list = [],
    verbose: bool = False,
):
    logger = logging.getLogger("HOP Backup")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(console_handler)
    logging.getLogger().setLevel(logging.WARNING)

    collection = get_collection("backups", "files")
    ignore_paths = [Path(start_folder) / ignore for ignore in ignore_folders]
    for walk in os.walk(start_folder):
        folder = walk[0]
        folder_parts = [part.lower() for part in Path(folder).parts]

        if any(
            skip_string.lower() in folder_parts for skip_string in ignore_folder_names
        ):
            logger.debug(f"Skipping {folder}: Ignored folder name")
            continue
        for file in walk[2]:
            path = Path(folder) / file
            if any(
                path == ignore or path.is_relative_to(ignore) for ignore in ignore_paths
            ):
                logger.debug(f"Skipping {str(path)}: Ignored path")
                continue
            if any(file.lower().endswith(ext.lower()) for ext in ignore_file_types):
                logger.debug(f"Skipping {str(path)}: Ignored file type")
                continue
            file_time = datetime.fromtimestamp(os.stat(str(path)).st_mtime).timestamp()
            doc = collection.find_one({"path": str(path)})
            upload_file = True
            delete = False
            if doc is not None:
                if doc["time"] < file_time:
                    delete = True
                else:
                    logger.debug(f"Skipping {str(path)}: No change")
                    upload_file = False

            if upload_file:
                file_parts = list(Path(str(path).replace(start_folder, "")).parts)
                if file_parts[0] == os.sep:
                    file_parts.pop(0)
                file_parts.insert(0, "backup")
                if delete:
                    logger.info(f"Deleting {str(path)}")
                    post("delete", {"location": file_parts})
                logger.info(f"Uploading {str(path)}")
                post("upload", {"location": file_parts[:-1], "uuid": False}, str(path))

                if doc is None:
                    collection.insert_one({
                        "path": str(path),
                        "time": file_time,
                    })
                else:
                    collection.update_one(
                        {"path": str(path)}, {"$set": {"time": file_time}}
                    )


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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (prints debug information)",
    )
    args = parser.parse_args()
    backup(
        start_folder=args.start_folder,
        ignore_folders=args.ignore_folders,
        ignore_folder_names=args.ignore_folder_names,
        ignore_file_types=args.ignore_file_types,
        verbose=args.verbose,
    )
