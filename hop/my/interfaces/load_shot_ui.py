import sys
from hop.my.util import find_pyside
from hop.util import get_collection
import maya.cmds as cmds
PySide = find_pyside()
from PySide.QtCore import Qt
from PySide.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QApplication,
)


class ShotLoadUI(QDialog):
    def __init__(self):
        super().__init__()
        self.collection = get_collection("shots", "active_shots")
        self.main_layout = QVBoxLayout(self)
        self.results = None
        self.setWindowTitle("Select Shot")
        self.setup_ui()

    def setup_ui(self):
        self.make_buttons()
        self.create_finish_layout()

    def make_buttons(self):
        shot_data = None
        if cmds.attributeQuery("loadedShot", node="defaultRenderGlobals", exists=True):
            shot_data = cmds.getAttr("defaultRenderGlobals.loadedShot")

        shots = self.collection.find({}).sort("shot_number", 1)

        exclusive_buttons = QButtonGroup(self)
        exclusive_buttons.buttonPressed.connect(self.handle_pressed)
        exclusive_buttons.buttonClicked.connect(self.handle_clicked)

        main_button_layout = QVBoxLayout()
        h_layout = QHBoxLayout()
        layouts = [h_layout]
        current_row_width = 0

        for shot in shots:
            button = QPushButton(f"Shot {shot['shot_number']}")
            button.setCheckable(True)
            exclusive_buttons.addButton(button)
            button.setToolTip(shot["description"])

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
            button.toggled.connect(
                lambda checked, shot_data=shot: self.record_selection(
                    checked, shot_data
                )
            )
            if str(shot["_id"]) == shot_data:
                button.click()

        for layout in layouts:
            main_button_layout.addLayout(layout)

        self.main_layout.addLayout(main_button_layout)

    def create_finish_layout(self):
        finish_layout = QHBoxLayout()
        confirm = QPushButton("Confirm")
        confirm.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        finish_layout.addWidget(confirm, alignment=Qt.AlignCenter)
        finish_layout.addWidget(cancel, alignment=Qt.AlignCenter)
        self.main_layout.addLayout(finish_layout)
        return finish_layout

    def record_selection(self, checked, shot_data):
        if checked:
            self.results = shot_data
        else:
            self.results = None

    def handle_pressed(self, button):
        button.group().setExclusive(not button.isChecked())

    def handle_clicked(self, button):
        button.group().setExclusive(True)

    def get_result(self):
        return self.results if self.exec_() == QDialog.Accepted else None


def load_shot() -> None | dict:
    app = QApplication.instance()
    created_app = False
    if not app:
        app = QApplication(sys.argv)
        created_app = True
    dialogue = ShotLoadUI().get_result()
    if created_app:
        del app
    return dialogue


if __name__ == "__main__":
    load_shot()
