import sys
from PySide2.QtWidgets import QApplication, QDialog
from PySide2.QtCore import Qt


class ShotMerge(QDialog):
    def __init__(self, modules=None):  # Change to accept modules as an argument
        super().__init__()  # Call the superclass's __init__
        self.modules = modules
        self.test()

    def test(self):
        print(self.modules)  # Print the modules attribute


def run(modules=None):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    dialog = ShotMerge(modules)  # Pass the modules dictionary to the dialog
    dialog.show()  # Show the dialog
    sys.exit(app.exec_())


if __name__ == "__main__":
    run({"test": "hi there"})  # Call run without arguments
