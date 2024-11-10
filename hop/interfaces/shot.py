import sys
from typing import Optional
import uuid
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


class Drag_Item(QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.origin: Optional[Drag_List] = None
        self.key: Optional[str] = None
        self.selection: Optional[str] = None
        self.index: Optional[int] = None
        self.id = uuid.uuid4()
        self.source = set()

    def __hash__(self):
        return hash(self.id)


class Drag_List(QListWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDefaultDropAction(Qt.IgnoreAction)
        self.stuck = set()
        self.source = set()
        self.selection = False

    def startDrag(self, *args, **kwargs):
        # Lock existing assets
        item = self.currentItem()
        if item in self.stuck:
            return
        super().startDrag(*args, **kwargs)

    def dropEvent(self, event):
        source_list = event.source()
        item = source_list.currentItem()
        new_item = Drag_Item(item.text())
        new_item.origin = item.origin
        new_item.key = item.key
        new_item.selection = item.selection
        new_item.index = item.index
        new_item.id = item.id
        new_item.source = item.source
        if self not in item.source:
            # Add item to correct list
            item.origin.addItem(new_item)
            source_list.takeItem(source_list.row(item))
            self.window().record_selection(
                item.key, item.selection, item.index, self.selection
            )
            event.accept()
            return

        # Add item to current list if valid
        self.addItem(new_item)
        source_list.takeItem(source_list.row(item))
        print(item.key, item.selection, item.index, self.selection)
        self.window().record_selection(
            item.key, item.selection, item.index, self.selection
        )

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

        # Finish Options
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
            selected = Drag_List()
            selected.selection = True
            selected_layout.addWidget(selected)

            # Add existing assets to selection and lock
            current_selection = items.pop(0)
            if current_selection is not None:
                for item in current_selection:
                    asset = Drag_Item(item)
                    selected.addItem(asset)
                    selected.stuck.add(asset)
                    self.record_selection(key, item, 0, True)

            # Create tabs for available items
            if len(items) == 1 and items[0] is not None:
                label_list_layout = QVBoxLayout()
                list_layout.addLayout(label_list_layout)
                shot_label = QLabel(f"Shot {self.shots[1]}")
                shot_label.setAlignment(Qt.AlignCenter)
                label_list_layout.addWidget(shot_label)

                stored_assets = Drag_List()
                label_list_layout.addWidget(stored_assets)
                stored_assets.setDefaultDropAction(Qt.IgnoreAction)
                stored_assets.setWordWrap(True)
                stored_assets.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                stored_assets.setUniformItemSizes(True)

                for item in items[0]:
                    asset = Drag_Item(item)
                    asset.key = key
                    asset.selection = item
                    asset.index = 1
                    asset.origin = stored_assets
                    stored_assets.addItem(asset)
                    # stored_assets.source.add(asset)
                    asset.source.add(stored_assets)
                    asset.source.add(selected)                    
                    # selected.source.add(asset)

            else:
                tabs = QTabWidget()
                list_layout.addWidget(tabs)
                for shot, collection in enumerate(items):
                    if collection is not None:
                        stored_assets = Drag_List()
                        stored_assets.setDefaultDropAction(Qt.IgnoreAction)
                        stored_assets.setWordWrap(True)
                        stored_assets.setHorizontalScrollBarPolicy(
                            Qt.ScrollBarAlwaysOff
                        )
                        stored_assets.setUniformItemSizes(True)
                        tabs.addTab(stored_assets, f"Shot {self.shots[shot + 1]}")

                        for item in collection:
                            asset = Drag_Item(item)
                            asset.key = key
                            asset.selection = item
                            asset.index = shot + 1
                            asset.origin = stored_assets
                            stored_assets.addItem(asset)
                            asset.source.add(stored_assets)
                            asset.source.add(selected)                            
                            # stored_assets.source.add(asset)
                            # selected.source.add(asset)

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
                    shots_layout.addWidget(button)
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
            "assets": [["harry"], ["robbie", "harry"], ["robbie", "harry"]],
        },
        ["New Shot", 1, 2],
    )
    print(selections)
