import sys

try:
    from PySide2.QtCore import Qt
    from PySide2.QtWidgets import (
        QApplication,
        QButtonGroup,
        QDialog,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QVBoxLayout,
    )
except ModuleNotFoundError:
    from hop.my.util import find_pyside
    PySide = find_pyside()
    from PySide.QtCore import Qt
    from PySide.QtWidgets import (
        QApplication,
        QButtonGroup,
        QDialog,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QVBoxLayout,
    )



class CustomDialogueUI(QDialog):
    def __init__(self, title, description, options, default, tool_tips):
        super().__init__()

        self.description = description
        self.options = options
        self.tool_tips = tool_tips
        self.choice = None
        self.default = default

        self.main_layout = QVBoxLayout(self)
        self.setWindowTitle(title)
        self.make_ui()
        self.create_finish_layout()

        self.adjustSize()
        self.setFixedSize(self.size())
        self.setWindowFlags(self.windowFlags() | Qt.MSWindowsFixedSizeDialogHint)

    def make_ui(self):
        label = QLabel(self.description)
        label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(label)

        button_layout = QHBoxLayout()
        exclusive_buttons = QButtonGroup(self)
        exclusive_buttons.setExclusive(True)

        max_width = 0
        buttons = []

        for count, option in enumerate(self.options):
            button = QPushButton(str(option))
            button.setCheckable(True)
            button_layout.addWidget(button)
            exclusive_buttons.addButton(button)
            buttons.append(button)

            max_width = max(max_width, button.sizeHint().width())

            if self.tool_tips:
                button.setToolTip(str(self.tool_tips[count]))

            button.toggled.connect(
                lambda checked, index=count: self.record_selection(index)
                if checked
                else None
            )

            if count == self.default:
                button.click()

        # Ensure all buttons have uniform width
        for button in buttons:
            button.setFixedWidth(max_width + 10)

        self.main_layout.addLayout(button_layout)

    def create_finish_layout(self):
        confirm = QPushButton("Confirm")
        confirm.clicked.connect(self.accept)
        confirm.setFixedSize(confirm.minimumSizeHint())

        confirm_layout = QHBoxLayout()
        confirm_layout.addWidget(confirm)
        confirm_layout.setAlignment(Qt.AlignCenter)

        self.main_layout.addLayout(confirm_layout)

    def record_selection(self, index):
        self.choice = index

    def get_result(self):
        return self.choice if self.exec_() == QDialog.Accepted else None

    def reject(self):
        pass


def custom_dialogue(
    title: str,
    description: str,
    options: list,
    default: int | None = None,
    tool_tips: list | None = None,
) -> int | None:
    if tool_tips and len(options) != len(tool_tips):
        raise IndexError("Length of tool tips doesn't match options")

    app = QApplication.instance()
    created_app = False

    if not app:
        app = QApplication(sys.argv)
        created_app = True

    dialogue = CustomDialogueUI(
        title, description, options, default, tool_tips
    ).get_result()

    if created_app:
        del app

    return dialogue


if __name__ == "__main__":
    result = custom_dialogue(
        "Title check",
        "Pick an option",
        [1, "Other option", "Wow, I'm so good at code"],
        0,
    )
    print(result)

