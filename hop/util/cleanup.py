from argparse import ArgumentParser
import logging
import os
from pathlib import Path
from datetime import datetime


def cleanup(start_folder: str, hours: float, verbose: bool = False):
    logger = logging.getLogger("HOP Cleanup")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        logger.addHandler(console_handler)

    current_time = datetime.now().timestamp()
    cutoff_time = current_time - (hours * 3600)
    logger.debug(f"Current time: {datetime.fromtimestamp(current_time)}")
    logger.debug(f"Cutoff time: {datetime.fromtimestamp(cutoff_time)}")

    for root, _, files in os.walk(start_folder, topdown=False):
        for file in files:
            file_path = Path(root) / file
            logger.debug(f"Checking: {str(file_path)}")
            file_mtime = file_path.stat().st_mtime
            if file_mtime < cutoff_time:
                logger.info(f"Removing: {file_path} (Older than cutoff)")
                file_path.unlink()
        if not os.listdir(root):
            logger.info(f"Removing: {root} (Empty)")
            os.rmdir(root)


if __name__ == "__main__":
    parser = ArgumentParser(description="Cleanup files older than the specified hours")
    parser.add_argument(
        "start_folder",
        nargs="?",
        default=os.environ.get("HOP_TEMP"),
        help="Root folder to clean (default: HOP_TEMP environment variable)",
    )
    parser.add_argument(
        "--time", type=float, default=24, help="Age threshold in hours (default: 24)"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if not args.start_folder:
        parser.error(
            "start_folder must be provided or set HOP_TEMP environment variable"
        )

    cleanup(args.start_folder, args.time, args.verbose)

