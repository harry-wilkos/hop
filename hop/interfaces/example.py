import sys
from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy
)
from PySide2.QtGui import QFont
class SelectionDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.selected_button_id = None  # Store selected button ID
        self.initUI()

    def initUI(self):
        # Main vertical layout
        self.vertical_layout = QVBoxLayout(self)

        # Container widget for the camera layout
        self.camera_w = QWidget()
        self.camera_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Stretch horizontally, fixed vertically
        self.camera_vl = QVBoxLayout(self.camera_w)

        # Camera label
        self.camera_label = QLabel("Camera")
        self.camera_label.setAlignment(Qt.AlignCenter)

        # Add widgets to layout
        self.button_1 = QPushButton("1")
        self.button_2 = QPushButton("2")

        # Make buttons checkable
        self.button_1.setCheckable(True)
        self.button_2.setCheckable(True)

        # Group the buttons so only one can be selected at a time
        self.button_group = QButtonGroup()
        self.button_group.addButton(self.button_1, id=1)  # Assign an ID for easy reference
        self.button_group.addButton(self.button_2, id=2)
        self.button_group.setExclusive(True)  # Ensures mutual exclusivity

        # Connect the button group's signal to store selected button ID
        self.button_group.buttonClicked.connect(self.on_button_clicked)

        # Add camera label and buttons to the layout
        self.camera_vl.addWidget(self.camera_label)

        # Horizontal layout for buttons
        self.camera_hl = QHBoxLayout()
        self.camera_hl.addWidget(self.button_1)
        self.camera_hl.addWidget(self.button_2)
        
        self.camera_vl.addLayout(self.camera_hl)
        
        # Add the camera widget to the main vertical layout without centering alignment
        self.vertical_layout.addWidget(self.camera_w)

        # Spacer to push content up and create space for the Confirm button
        self.vertical_layout.addStretch()

        # Confirm button at the bottom
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)  # Trigger accept to close dialog
        self.vertical_layout.addWidget(self.confirm_button, alignment=Qt.AlignCenter)

    def on_button_clicked(self, button):
        # Store the ID of the selected button
        self.selected_button_id = self.button_group.id(button)

    def exec_and_get_selection(self):
        # Execute the dialog modally
        result = self.exec_()
        # Check if the dialog was accepted before trying to access the selection
        if result == QDialog.Accepted:
            return self.selected_button_id
        return None

# Function to call the dialog and get the selected button ID
def get_selected_button():
    dialog = SelectionDialog()
    return dialog.exec_and_get_selection()

if __name__ == "__main__":
    # Enable high-DPI scaling for PySide2
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)

    # Set a default font to avoid font-related warnings
    QApplication.setFont(QFont("Arial", 10))

    # Call the function to get the selected button
    selected_button = get_selected_button()
    if selected_button is not None:
        print(f"Selected button: {selected_button}")
    else:
        print("No selection made.")

    sys.exit(app.exec_())

