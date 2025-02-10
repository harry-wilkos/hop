import os
import requests
from pymongo import MongoClient
from pymongo.collection import Collection
import json
from pathlib import Path


def post(method: str, data: dict, file_path: str | None = None):
    url = f"{os.environ['API_ADDRESS']}/{method}"
    for key, value in data.items():
        data[key] = json.dumps(value)

    if not file_path:
        resp = requests.post(url, data=data)
    else:
        with open(file_path, "rb") as file:
            files = {"file": (file.name, file, "application/octet-stream")}
            resp = requests.post(
                url,
                files=files,
                data=data | {"source_path": json.dumps(list(Path(file_path).parts))},
            )
    return resp.json()


def get_collection(database_name: str, collection_name: str) -> Collection:
    client = MongoClient(os.environ["MONGO_ADDRESS"])
    if database_name in client.list_database_names():
        db = client.get_database(database_name)
    else:
        db = client[database_name]
    if collection_name in db.list_collection_names():
        collection = db.get_collection(collection_name)
    else:
        collection = db[collection_name]
    return collection


def find_shot(collection: Collection, start: int, end: int) -> dict:
    return list(
        collection.aggregate([
            {
                "$addFields": {
                    "start_diff": {"$abs": {"$subtract": ["$start_frame", start]}},
                    "end_diff": {"$abs": {"$subtract": ["$end_frame", end]}},
                    "range_diff": {
                        "$abs": {
                            "$subtract": [
                                {
                                    "$subtract": [
                                        "$end_frame",
                                        "$start_frame",
                                    ]
                                },
                                {"$subtract": [end, start]},
                            ]
                        }
                    },
                    "proximity_score": {
                        "$add": [
                            {"$abs": {"$subtract": ["$start_frame", start]}},
                            {"$abs": {"$subtract": ["$end_frame", end]}},
                        ]
                    },
                }
            },
            {"$sort": {"proximity_score": 1, "range_diff": 1}},
            {"$limit": 1},
        ])
    )[0]
