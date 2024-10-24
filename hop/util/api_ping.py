import os
import requests
from pymongo import MongoClient
from pymongo.collection import Collection


def upload(
    filepath: str, location: list, api_address: str = "API_ADDRESS", uuid: bool = False
) -> dict:
    path = ""
    for i in location:
        path = os.path.join(path, i)
    url = f"{os.environ[api_address]}/upload"
    with open(filepath, "rb") as file:
        files = {"file": (file.name, file, "application/octet-stream")}
        resp = requests.post(url, files=files, data={"location": path, "uuid": uuid})
    return resp.json()


def post(method: str, data: dict, api_address: str = "API_ADDRESS") -> dict:
    url = f"{os.environ[api_address]}/{method}"
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=data)
    return resp.json()


def get_collection(
    database_name: str, collection_name: str, mongo_address: str = "MONGO_ADDRESS"
) -> Collection:
    client = MongoClient(os.environ[mongo_address])
    if database_name in client.list_database_names():
        db = client.get_database(database_name)
    else:
        db = client[database_name]
    if collection_name in db.list_collection_names():
        collection = db.get_collection(collection_name)
    else:
        collection = db[collection_name]
    return collection
