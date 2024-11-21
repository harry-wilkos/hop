import sys
import uuid
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
from .load_style import load_style

class DragItem(QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.origin: Optional[DragList] = None
        self.key: Optional[str] = None
        self.selection: Optional[str] = None
        self.index: Optional[int] = None
        self.source = set()
        self.id = uuid.uuid4()

    def __hash__(self):
        return hash(self.id)


class DragList(QListWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDefaultDropAction(Qt.IgnoreAction)
        self.stuck = set()
        self.selection = False

    def startDrag(self, *args, **kwargs):
        # Lock existing assets to selected
        if self.currentItem() not in self.stuck:
            super().startDrag(*args, **kwargs)

    def dropEvent(self, event):
        # Create New Item
        source_list = event.source()
        item = source_list.currentItem()
        new_item = self.copy_drag_item(item)

        if self not in item.source:
            # Move to correct list
            item.origin.addItem(new_item)
            source_list.takeItem(source_list.row(item))
            self.window().record_selection(
                item.key, item.selection, item.index, self.selection
            )
        else:
            # Copy into list
            self.addItem(new_item)
            source_list.takeItem(source_list.row(item))
            self.window().record_selection(
                item.key, item.selection, item.index, self.selection
            )

        event.accept()

    @staticmethod
    def copy_drag_item(item):
        new_item = DragItem(item.text())
        new_item.origin, new_item.key, new_item.selection = (
            item.origin,
            item.key,
            item.selection,
        )
        new_item.index, new_item.id, new_item.source = item.index, item.id, item.source
        return new_item


class ShotMergeUI(QDialog):
    def __init__(self, modules, shots):
        super().__init__()
        self.modules = modules
        self.shots = shots
        self.results = {key: [None] * len(shots) for key in modules}
        self.setWindowTitle("Absorb Shots")
        self.setup_ui()
        try:
            self.setStyleSheet(load_style())
        except AttributeError:
            pass

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)

        # Split based on type
        assets, exclusive_modules = pop_dict(self.modules, "assets")
        self.create_exclusive_options(exclusive_modules)
        self.create_multi_options(assets)

        # Add confirm options
        finish_layout = self.create_finish_layout()
        self.main_layout.addStretch()
        self.main_layout.addLayout(finish_layout)

    def create_multi_options(self, options):
        for key, items in options.items():
            if [value for value in items if value is not None]:
                # Init new module
                container, layout, list_layout = self.create_base_layout(key)

                # Create selected list on left
                selected = self.create_selected_list(list_layout, key, items[0])[0]

                # Create possible asseets on right
                self.create_asset_tabs_or_labels(items[1:], key, list_layout, selected)

                layout.addLayout(list_layout)
                self.main_layout.addWidget(container)

    def create_asset_tabs_or_labels(self, items, key, list_layout, selected):
        # Filter out None Values
        valid_collections = [item for item in items if item is not None]

        if len(valid_collections) == 1:
            # Don't Create tabs if only one shot
            list_layout.addLayout(
                self.create_labeled_layout(valid_collections[0], key, selected, 1)
            )
        else:
            tabs = QTabWidget()
            list_layout.addWidget(tabs)
            for shot, collection in enumerate(items):
                if collection is not None:
                    stored_assets = self.setup_stored_assets(
                        collection, key, selected, shot + 1
                    )
                    tabs.addTab(stored_assets, f"Shot {self.shots[shot + 1]}")

    def create_labeled_layout(self, items, key, selected, index):
        label_layout = QVBoxLayout()
        shot_label = QLabel(f"Shot {self.shots[index]}")
        shot_label.setAlignment(Qt.AlignCenter)
        label_layout.addWidget(shot_label)
        stored_assets = self.setup_stored_assets(items, key, selected, index)
        label_layout.addWidget(stored_assets)
        return label_layout

    def setup_stored_assets(self, items, key, selected, index):
        # Create list with assets
        stored_assets = DragList()
        self.configure_drag_list(stored_assets)
        for item in items:
            asset = DragItem(item)
            asset.key, asset.selection, asset.index, asset.origin = (
                key,
                item,
                index,
                stored_assets,
            )
            asset.source.update({stored_assets, selected})
            stored_assets.addItem(asset)
        return stored_assets

    @staticmethod
    def configure_drag_list(drag_list):
        drag_list.setDefaultDropAction(Qt.IgnoreAction)
        drag_list.setWordWrap(True)
        drag_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        drag_list.setUniformItemSizes(True)
        drag_list.setAlternatingRowColors(True)

    def create_exclusive_options(self, options):
        for key, items in options.items():
            if [value for value in items if value is not None]:
                container, layout, shots_layout = self.create_base_layout(
                    key, for_buttons=True
                )

                exclusive_buttons = QButtonGroup(self)
                exclusive_buttons.setExclusive(True)
                exclusive_buttons.buttonPressed.connect(self.handle_pressed)
                exclusive_buttons.buttonClicked.connect(self.handle_clicked)

                for count, item in enumerate(items):
                    if item is not None:
                        button = QPushButton(
                            f"Shot {self.shots[count]}"
                            if isinstance(self.shots[count], int)
                            else str(self.shots[count])
                        )
                        button.setCheckable(True)
                        exclusive_buttons.addButton(button)
                        button.toggled.connect(
                            lambda checked, m=key, s=item, idx=count: self.record_selection(
                                m, s, idx, checked
                            )
                        )
                        shots_layout.addWidget(button)

                layout.addLayout(shots_layout)
                self.main_layout.addWidget(container)

    def create_base_layout(self, key, for_buttons=False):
        container = QWidget()
        layout = QVBoxLayout(container)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        module_label = QLabel(key.title())
        module_label.setObjectName("bold")
        module_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(module_label)

        if for_buttons:
            return container, layout, QHBoxLayout()

        list_layout = QHBoxLayout()
        return container, layout, list_layout

    def create_selected_list(self, list_layout, key, current_selection):
        selected_layout = QVBoxLayout()
        list_layout.addLayout(selected_layout)

        label = QLabel(self.shots[0])
        label.setAlignment(Qt.AlignCenter)
        selected_layout.addWidget(label)

        selected = DragList()
        self.configure_drag_list(selected)
        selected.selection = True
        selected_layout.addWidget(selected)

        if current_selection is not None:
            for item in current_selection:
                asset = DragItem(item)
                selected.addItem(asset)
                selected.stuck.add(asset)
                self.record_selection(key, item, 0, True)

        return selected, selected_layout

    def create_finish_layout(self):
        finish_layout = QHBoxLayout()
        confirm = QPushButton("Confirm")
        confirm.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        finish_layout.addWidget(confirm, alignment=Qt.AlignCenter)
        finish_layout.addWidget(cancel, alignment=Qt.AlignCenter)
        return finish_layout

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


def merge_shots(modules=None, shots=None) -> Optional[dict]:
    app = QApplication.instance()
    created_app = False
    if not app:
        app = QApplication(sys.argv)
        created_app = True
    dialogue = ShotMergeUI(modules, shots).get_result()
    if created_app:
        del app
    return dialogue


if __name__ == "__main__":
    selections = merge_shots(
        {
            "cam": ["camera1", "cam", "cam"],
            "plate": ["back_plate.hdr", "plate", "plate"],
            "lights": [None, "lights", "lights"],
            "assets": [["harry"], ["robbie", "harry"], ["harry", "robbie"]],
        },
        ["New Shot", 1, 2],
    )
    print(selections)
