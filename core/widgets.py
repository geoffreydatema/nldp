from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog
from PySide6.QtCore import Signal

class NLDPFileBrowserWidget(QWidget):
    """
    A compound widget that includes a QLineEdit for a file path
    and a QPushButton to open a file dialog.
    """
    # Custom signal that will be emitted when a file is chosen.
    path_selected = Signal()

    def __init__(self, view=None, parent=None):
        super().__init__(parent)
        
        self.view = view
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        self.line_edit = QLineEdit()
        self.browse_button = QPushButton("...")

        self.layout.addWidget(self.line_edit)
        self.layout.addWidget(self.browse_button)

        self.browse_button.clicked.connect(self.open_file_dialog)

    def open_file_dialog(self):
        """
        Opens a file dialog and sets the chosen path in the line edit.
        The view is used as the parent to prevent focus issues.
        """
        file_path, _ = QFileDialog.getOpenFileName(self.view, "Select File")
        if file_path:
            self.line_edit.setText(file_path)
            # Emit the custom signal to notify that a new path has been set.
            self.path_selected.emit()

    def text(self):
        """
        Returns the current text from the line edit.
        """
        return self.line_edit.text()

    def setText(self, text):
        """
        Sets the text in the line edit.
        """
        self.line_edit.setText(text)

    def textChanged(self):
        """
        Returns the textChanged signal from the line edit.
        """
        return self.line_edit.textChanged
