import sys
from typing import Optional

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..util import pop_dict


class drag_item(QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.origin: Optional[drag_list] = None


class drag_list(QListWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.stuck = set()
        self.source = set()

    def startDrag(self, *args, **kwargs):
        item = self.currentItem().text()
        if item in self.stuck:
            return
        super().startDrag(*args, **kwargs)

    def dropEvent(self, event):
        item = event.source().currentItem()
        if item.text() not in self.source:
            parent = item.origin
            parent.addItem(item)
            event.accept()
            return
        new_item = drag_item(item.text())
        new_item.origin = item.origin
        self.addItem(new_item)
        event.accept()


class ShotMerge_UI(QDialog):
    def __init__(self, modules, shots):
        super().__init__()
        self.modules = modules
        self.shots = shots
        self.results = {key: [None] * len(shots) for key in modules}
        self.setWindowTitle("Absorb Shots")
        self.setup_ui()

    def setup_ui(self):
        self.main_vertical = QVBoxLayout(self)
        assets, exclusive_modules = pop_dict(self.modules, "assets")
        self.exclusive_options(exclusive_modules)
        self.multi_options(assets)

        # Add Finish Options
        self.main_vertical.addStretch()
        finish_layout = QHBoxLayout()
        confirm = QPushButton("Confirm")
        confirm.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        finish_layout.addWidget(confirm, alignment=Qt.AlignCenter)
        finish_layout.addWidget(cancel, alignment=Qt.AlignCenter)
        self.main_vertical.addLayout(finish_layout)

    def multi_options(self, options):
        for key, items in options.items():
            container = QWidget()
            layout = QVBoxLayout(container)
            container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            module_label = QLabel(key.title())
            module_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(module_label)

            list_layout = QHBoxLayout()

            selected_layout = QVBoxLayout()
            list_layout.addLayout(selected_layout)
            label = QLabel(self.shots[0])
            label.setAlignment(Qt.AlignCenter)
            selected_layout.addWidget(label)
            selected = drag_list()
            selected_layout.addWidget(selected)

            current_selection = items.pop(0)
            if current_selection is not None:
                for item in current_selection:
                    asset = drag_item(item)
                    selected.addItem(asset)
                    selected.stuck.add(asset.text())

            tabs = QTabWidget()
            list_layout.addWidget(tabs)
            for shot, collection in enumerate(items):
                if collection is not None:
                    stored_assets = drag_list()
                    stored_assets.setDefaultDropAction(Qt.MoveAction)
                    tabs.addTab(stored_assets, f"Shot {self.shots[shot + 1]}")
                    for item in collection:
                        asset = drag_item(item)
                        asset.origin = stored_assets
                        stored_assets.addItem(asset)
                        stored_assets.source.add(asset.text())
                        selected.source.add(asset.text())

            layout.addLayout(list_layout)
            self.main_vertical.addWidget(container)

    def exclusive_options(self, options):
        for key, items in options.items():
            container = QWidget()
            layout = QVBoxLayout(container)
            container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            module_label = QLabel(key.title())
            module_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(module_label)

            exclusive_buttons = QButtonGroup(self)
            exclusive_buttons.setExclusive(True)
            exclusive_buttons.buttonPressed.connect(self.handle_pressed)
            exclusive_buttons.buttonClicked.connect(self.handle_clicked)

            shots_layout = QHBoxLayout()
            for count, item in enumerate(items):
                options_layout = QVBoxLayout()
                if item is not None:
                    shot = self.shots[count]
                    button = QPushButton(
                        f"Shot {shot}" if isinstance(shot, int) else str(shot)
                    )
                    button.setCheckable(True)
                    exclusive_buttons.addButton(button)

                    button.toggled.connect(
                        lambda checked,
                        m=key,
                        s=items[count],
                        idx=count: self.record_selection(m, s, idx, checked)
                    )
                    options_layout.addWidget(button)
                shots_layout.addLayout(options_layout)
            layout.addLayout(shots_layout)
            self.main_vertical.addWidget(container)

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
            "assets": [["already existing"], ["tree", "ed"], ["bear", "teddy"]],
        },
        ["New Shot", 1, 2],
    )
    print(selections)
