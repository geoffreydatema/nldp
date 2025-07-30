import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtCore import Qt


class NLDPWindow(QMainWindow):
    """
    The main window for the node editor application.
    """

    def __init__(self, parent=None):
        """
        Initializes the main window, scene, and view.
        """
        super().__init__(parent)

        # --- Window Properties ---
        self.setWindowTitle("nldp")
        self.setGeometry(0, 0, 1280, 720)

        # --- Graphics Scene ---
        # The scene is the logical container for all 2D graphical items.
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(20, 20, 20)) # A dark background color

        # --- Graphics View ---
        # The view is the widget that visualizes the scene.
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing) # Improves visual quality
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag) # Allows selecting items by dragging a box
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)


        # Set the view as the central widget of the main window
        self.setCentralWidget(self.view)

        # --- Add a simple test item ---
        # This is just to demonstrate that the scene is working.
        # We will replace this with actual nodes later.
        test_item = QGraphicsRectItem(0, 0, 128, 192)
        test_item.setBrush(QColor(50, 50, 50))
        test_item.setPen(QColor(110, 110, 110))
        self.scene.addItem(test_item)


if __name__ == "__main__":
    # --- Application Setup ---
    app = QApplication(sys.argv)

    # --- Create and Show Window ---
    window = NLDPWindow()
    window.show()

    # --- Start Event Loop ---
    sys.exit(app.exec())
