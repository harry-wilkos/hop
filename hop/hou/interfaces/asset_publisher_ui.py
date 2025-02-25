import sys
from PySide2.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QComboBox,
    QSizePolicy,
    QSlider,
    QDoubleSpinBox,
)
from PySide2.QtCore import Qt
from hop.util import get_collection
from hop.hou.util import load_style
import hou

class ShotMergeUI(QDialog):
    collection = get_collection("assets", "active_assets")
    style_sheet = None
    margins = 20
    try:
        style_sheet = load_style()
    except AttributeError:
        pass

    def __init__(self):
        super().__init__()
        self.main_vertical = QVBoxLayout(self)
        self.node = None
        self.parm_map = {}
        self.make_ui()
        self.setStyleSheet(self.style_sheet) if self.style_sheet else None

    def make_ui(self):
        self.main_vertical.setContentsMargins(*[self.margins for _ in range(4)])
        self.main_vertical.addWidget(hou.qt.ComboBox())
        self.make_asset_selection()
        self.make_proxy_selection()

    def make_asset_selection(self):
        asset_horizontal = QHBoxLayout()
        asset_name, branch = QComboBox(), QComboBox()

        asset_name.addItem("Select Asset...", "")
        for asset in self.collection.find({}).sort("name", 1):
            name = asset["name"]
            asset_name.addItem(name.capitalize(), name)
        asset_name.currentIndexChanged.connect(
            lambda index: self.push_to_parm("name", asset_name.itemData(index))
        )

        options = [("Main", "main"), ("Anim", "anim"), ("FX", "fx")]
        [branch.addItem(*option) for option in options]
        branch.currentIndexChanged.connect(
            lambda index: self.push_to_parm("branch", branch.itemData(index))
        )

        reload = QPushButton("Reload")
        reload.clicked.connect(self.reload)

        self.parm_map["branch"] = branch
        self.parm_map["name"] = asset_name

        self.set_size(asset_name, branch)
        reload.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        asset_horizontal.addWidget(asset_name)
        asset_horizontal.addWidget(branch)
        asset_horizontal.addStretch()
        asset_horizontal.addWidget(reload)
        self.main_vertical.addLayout(asset_horizontal)

    def make_proxy_selection(self):
        main_proxy_vertical = QVBoxLayout()
        proxy_horizontal = QHBoxLayout()
        options_vertical = QVBoxLayout()

        label = QLabel("Proxy Generation")
        self.set_size(label)
        main_proxy_vertical.addWidget(label)

        proxy_type = QComboBox()
        options = [("None", 0), ("Bounding Box", 1), ("Convex Hull", 2)]
        [proxy_type.addItem(*option) for option in options]
        options_vertical.addWidget(proxy_type)
        proxy_type.currentIndexChanged.connect(
            lambda index: self.push_to_parm("proxy_type", proxy_type.itemData(index))
        )
        self.parm_map["proxy_type"] = proxy_type

        slider_horizontal = QHBoxLayout()
        proxy_quality = QDoubleSpinBox()
        proxy_quality.setRange(0, 1)
        slider_horizontal.addWidget(proxy_quality)
        proxy_slider = QSlider(Qt.Horizontal)
        proxy_slider.setRange(0, 100)
        slider_horizontal.addWidget(proxy_slider)

        widgets_to_sync = [proxy_quality, proxy_slider]
        proxy_quality.valueChanged.connect(
            lambda value: (
                self.push_to_parm("proxy_quality", value),
                self.syn_pairs(proxy_quality, value, widgets_to_sync),
            )
        )
        proxy_slider.valueChanged.connect(
            lambda value: (
                self.push_to_parm("proxy_quality", value / 100),
                self.syn_pairs(proxy_slider, value, widgets_to_sync),
            )
        )
        options_vertical.addLayout(slider_horizontal)
        self.parm_map["proxy_quality"] = (proxy_quality, proxy_slider)

        proxy_horizontal.addLayout(options_vertical)
        main_proxy_vertical.addLayout(proxy_horizontal)
        self.main_vertical.addLayout(main_proxy_vertical)

    def reload(self):
        self.clear_layout(self.main_vertical)
        self.make_ui()
        self.load(self.node)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self.clear_layout(child.layout())

    def load(self, node):
        self.node = node
        for parm_name in self.parm_map:
            if parm := node.parm(parm_name):
                widgets = (
                    widget
                    if hasattr((widget := self.parm_map[parm_name]), "__iter__")
                    else [widget]
                )
                [self.sync_widgets(widget, parm.rawValue()) for widget in widgets]

    def push_to_parm(self, parm, value):
        if self.node:
            self.node.parm(parm).set(value)

    @staticmethod
    def syn_pairs(source, value, widgets):
        value = value * 100 if value <= 1 else value / 100
        for widget in widgets:
            if widget is source:
                continue
            if widget.value() != value:
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)
            pass

    @staticmethod
    def sync_widgets(widget, value):
        print(type(widget))
        widget.blockSignals(True)
        if isinstance(widget, QComboBox):
            index = widget.findData(value)
            widget.setCurrentIndex(index if index >= 0 else 0)
        elif isinstance(widget, QSlider):
            widget.setValue(int(float(value) * 100))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))
        else:
            widget.setValue(value)

        widget.blockSignals(False)

    @staticmethod
    def set_size(*widgets):
        [
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            for widget in widgets
        ]

    def run(self):
        return self.results if self.exec_() == QDialog.Accepted else None


def asset_publisher() -> ShotMergeUI | None:
    app = QApplication.instance()
    created_app = False
    if not app:
        app = QApplication(sys.argv)
        created_app = True
    dialogue = ShotMergeUI().run()
    if created_app:
        del app
    return dialogue


if __name__ == "__main__":
    asset_publisher()
