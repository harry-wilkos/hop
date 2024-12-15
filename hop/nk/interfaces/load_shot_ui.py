import os
from hop.util import get_collection
from PySide2.QtCore import QSize
from PySide2.QtWidgets import (
    QButtonGroup,
    QDialog,
    QApplication,
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
        shots = self.collection.find({})

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

    def sizeHint(self):
        return QSize(self.size().width(), 100)

    def makeUI(self):
        return self

    def handle_pressed(self, button):
        if not button.isChecked():
            shot_data = self.collection.find_one({"_id": button.id})
            self.node.knob("store_id").setValue(str(button.id))
            if shot_data:
                plate = shot_data["plate"]
                self.node.knob("plate_path").setValue(
                        os.path.expandvars(plate)
                )
                self.node.knob("start_frame").setValue(shot_data["start_frame"])
                self.node.knob("end_frame").setValue(shot_data["end_frame"])
                
        else:
            self.node.knob("store_id").setValue("")
            self.node.knob("plate_path").setValue("")
            self.node.knob("start_frame").setValue(0)
            self.node.knob("end_frame").setValue(0)
        button.group().setExclusive(not button.isChecked())

    def handle_clicked(self, button):
        button.group().setExclusive(True)


# def load_shot():
#     app = QApplication.instance()
#     created_app = False
#     if not app:
#         app = QApplication(sys.argv)
#         created_app = True
#     dialogue = ShotLoadUI()
#     dialogue.exec_()
#     if created_app:
#         del app


# if __name__ == "__main__":
#     load_shot()
