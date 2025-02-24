from hop.util import get_collection
from pymongo.collection import ObjectId
import os


def resolve_texture(hash, path: str = ""):
    hop_value, hop_id = os.environ["HOP"], "$HOP"
    hash = ObjectId(hash)
    collection = get_collection("assets", "textures")
    texture_dict = collection.find_one({"_id": hash})
    if not texture_dict and path:
        texture_dict = {"_id": hash, "path": path.replace(hop_value, hop_id)}
        collection.insert_one(texture_dict)
    return texture_dict["path"].replace(hop_id, hop_value) if texture_dict else None
