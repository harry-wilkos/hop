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


class ShotMerge(QDialog):
    def __init__(self, modules, shots):
        super().__init__()
        self.modules = modules
        self.shots = shots
        self.results = self.init_results()
        self.ui()

    def init_results(self):
        results = {}
        for key in self.modules:
            results[key] = []
            for _ in self.shots:
                results[key].append(None)
        return results

    def ui(self):
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

                    if isinstance(item, str):
                        item = [item]
                    for i in item:
                        button = QPushButton(str(i))
                        button.setCheckable(True)
                        options_layout.addWidget(button)

                        if key in ["cam", "plate"]:
                            exclusive_buttons.addButton(button)

                        button.toggled.connect(
                            lambda checked,
                            module=key,
                            selection=i,
                            idx=count: self.record_selection(
                                module, selection, idx, checked
                            )
                        )

                shots_layout.addLayout(options_layout)
            layout.addLayout(shots_layout)
            main_vertical.addWidget(container)

        main_vertical.addStretch()

        finish_layout = QHBoxLayout()
        self.confirm = QPushButton("Confirm")
        self.confirm.clicked.connect(self.accept)
        self.cancel = QPushButton("Cancel")
        self.cancel.clicked.connect(self.reject)
        finish_layout.addWidget(self.confirm, alignment=Qt.AlignCenter)
        finish_layout.addWidget(self.cancel, alignment=Qt.AlignCenter)
        main_vertical.addLayout(finish_layout)

    def record_selection(self, module, selection, count, checked):
        if checked:
            if self.results[module][count] is None:
                self.results[module][count] = selection
            elif isinstance(self.results[module][count], list):
                if selection not in self.results[module][count]:
                    self.results[module][count].append(selection)
            else:
                self.results[module][count] = [
                    self.results[module][count],
                    selection,
                ]
        else:
            if isinstance(self.results[module][count], list):
                self.results[module][count].remove(selection)
                if len(self.results[module][count]) == 1:
                    self.results[module][count] = self.results[
                        module
                    ][count][0]
            else:
                self.results[module][count] = None

    def handle_pressed(self, button):
        button.group().setExclusive(not button.isChecked())

    def handle_clicked(self, button):
        button.group().setExclusive(True)

    def get_result(self):
        result = self.exec_()
        if result == QDialog.Accepted:
            return self.results
        return None


def run(modules=None, shots=None) -> None | dict:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    dialogue = ShotMerge(modules, shots).get_result()
    del app
    return dialogue


if __name__ == "__main__":
    selections = run(
        {
            "cam": ["camera1", "cam", "cam"],
            "plate": ["back_plate.hdr", "plate", "plate"],
            "lights": [None, "lights", "lights"],
            "assets": [None, ["tree", "ed"], ["tree", "ed"]],
        },
        ["New Shot", 1, 2],
    )
    print(selections)
