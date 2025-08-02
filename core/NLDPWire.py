from PySide6.QtWidgets import QGraphicsPathItem
from PySide6.QtGui import QColor, QPen, QPainterPath
from PySide6.QtCore import Qt, QPointF

class NLDPWire(QGraphicsPathItem):
    """
    Represents a wire connecting two sockets in the graph.
    """
    def __init__(self, start_socket, end_socket, parent=None):
        """
        Initializes the wire.

        Args:
            start_socket (NLDPSocket): The socket where the wire begins.
            end_socket (NLDPSocket): The socket where the wire ends.
            parent (QGraphicsItem): The parent item in the scene.
        """
        super().__init__(parent)
        self.start_socket = start_socket
        self.end_socket = end_socket

        # --- Visual Properties ---
        self.color = QColor(200, 200, 200)
        self.thickness = 2.0
        self.pen = QPen(self.color, self.thickness)
        self.pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(self.pen)
        
        # Ensure the wire is drawn behind nodes
        self.setZValue(-1)

        # Connect sockets
        self.start_socket.connections.append(self.end_socket)
        self.end_socket.connections.append(self.start_socket)

        self.update_path()

    def update_path(self):
        """
        Calculates and sets the cubic Bezier path for the wire.
        """
        start_pos = self.mapFromScene(self.start_socket.scenePos())
        end_pos = self.mapFromScene(self.end_socket.scenePos())

        path = QPainterPath()
        path.moveTo(start_pos)

        # --- Bezier Curve Calculation ---
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        
        # Control points are halfway horizontally, creating the "S" curve
        control_point1 = QPointF(start_pos.x() + dx * 0.5, start_pos.y())
        control_point2 = QPointF(start_pos.x() + dx * 0.5, end_pos.y())

        path.cubicTo(control_point1, control_point2, end_pos)
        self.setPath(path)

    def __del__(self):
        """
        Handles cleanup when the wire is deleted.
        """
        # Disconnect sockets
        if self.end_socket in self.start_socket.connections:
            self.start_socket.connections.remove(self.end_socket)
        if self.start_socket in self.end_socket.connections:
            self.end_socket.connections.remove(self.start_socket)
