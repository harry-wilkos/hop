from hop.util import get_collection
from pymongo.collection import ObjectId
import os
from glob import glob
import clique
import hashlib
from pathlib import Path


def resolve_texture(hash, path: str = ""):
    hop_value, hop_id = str(Path(os.environ["HOP"])), "$HOP"
    hash = ObjectId(hash)
    collection = get_collection("assets", "textures")
    texture_dict = collection.find_one({"_id": hash})
    if not texture_dict and path:
        texture_dict = {"_id": hash, "path": path.replace(hop_value, hop_id)}
        collection.insert_one(texture_dict)
    return texture_dict["path"].replace(hop_id, hop_value) if texture_dict else None


def create_hash(path: str):
    hash = ""
    files = glob(path.replace("<UDIM>", "*"))
    if not files:
        return None
    assembly = clique.assemble(
        files, minimum_items=1, patterns=[clique.PATTERNS["frames"]]
    )
    if pattern := assembly[0]:
        resolved_sequence = pattern[0]
    else:
        resolved_sequence = assembly[1]
    for file in resolved_sequence:
        stat = os.stat(file)
        hash += f"{file}{stat.st_mtime}{stat.st_size}"
    return hashlib.blake2b(hash.encode("utf-8"), digest_size=12).hexdigest()
