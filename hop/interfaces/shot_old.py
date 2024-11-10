import sys

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ShotMerge_UI(QDialog):
    def __init__(self, modules, shots):
        super().__init__()
        self.modules = modules
        self.shots = shots
        self.results = {key: [None] * len(shots) for key in modules}
        self.setWindowTitle("Absorb Shots")
        self.setup_ui()

    def setup_ui(self):
        main_vertical = QVBoxLayout(self)

        for key, items in self.modules.items():
            container = QWidget()
            layout = QVBoxLayout(container)
            container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            exclusive_buttons = QButtonGroup(self)
            exclusive_buttons.setExclusive(True)
            exclusive_buttons.buttonPressed.connect(self.handle_pressed)
            exclusive_buttons.buttonClicked.connect(self.handle_clicked)

            module_label = QLabel(key.title())
            module_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(module_label)

            shots_layout = QHBoxLayout()
            for count, item in enumerate(items):
                options_layout = QVBoxLayout()
                if item is not None:
                    shot = self.shots[count]
                    shot_label = QLabel(
                        f"Shot {shot}" if isinstance(shot, int) else str(shot)
                    )
                    shot_label.setAlignment(Qt.AlignCenter)
                    options_layout.addWidget(shot_label)

                    for i in item if isinstance(item, list) else [item]:
                        button = QPushButton(str(i))
                        button.setCheckable(True)
                        options_layout.addWidget(button)
                        if key in ["cam", "plate"]:
                            exclusive_buttons.addButton(button)

                        # Connect button toggle signal to result recording
                        button.toggled.connect(
                            lambda checked,
                            m=key,
                            s=i,
                            idx=count: self.record_selection(m, s, idx, checked)
                        )
                shots_layout.addLayout(options_layout)

            layout.addLayout(shots_layout)
            main_vertical.addWidget(container)

        # Add Finish Options
        main_vertical.addStretch()
        finish_layout = QHBoxLayout()
        confirm = QPushButton("Confirm")
        confirm.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        finish_layout.addWidget(confirm, alignment=Qt.AlignCenter)
        finish_layout.addWidget(cancel, alignment=Qt.AlignCenter)
        main_vertical.addLayout(finish_layout)

    def record_selection(self, module, selection, index, checked):
        current_selection = self.results[module][index]

        if checked:
            if current_selection is None:
                self.results[module][index] = selection
            elif isinstance(current_selection, list):
                if selection not in current_selection:
                    current_selection.append(selection)
            else:
                self.results[module][index] = [current_selection, selection]
        else:
            if isinstance(current_selection, list):
                current_selection.remove(selection)
                if len(current_selection) == 1:
                    self.results[module][index] = current_selection[0]
            else:
                self.results[module][index] = None

    def handle_pressed(self, button):
        button.group().setExclusive(not button.isChecked())

    def handle_clicked(self, button):
        button.group().setExclusive(True)

    def get_result(self):
        return self.results if self.exec_() == QDialog.Accepted else None


def ShotMerge(modules=None, shots=None) -> None | dict:
    app = QApplication.instance()
    created_app = False
    if not app:
        app = QApplication(sys.argv)
        created_app = True
    dialogue = ShotMerge_UI(modules, shots).get_result()
    if created_app:
        del app
    return dialogue


if __name__ == "__main__":
    selections = ShotMerge(
        {
            "cam": ["camera1", "cam", "cam"],
            "plate": ["back_plate.hdr", "plate", "plate"],
            "lights": [None, "lights", "lights"],
            "assets": [None, ["tree", "ed"], ["tree", "ed"]],
        },
        ["New Shot", 1, 2],
    )
    print(selections)
