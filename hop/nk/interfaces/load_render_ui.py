from PySide2.QtWidgets import QPushButton, QDialog, QHBoxLayout, QSizePolicy, QComboBox
from hop.util import get_collection
from pymongo.collection import ObjectId
from pathlib import Path
import nuke


def find_shot(node):
    while node:
        parent = node.input(0)
        if parent and parent.knob("HOP") and parent.knob("HOP").value() == "shot":
            return parent
        else:
            node = parent


class RenderLoadUI(QDialog):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.collection = get_collection("shots", "active_shots")
        self.main_layout = QHBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        shot = find_shot(self.node)
        stored_id = (
            str(store_id.value())
            if (store_id := shot.knob("store_id") if shot else False)
            else False
        )
        if shot and shot.knob("off_pipe").value():
            self.collection = get_collection("shots", "retired_shots")
        self.renders = (
            doc["render_versions"]
            if (
                doc := self.collection.find_one({"_id": ObjectId(stored_id)})
                if stored_id
                else False
            )
            else []
        )
        self.make_version()
        self.make_holdouts()
        self.make_reload()

        version_index = self.node.knob("version").value()
        if version_index >= self.version_widget.count():
            version_index = 0
            self.node.knob("version").setValue(version_index)
        self.version_widget.setCurrentIndex(version_index)

        holdout_index = self.node.knob("holdout").value()
        if holdout_index >= self.holdout_widget.count():
            holdout_index = 0
            self.node.knob("holdout").setValue(holdout_index)
            with self.node.begin():
                nuke.toNode("Read1").knob("file").setValue("")
                nuke.toNode("DeepRead1").knob("file").setValue("")

        self.holdout_widget.setCurrentIndex(holdout_index)
        self.holdout_widget.currentIndexChanged.connect(self.load)

    def make_version(self):
        self.version_widget = QComboBox()
        self.version_widget.addItem("Select Version...")
        option_len = len(self.renders)
        if not option_len:
            self.version_widget.setEnabled(False)
        for version in range(0, option_len):
            self.version_widget.addItem(f"V{version + 1:02d}", self.renders[version])
        self.version_widget.currentIndexChanged.connect(self.update_holdouts)
        self.main_layout.addWidget(self.version_widget)

    def make_holdouts(self):
        self.holdout_widget = QComboBox()
        self.holdout_widget.addItem("Select Render Pass...")
        self.holdout_widget.setEnabled(False)
        self.main_layout.addWidget(self.holdout_widget)

    def make_reload(self):
        reload = QPushButton("Reload")
        reload.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        reload.clicked.connect(self.handle_reload)
        self.main_layout.addWidget(reload)

    def handle_reload(self):
        self.node.removeKnob(self.node.knob("loadUI"))
        load = nuke.PyCustom_Knob(
            "loadUI",
            "Load Render",
            "RenderLoadUI(nuke.thisNode()) if 'RenderLoadUI' in globals() else type('Dummy', (), {'makeUI': classmethod(lambda self: None)})",
        )
        self.node.addKnob(load)

    def update_holdouts(self, index):
        self.holdout_widget.clear()
        self.holdout_widget.addItem("Select Render Pass...")
        self.node.knob("version").setValue(index)
        if index <= 0:
            self.node.knob("holdout").setValue(0)
            self.holdout_widget.setEnabled(False)
            return
        version_data = self.version_widget.itemData(index)
        if version_data:
            for holdout in version_data:
                r_pass = str(Path(holdout).parts[-1])
                text = r_pass if r_pass == "Deep" else f"Holdout {int(r_pass)}"
                self.holdout_widget.addItem(text, holdout)
        self.holdout_widget.setEnabled(True)

    def load(self, index):
        self.node.knob("postage_stamp").setValue(False)
        self.node.knob("holdout").setValue(index)
        r_pass = (
            r_pass
            if (r_pass := self.holdout_widget.itemText(index))
            != "Select Render Pass..."
            else ""
        )
        path = (
            f"{value.replace('$HOP', '[getenv HOP]')}/####.exr".replace("\\", "/")
            if (value := self.holdout_widget.itemData(index))
            else ""
        )
        self.node.knob("label").setValue(r_pass)
        with self.node.begin():
            out = nuke.toNode("Output1")
            if r_pass == "Deep":
                read = nuke.toNode("DeepRead1")
                self.node.knob("tile_color").setValue(19201)
                postage = False
            else:
                read = nuke.toNode("Read1")
                read.knob("raw").setValue(True)
                self.node.knob("tile_color").setValue(4294967041)
                postage = True
            read.knob("file").setValue(path)
            read.knob("first").setValue(int(nuke.Root().knob("first_frame").value()))
            read.knob("last").setValue(int(nuke.Root().knob("last_frame").value()))
            out.setInput(0, read)
        self.node.knob("postage_stamp").setValue(postage)

    def makeUI(self):
        return self
