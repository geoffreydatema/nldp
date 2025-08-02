from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, QRectF, QPointF

class NLDPSocket(QGraphicsItem):
    """
    Represents a connection point (socket) on an NLDPNode.
    Its properties are now set by its parent node during layout creation.
    """
    def __init__(self, parent, radius=5.0):
        """
        Initializes the socket.

        Args:
            parent (QGraphicsItem): The parent NLDPNode of this socket.
            radius (float): The radius of the socket circle.
        """
        super().__init__(parent)

        # --- Logical Properties (set by the parent node) ---
        self.socket_type = None
        self.connections = []
        self.label = ""

        # --- Visual Properties ---
        self.radius = radius
        self.color_fill = QColor(255, 165, 0) # Default orange

    def set_properties(self, socket_type, label, color):
        """
        Sets the logical and visual properties of the socket.

        Args:
            socket_type (str): The logical type (e.g., SOCKET_TYPE_INPUT).
            label (str): The text label to be displayed next to the socket.
            color (QColor): The fill color of the socket.
        """
        self.socket_type = socket_type
        self.label = label
        if color:
            self.color_fill = color

    def boundingRect(self):
        """
        Returns the bounding rectangle of the socket.
        """
        return QRectF(-self.radius, -self.radius,
                      self.radius * 2, self.radius * 2)

    def paint(self, painter, option, widget=None):
        """
        Draws the socket circle.
        """
        painter.setBrush(self.color_fill)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(0, 0), self.radius, self.radius)
