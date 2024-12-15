import nuke
from hop.util import get_collection
from PySide2.QtCore import QSize
from PySide2.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)


class ShotLoadUI(QDialog):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.collection = get_collection("shots", "active_shots")
        self.main_layout = QVBoxLayout(self)
        self.make_buttons()

    def make_buttons(self):
        shots = self.collection.find({}).sort("shot_number", 1)

        exclusive_buttons = QButtonGroup(self)
        exclusive_buttons.buttonPressed.connect(self.handle_pressed)
        exclusive_buttons.buttonClicked.connect(self.handle_clicked)

        main_button_layout = QVBoxLayout()
        h_layout = QHBoxLayout()
        layouts = [h_layout]
        current_row_width = 0
        loaded_shot = self.node["store_id"].value()
        loaded_button = None

        for shot in shots:
            button = QPushButton(f"Shot {shot['shot_number']}")
            button.id = shot["_id"]
            if str(button.id) == loaded_shot:
                loaded_button = button
            button.setCheckable(True)
            exclusive_buttons.addButton(button)

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

    def handle_pressed(self, button):
        if not button.isChecked():
            self.node.knob("store_id").setValue(str(button.id))
            shot_data = self.collection.find_one({"_id": button.id})
            if shot_data:
                self.node.knob("label").setValue(str(shot_data["shot_number"]))
                self.node.knob("start").setValue(shot_data["start_frame"])
                self.node.knob("end").setValue(shot_data["end_frame"])

                with self.node.begin():
                    read = nuke.toNode("Read1")

                    first = 1001
                    last = 1001 + shot_data["end_frame"] - shot_data["start_frame"]

                    read.knob("offset").setValue(shot_data["start_frame"] - first)
                    read.knob("frame").setValue("frame - offset")

                    read.knob("first").setValue(first)
                    read.knob("last").setValue(last)
                    read.knob("origfirst").setValue(first)
                    read.knob("origlast").setValue(last)

                    read.knob("file").setValue(
                        shot_data["plate"].replace("$HOP", "[getenv HOP]")
                    )

                    nuke.Root().knob("first_frame").setValue(shot_data["start_frame"])
                    nuke.Root().knob("last_frame").setValue(shot_data["end_frame"])

        else:
            self.node.knob("store_id").setValue(None)
            self.node.knob("label").setValue(None)

            with self.node.begin():
                read = nuke.toNode("Read1")
                read.knob("file").setValue("")

        button.group().setExclusive(not button.isChecked())

    def handle_clicked(self, button):
        button.group().setExclusive(True)

    def sizeHint(self):
        return QSize(self.size().width(), 100)

    def makeUI(self):
        return self