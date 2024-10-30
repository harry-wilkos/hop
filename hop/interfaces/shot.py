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
        self.ui()

    def ui(self):
        main_vertical = QVBoxLayout(self)
        self.module_layouts = {}
        for key, items in self.modules.items():
            # Create a new widget as a container
            container = QWidget()
            layout = QVBoxLayout(container)
            container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            exclusive_buttons = QButtonGroup(self)
            exclusive_buttons.setExclusive(True)

            # Make label for module
            module_label = QLabel(key.title())
            module_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(module_label)

            # Make horizontal layout for shots
            shots_layout = QHBoxLayout()
            for count, item in enumerate(items):
                options_layout = QVBoxLayout()
                if item is not None:
                    # Make Shot Labels
                    shot = self.shots[count]
                    if isinstance(shot, int):
                        shot = f"Shot {shot}"
                    shot_label = QLabel(str(shot))
                    shot_label.setAlignment(Qt.AlignCenter)
                    options_layout.addWidget(shot_label)

                    # Make Buttons:
                    if isinstance(item, str):
                        item = [item]
                    for i in item:
                        button = QPushButton(str(i))
                        button.setCheckable(True)
                        options_layout.addWidget(button)

                        if key in ["cam", "plate"]:
                            exclusive_buttons.addButton(button)

                shots_layout.addLayout(options_layout)

            # Add shots_layout to the container's layout
            layout.addLayout(shots_layout)

            # Store the container in the dictionary and add it to the main layout
            self.module_layouts[key] = container
            main_vertical.addWidget(container)


def run(modules=None, shots=None):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    dialog = ShotMerge(modules, shots)
    dialog.exec_()  # Use exec_ to open dialog modally
    sys.exit(app.exec_())


if __name__ == "__main__":
    run(
        {
            "cam": ["camera1", "cam", "cam"],
            "plate": ["back_plate.hdr", "plate", "plate"],
            "lights": [None, "lights", "lights"],
            "assets": [None, ["tree", "ed"], ["tree", "ed"]],
        },
        ["New Shot", 1, 2],
    )

