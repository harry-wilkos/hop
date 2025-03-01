from argparse import ArgumentParser
from hop.util import get_collection
import logging


def create_asset(name: str):
    logger = logging.getLogger("HOP Asset Publish")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        logger.addHandler(console_handler)
    logging.getLogger().setLevel(logging.WARNING)
    name = name.lower().rstrip().lstrip()
    collection = get_collection("assets", "active_assets")
    existing = collection.find_one({"name": name})
    if existing:
        logger.warning(f"{name.capitalize()} already exists")
        return 1
    asset_dict = {
        "name": name,
        "init": False,
        "main": 0,
        "overrides": {},
    }
    collection.insert_one(asset_dict)
    logger.info(f"{name.capitalize()} published!")
    return 0


if __name__ == "__main__":
    parser = ArgumentParser(description="Create a new asset.")
    parser.add_argument("name", help="The name of the asset")
    args = parser.parse_args()
    create_asset(name=args.name)
