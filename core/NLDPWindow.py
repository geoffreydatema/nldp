from PySide6.QtWidgets import QMainWindow, QGraphicsScene
from PySide6.QtGui import QColor
from core import NLDPView
from standard import NLDPStandardValueNode, NLDPStandardOutputNode

class NLDPWindow(QMainWindow):
    """
    The main window for the NLDP application.
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
        self.scene = QGraphicsScene()
        # Set a large scene rectangle to allow for panning around.
        self.scene.setSceneRect(-4096, -4096, 8192, 8192)
        self.scene.setBackgroundBrush(QColor(20, 20, 20))

        # --- Graphics View ---
        # We now use our custom NLDPView class.
        self.view = NLDPView(self.scene, self)
        
        # Set the view as the central widget of the main window
        self.setCentralWidget(self.view)

        self.scene.addItem(NLDPStandardValueNode(x=0, y=0))
        self.scene.addItem(NLDPStandardOutputNode(x=8*32, y=0))
