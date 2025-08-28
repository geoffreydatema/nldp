from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QColor, QPainterPath
from PySide6.QtCore import Qt, QPointF, QRectF
from . import constants

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
        self.data_type = None
        self.field_type = None
        self.connections = []
        self.label = ""
        self.socket_shape = constants.SOCKET_SHAPE_CIRCLE # Default shape

        # --- Visual Properties ---
        self.radius = radius
        self.color_fill = QColor(200, 200, 200) # Default grey

    def set_properties(self, socket_type, label, data_type, field_type, shape=constants.SOCKET_SHAPE_CIRCLE):
        """
        Sets the logical and visual properties of the socket.
        """
        self.socket_type = socket_type
        self.label = label
        self.data_type = data_type
        self.field_type = field_type
        self.socket_shape = shape
        
        # Set color based on data type
        color_tuple = constants.DTYPE_COLORS.get(data_type, (200, 200, 200))
        self.color_fill = QColor(*color_tuple)

    def boundingRect(self):
        """
        Returns the bounding rectangle of the socket.
        """
        if self.socket_shape == constants.SOCKET_SHAPE_PILL:
            return QRectF(-self.radius * 1.5, -self.radius,
                          self.radius * 3, self.radius * 2)
        else: # Circle
            return QRectF(-self.radius, -self.radius,
                          self.radius * 2, self.radius * 2)

    def paint(self, painter, option, widget=None):
        """
        Draws the socket.
        """
        painter.setBrush(self.color_fill)
        painter.setPen(Qt.PenStyle.NoPen)

        if self.socket_shape == constants.SOCKET_SHAPE_PILL:
            path = QPainterPath()
            path.addRoundedRect(self.boundingRect(), self.radius, self.radius)
            painter.drawPath(path)
        else: # Circle
            painter.drawEllipse(QPointF(0, 0), self.radius, self.radius)
