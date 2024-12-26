import nuke
import os
from hop.util import get_collection
from hop.nk.gizmos.shot import handle_change
from PySide2.QtCore import QSize
from PySide2.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class ShotLoadUI(QDialog):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.collection = get_collection("shots", "active_shots")
        handle_change(self.node)
        self.main_layout = QVBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        self.make_buttons()
        self.make_reload()

    def make_buttons(self):
        shots = self.collection.find({}).sort("shot_number", 1)

        exclusive_buttons = QButtonGroup(self)
        exclusive_buttons.buttonPressed.connect(self.handle_pressed)
        exclusive_buttons.buttonClicked.connect(self.handle_clicked)

        main_button_layout = QVBoxLayout()
        h_layout = QHBoxLayout()
        layouts = [h_layout]
        current_row_width = 0
        loaded_shot = (
            self.node["store_id"].value() if not self.node["off_pipe"].value() else None
        )
        loaded_button = None

        for shot in shots:
            button = QPushButton(f"Shot {shot['shot_number']}")
            button.setCheckable(True)
            exclusive_buttons.addButton(button)
            button.id = shot["_id"]
            if str(button.id) == loaded_shot:
                loaded_button = button

            button_min_width = button.minimumSizeHint().width()
            button_spacing = h_layout.spacing()
            total_width_with_button = (
                current_row_width + button_min_width + button_spacing
            )
            if total_width_with_button > self.width():
                h_layout = QHBoxLayout()
                layouts.append(h_layout)
                current_row_width = 0

            h_layout.addWidget(button)
            current_row_width += button_min_width + button_spacing

        for layout in layouts:
            main_button_layout.addLayout(layout)
        self.main_layout.addLayout(main_button_layout)
        if loaded_button is not None:
            loaded_button.click()

    def make_reload(self):
        reload_layout = QHBoxLayout()

        reload = QPushButton("Reload")
        reload.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        reload.clicked.connect(self.handle_reload)
        reload_layout.addWidget(reload)

        auto_alpha = QCheckBox("Auto Alpha")
        reload_layout.addWidget(auto_alpha)
        if self.node.knob("auto_alpha").value():
            auto_alpha.setChecked(True)
        auto_alpha.stateChanged.connect(self.handle_auto_alpha)

        self.main_layout.addLayout(reload_layout)

    def handle_auto_alpha(self, state):
        store = self.node.knob("auto_alpha")
        if state:
            store.setValue(True)
        else:
            store.setValue(False)

    def handle_reload(self):
        self.node.removeKnob(self.node.knob("loadUI"))
        handle_change(self.node)
        load = nuke.PyCustom_Knob(
            "loadUI",
            "Load Shot",
            "ShotLoadUI(nuke.thisNode()) if 'ShotLoadUI' in globals() else type('Dummy', (), {'makeUI': classmethod(lambda self: None)})",
        )
        self.node.addKnob(load)

    def handle_pressed(self, button):
        if not button.isChecked():
            self.node.knob("store_id").setValue(str(button.id))
            shot_data = self.collection.find_one({"_id": button.id})

            if shot_data:
                self.node.knob("label").setValue(str(shot_data["shot_number"]))
                self.node.knob("start").setValue(shot_data["start_frame"])
                self.node.knob("end").setValue(shot_data["end_frame"])
                self.node.knob("cam").setValue(
                    shot_data["cam"].replace("$HOP", os.environ["HOP"])
                )

                with self.node.begin():
                    read = nuke.toNode("Read1")

                    first = 1001
                    last = 1001 + shot_data["end_frame"] - shot_data["start_frame"]

                    read.knob("offset").setValue(shot_data["start_frame"] - first - shot_data["padding"])
                    read.knob("frame").setValue("frame - offset")

                    read.knob("first").setValue(first)
                    read.knob("last").setValue(last)
                    read.knob("origfirst").setValue(first)
                    read.knob("origlast").setValue(last)

                    read.knob("file").setValue(
                        shot_data["plate"].replace("$HOP", os.environ["HOP"])
                    )

                    st_map = nuke.toNode("Read2")
                    st_map.knob("file").setValue(
                        shot_data["st_map"].replace("$HOP", "[getenv HOP]")
                    )

                    nuke.Root().knob("first_frame").setValue(shot_data["start_frame"] - shot_data["padding"])
                    nuke.Root().knob("last_frame").setValue(shot_data["end_frame"] + shot_data["padding"])
                dependents = self.node.dependent()
                for out in dependents:
                    reload = out.knob("reload")
                    if reload:
                        reload.execute()


        else:
            self.node.knob("store_id").setValue(None)
            self.node.knob("label").setValue(None)
            self.node.knob("cam").setValue(None)

            with self.node.begin():
                read = nuke.toNode("Read1")
                read.knob("file").setValue("")
                st_map = nuke.toNode("Read2")
                st_map.knob("file").setValue("")

        button.group().setExclusive(not button.isChecked())

    def handle_clicked(self, button):
        button.group().setExclusive(True)

    def makeUI(self):
        return self
