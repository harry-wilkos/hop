import sys

import hou
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2.QtGui import QColor
from PySide2.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
)

from hop.hou.util import load_style
from hop.util import get_collection
from functools import partial


class ShotMergeUI(QtWidgets.QWidget):
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
        if self.style_sheet:
            self.setStyleSheet(self.style_sheet)

    def make_ui(self):
        self.main_vertical.setContentsMargins(*[self.margins for _ in range(4)])
        self.make_asset_selection()
        self.main_vertical.addSpacing(self.margins)
        self.make_proxy_selection()
        self.main_vertical.addSpacing(self.margins)
        self.make_view_selection()
        self.main_vertical.addSpacing(self.margins)
        self.make_shot_selection()
        self.main_vertical.addSpacing(self.margins)
        self.make_publish()
        self.main_vertical.addWidget(hou.qt.Separator())

    def make_asset_selection(self):
        asset_horizontal = QHBoxLayout()
        asset_name, branch = hou.qt.ComboBox(), hou.qt.ComboBox()

        asset_name.addItem("Select Asset...", "")
        for asset in self.collection.find({}).sort("name", 1):
            name = asset["name"]
            asset_name.addItem(name.capitalize(), name)
        asset_name.currentIndexChanged.connect(
            lambda index: (
                self.push_to_parm("name", asset_name.itemData(index)),
            )
        )

        options = [("Main", "main"), ("Anim", "anim"), ("FX", "fx")]
        for option in options:
            branch.addItem(*option)
        branch.currentIndexChanged.connect(
            lambda index: self.push_to_parm("branch", branch.itemData(index))
        )

        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self.reload)

        self.parm_map["branch"] = branch
        self.parm_map["name"] = asset_name

        self.set_size(asset_name, branch)
        reload_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        asset_horizontal.addWidget(asset_name)
        asset_horizontal.addWidget(branch)
        asset_horizontal.addStretch()
        asset_horizontal.addWidget(reload_button)
        self.main_vertical.addLayout(asset_horizontal)

    def make_proxy_selection(self):
        main_proxy_vertical = QVBoxLayout()

        label = QLabel("Proxy Generation")
        self.set_size(label)
        main_proxy_vertical.addWidget(label)
        slider_horizontal = QHBoxLayout()

        proxy_type = hou.qt.ComboBox()
        options = [("None", 0), ("Bounding Box", 1), ("Convex Hull", 2)]
        for option in options:
            proxy_type.addItem(*option)
        slider_horizontal.addWidget(proxy_type)
        proxy_type.currentIndexChanged.connect(
            lambda index: self.push_to_parm("proxy_type", proxy_type.itemData(index))
        )
        self.parm_map["proxy_type"] = proxy_type
        slider_horizontal.addSpacing(self.margins)

        proxy_quality = QDoubleSpinBox()
        proxy_quality.setRange(0, 1)
        slider_horizontal.addWidget(proxy_quality)

        proxy_slider = QSlider(Qt.Horizontal)
        proxy_slider.setParent(self)
        proxy_slider.setRange(0, 100)
        slider_horizontal.addWidget(proxy_slider)

        widgets_to_sync = [proxy_quality, proxy_slider]
        proxy_quality.valueChanged.connect(
            lambda value: (
                self.push_to_parm("proxy_quality", value),
                self.sync_pairs(proxy_quality, value, widgets_to_sync),
            )
        )
        proxy_slider.valueChanged.connect(
            lambda value: (
                self.push_to_parm("proxy_quality", value / 100),
                self.sync_pairs(proxy_slider, value, widgets_to_sync),
            )
        )
        self.parm_map["proxy_quality"] = (proxy_quality, proxy_slider)

        slider_horizontal.addSpacing(self.margins)
        self.proxy_color_widget = hou.qt.ColorSwatchButton(include_alpha=True)
        slider_horizontal.addWidget(self.proxy_color_widget)
        self.proxy_color_widget.colorChanged.connect(
            lambda color: self.set_node_proxy_color(self.qcolor_to_list(color))
        )
        self.parm_map["proxy_color"] = self.proxy_color_widget

        main_proxy_vertical.addLayout(slider_horizontal)
        self.main_vertical.addLayout(main_proxy_vertical)

    def make_view_selection(self):
        main_view_vertical = QVBoxLayout()
        label = QLabel("View Mode")
        self.set_size(label)
        main_view_vertical.addWidget(label)

        button_horizontal = QHBoxLayout()
        exclusive_buttons = QButtonGroup()
        exclusive_buttons.setExclusive(True)
        for value, option in enumerate(("Default", "Error Map", "Error Geometry")):
            button = QPushButton(option)
            button.setCheckable(True)
            button.value = value
            exclusive_buttons.addButton(button)
            button_horizontal.addWidget(button)

        exclusive_buttons.buttonPressed.connect(
            lambda button: self.push_to_parm("debug", button.value),
        )
        self.parm_map["debug"] = exclusive_buttons

        main_view_vertical.addLayout(button_horizontal)
        self.main_vertical.addLayout(main_view_vertical)

    def make_shot_selection(self):
        main_shot_layout = QVBoxLayout()
        h_layout = QHBoxLayout()
        current_row_width = 0
        layouts = [h_layout]

        label = QLabel("Shots")
        main_shot_layout.addWidget(label)

        shots = get_collection("shots", "active_shots").find({}).sort("shot_number", 1)
        for shot in shots:
            check = QCheckBox(f"Shot {shot['shot_number']}")
            check.setToolTip(shot["description"])
            check_min_width = check.minimumSizeHint().width()
            check_spacing = h_layout.spacing()
            total_width_with_button = (
                current_row_width + check_min_width + check_spacing
            )
            if total_width_with_button > self.width() * 0.75:
                h_layout = QHBoxLayout()
                layouts.append(h_layout)
                current_row_width = 0

            h_layout.addWidget(check)
            current_row_width += check_min_width + check_spacing
            [main_shot_layout.addLayout(layout) for layout in layouts]
        self.main_vertical.addLayout(main_shot_layout)

    def make_publish(self):
        main_publish_vertical = QVBoxLayout()
        buttons_layout = QHBoxLayout()
        publish_options = QHBoxLayout()

        label = QLabel("Publish Asset")
        main_publish_vertical.addWidget(label)
        for pub in zip(
            ("Model", "Materials", "Animation"),
            ("publish_model", "publish_mats", "publish_anim"),
        ):
            button = QPushButton(pub[0])
            button.clicked.connect(
                partial(
                    lambda parm_name: self.node.parm(parm_name).pressButton()
                    if self.node
                    else None,
                    pub[1],
                )
            )
            buttons_layout.addWidget(button)

        farm = QCheckBox("Cache On Farm")
        self.parm_map["farm_cache"] = farm
        farm.clicked.connect(lambda value: self.push_to_parm("farm_cache", bool(value)))
        flush = QCheckBox("Flush Frames")
        self.parm_map["flush_frames"] = flush
        flush.stateChanged.connect(
            lambda value: self.push_to_parm("flush_frames", bool(value))
        )
        publish_all = QPushButton("All")
        publish_all.clicked.connect(
            lambda: self.node.parm("publish_all").pressButton() if self.node else None
        )

        publish_options.addWidget(publish_all)
        publish_options.addWidget(farm)
        publish_options.addWidget(flush)
        publish_options.addStretch()

        main_publish_vertical.addLayout(buttons_layout)
        main_publish_vertical.addLayout(publish_options)
        self.main_vertical.addLayout(main_publish_vertical)

    def update_widgets(self, parm, value):
        match parm:
            case "name":
                pass
            case "branch":
                pass
            case "proxy_type":
                pass

    def set_node_proxy_color(self, color_values):
        if self.node:
            if self.node.parm("proxy_color"):
                self.node.parm("proxy_color").set(color_values)
            else:
                for channel, value in zip(("r", "g", "b", "a"), color_values):
                    parm = self.node.parm("proxy_color" + channel)
                    if parm:
                        parm.set(value)

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
        for parm_name, widget in self.parm_map.items():
            if parm_name == "proxy_color":
                if node.parm("proxy_color"):
                    color_values = node.parm("proxy_color").rawValue()
                else:
                    color_values = []
                    for channel in ("r", "g", "b", "a"):
                        parm = node.parm("proxy_color" + channel)
                        if parm:
                            color_values.append(parm.eval())
                        else:
                            color_values.append(1 if channel == "a" else 0)
                qcolor = QColor.fromRgbF(*map(float, color_values))
                widget.blockSignals(True)
                widget.setColor(qcolor)
                widget.blockSignals(False)
            else:
                if node.parm(parm_name):
                    value = node.parm(parm_name).rawValue()
                    if hasattr(widget, "__iter__"):
                        for w in widget:
                            self.sync_widgets(w, value)
                    else:
                        self.sync_widgets(widget, value)

                    self.update_widgets(parm_name, value)


    def push_to_parm(self, parm, value):
        if self.node:
            if self.node.parm(str(parm)):
                self.node.parm(str(parm)).set(value)
                self.update_widgets(str(parm), value)

    @staticmethod
    def sync_pairs(source, value, widgets):
        value = value * 100 if value <= 1 else value / 100
        for widget in widgets:
            if widget is source:
                continue
            if widget.value() != value:
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)

    @staticmethod
    def sync_widgets(widget, value, block=True):
        widget.blockSignals(True) if block else None
        if isinstance(widget, QComboBox):
            index = widget.findData(value)
            widget.setCurrentIndex(index if index >= 0 else 0)
        elif isinstance(widget, QSlider):
            widget.setValue(int(float(value) * 100))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))
        elif isinstance(widget, QButtonGroup):
            widget.buttons()[int(value)].click()
        elif isinstance(widget, QCheckBox):
            widget.setChecked(True if value == "on" else False)
        else:
            try:
                widget.setValue(value)
            except Exception:
                pass
        widget.blockSignals(False) if block else None

    @staticmethod
    def set_size(*widgets):
        for widget in widgets:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    @staticmethod
    def qcolor_to_list(color: QColor):
        return [color.redF(), color.greenF(), color.blueF(), color.alphaF()]

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
