import os
from pathlib import Path
from pymongo.collection import ObjectId
from hop.hou.asset_management.textures import create_hash, resolve_texture
from hop.util import get_collection
from glob import glob
import clique
from hop.util import MultiProcess, convert_rat
from hop.hou.util import error_dialog
import hou
from shutil import rmtree


class Asset:
    asset_collection = get_collection("assets", "active_assets")
    shot_collection = get_collection("shots", "active_shots")
    hop_root = Path(os.environ["HOP"]) / "assets"

    class Update:
        def __init__(self, asset: "Asset"):
            self.asset = asset

        def model(self, proxy: bool):
            model_path = self.asset.get_path("model")
            proxy_path = self.asset.get_path("proxy") if proxy else None
            self.asset.asset_info["model"] = model_path if model_path else ""
            self.asset.asset_info["proxy"] = proxy_path if proxy_path else ""

        def mat(self, textures: list):
            mat_path = self.asset.get_path("mat")
            self.asset.asset_info["mat"] = mat_path if mat_path else ""
            self.asset.textures.extend(textures)

        def anim(self, proxy: bool):
            anim_path = self.asset.get_path("anim")
            if anim_path:
                proxy_path = self.asset.get_path("proxy") if proxy else None
                self.asset.asset_info["anim"] = anim_path
                self.asset.asset_info["proxy"] = proxy_path if proxy_path else ""

    def __init__(self, asset_name: str, override: str = "", branch: str = ""):
        if not self.check_name(asset_name):
            raise ValueError(
                f"Asset name '{asset_name}' not found in asset collection."
            )
        if not self.asset_dict.get("init") or not override:
            self.override = "main"
            self.shot_dict = None
        else:
            self.shot_dict = self.shot_collection.find_one({"_id": ObjectId(override)})
            if not self.shot_dict:
                raise ValueError(f"Shot with override id '{override}' not found.")
            self.override = override

            if not self.check_branch(branch):
                raise ValueError(f"Invalid branch '{branch}'. Must be 'anim' or 'fx'.")

        self.update = self.Update(self)
        self.asset_info = {"proxy": "", "model": "", "anim": "", "mat": ""}
        self.store_version = 1
        self.textures = []
        self.frame_range = (
            (self.shot_dict["start_frame"], self.shot_dict["end_frame"])
            if self.shot_dict
            else ()
        )

    def check_name(self, name: str) -> bool:
        self.asset_dict = self.asset_collection.find_one({"name": name})
        if not self.asset_dict:
            return False
        self.asset_name = name
        return True

    def check_branch(self, branch: str) -> bool:
        if branch not in ("anim", "fx"):
            return False
        self.branch = branch
        return True

    def version(self, key: str) -> int | None:
        if not self.asset_dict or key not in (
            "proxy",
            "model",
            "anim",
            "mat",
        ):
            return None

        if self.override == "main":
            if key == "anim":
                return None
            self.store_version = self.asset_dict.get("main") + 1
            return self.store_version
        if self.branch == "anim" and key not in ("anim", "proxy"):
            return None
        if key == "proxy" and not (self.asset_info["anim"] or self.asset_info["model"]):
            return None
        overrides = self.asset_dict.get("overrides", {})
        if self.override not in overrides:
            self.store_version = 1
            return 1
        else:
            branch_versions = overrides[self.override].get(self.branch, [])
            self.store_version = branch_versions + 1
            return self.store_version

    def get_path(self, key: str, usd: str = "usdc") -> str | None:
        version = self.version(key)
        if not version:
            return None
        base_folder = (
            Path(self.override) / self.branch if self.override != "main" else "main"
        )
        base = self.hop_root / self.asset_name / base_folder
        asset_ver = Path(f"V{version:02}") / f"{key}.{usd}"
        self.asset_info["branch_ver"] = str(
            base / f"V{version:02}" / f"{self.asset_name}.{usd}"
        ).replace("\\", "/")
        return str(base / asset_ver).replace("\\", "/")

    def publish(self, node):
        caching = node.parm("caching")

        stepping = 1 / 4
        store_step = 0

        def call_progress():
            nonlocal store_step
            nonlocal stepping
            store_step += stepping
            overall_progress.updateProgress(store_step)

        try:
            with hou.InterruptableOperation(
                "Publishing Asset",
                "Publishing Asset",
                open_interrupt_dialog=True,
            ) as overall_progress:
                caching.set(1)
                call_progress()

                node.parm("version").set(self.store_version)
                node.parm("store_override").set(
                    "main" if self.override == "main" else self.branch
                )

                if not self.asset_info or not (
                    branch_ver := Path(self.asset_info["branch_ver"])
                ):
                    caching.set(0)
                    return
                node.parm("branch_path").set(
                    str(branch_ver.parent.parent / branch_ver.name).replace("\\", "/")
                )
                call_progress()
                # Set Convert textures
                process = None
                texture_keys, hashs = [], []
                if self.asset_info["mat"] and self.textures:
                    args = []
                    for texture in self.textures:
                        files = glob(texture[0].replace("<UDIM>", "*"))
                        if not files:
                            return None
                        hashs.append(create_hash(texture[0]))
                        texture_keys.append(texture[1])
                        collection = clique.assemble(
                            files, minimum_items=1, patterns=[clique.PATTERNS["frames"]]
                        )[0][0]
                        frames = sorted(list(collection.indexes))
                        for index, file in enumerate(collection):
                            args.append((
                                file,
                                texture[1].replace("<UDIM>", f"{frames[index]:04}"),
                            ))
                    process = MultiProcess(
                        convert_rat, args, interpreter=os.environ["PYTHON"]
                    ).execute()
                call_progress()

                # Export
                [
                    node.parm(f"{key}_publish").pressButton()
                    for key, path in self.asset_info.items()
                    if path
                    if key != "branch_ver"
                ]
                [
                    node.parm(f"reload_{key}").pressButton()
                    for key in self.asset_info
                    if key != "branch_ver"
                ]
                node.parm("reload_branch").pressButton()
                node.parm("branch_ver_publish").pressButton()
                call_progress()

                # Update Mongo
                if process:
                    process.retrieve()
                    [resolve_texture(*info) for info in zip(hashs, texture_keys)]
                if self.asset_dict:
                    if self.override == "main":
                        self.asset_dict["main"] = self.store_version
                        self.asset_dict["init"] = True
                        self.asset_collection.update_one(
                            {"name": self.asset_name}, {"$set": self.asset_dict}
                        )
                    else:
                        if self.override not in self.asset_dict["overrides"]:
                            self.asset_dict["overrides"][self.override] = {
                                "fx": 0,
                                "anim": 0,
                            }
                        self.asset_dict["overrides"][self.override][self.branch] = (
                            self.store_version
                        )
                        self.asset_collection.update_one(
                            {"name": self.asset_name}, {"$set": self.asset_dict}
                        )
                        if self.shot_dict:
                            self.shot_dict["assets"].append(
                                self.asset_name
                            ) if self.asset_name not in self.shot_dict[
                                "assets"
                            ] else None
                            self.shot_collection.update_one(
                                {"_id": ObjectId(self.override)},
                                {"$set": self.shot_dict},
                            )
                call_progress()
                node.parm("init").set(1)

        except hou.OperationInterrupted:
            try:
                rmtree(str(Path(self.asset_info["branch_ver"]).parent))
            except FileNotFoundError:
                pass
            try:
                error_dialog("Publish Asset", "Error Publishing Shot")
            except hou.OperationInterrupted:
                pass
        finally:
            caching.set(0)
