import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
)
from PySide6.QtGui import QColor, QPainter, QPen, QTransform
from PySide6.QtCore import Qt, QRectF, QLineF, QPoint, QPointF


class NLDPView(QGraphicsView):
    """
    Custom QGraphicsView for the NLDP editor.
    Implements custom background drawing, panning, and zooming with limits.
    """
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # --- Interaction State ---
        self._is_panning = False
        self._is_zooming = False
        self._last_pan_point = QPoint()
        self._last_zoom_point = QPoint()
        self._zoom_scene_anchor = QPointF()

        # --- Zoom Limits ---
        self.MIN_ZOOM = 0.2
        self.MAX_ZOOM = 5.0

        # Default anchor is under the mouse, for wheel-based zooming.
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, event):
        """
        Handles mouse wheel events for zooming, respecting zoom limits.
        """
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        # Check if the wheel is scrolled up or down
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        # Get the current scale and calculate the potential new scale
        current_scale = self.transform().m11()
        new_scale = current_scale * zoom_factor

        # Check if the new scale is within the defined limits
        if self.MIN_ZOOM <= new_scale <= self.MAX_ZOOM:
            self.scale(zoom_factor, zoom_factor)
        
        event.accept()


    def mousePressEvent(self, event):
        """
        Handles mouse press events to initiate panning or zooming.
        - Panning: Middle Mouse Button or Alt + Left Mouse Button.
        - Zooming: Alt + Right Mouse Button.
        """
        is_pan_middle = event.button() == Qt.MouseButton.MiddleButton
        is_pan_alt_left = (event.button() == Qt.MouseButton.LeftButton and
                           event.modifiers() == Qt.KeyboardModifier.AltModifier)
        is_zoom_alt_right = (event.button() == Qt.MouseButton.RightButton and
                             event.modifiers() == Qt.KeyboardModifier.AltModifier)

        if is_pan_middle or is_pan_alt_left:
            self._is_panning = True
            self._last_pan_point = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            event.accept()
            return

        if is_zoom_alt_right:
            self._is_zooming = True
            self._last_zoom_point = event.position().toPoint()
            # Store the scene point that should remain stationary.
            self._zoom_scene_anchor = self.mapToScene(event.position().toPoint())
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            # Set anchor to center for the scaling operation.
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Handles mouse release events to stop an interaction (panning or zooming).
        """
        if self._is_panning and (event.button() == Qt.MouseButton.MiddleButton or event.button() == Qt.MouseButton.LeftButton):
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            event.accept()
            return
            
        if self._is_zooming and event.button() == Qt.MouseButton.RightButton:
            self._is_zooming = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            # Restore the default anchor for wheel-based zooming.
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """
        Handles mouse move events to perform panning or zooming.
        """
        if self._is_panning:
            current_pos = event.position().toPoint()
            delta = current_pos - self._last_pan_point
            self._last_pan_point = current_pos
            
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            
            event.accept()
            return

        if self._is_zooming:
            current_pos = event.position().toPoint()
            delta = current_pos - self._last_zoom_point
            self._last_zoom_point = current_pos

            # Calculate zoom factor based on horizontal movement
            zoom_factor_delta = 1 + (delta.x() * 0.005)

            # Get current scale and calculate potential new scale
            current_scale = self.transform().m11()
            potential_new_scale = current_scale * zoom_factor_delta

            # Clamp the new scale to the defined limits
            clamped_new_scale = max(self.MIN_ZOOM, min(potential_new_scale, self.MAX_ZOOM))

            # If the scale is already at a limit and we're trying to go further, do nothing.
            if clamped_new_scale == current_scale:
                event.accept()
                return
                
            # Calculate the actual zoom factor to apply to reach the clamped scale
            actual_zoom_factor = clamped_new_scale / current_scale

            # Get the view coordinates of the anchor point before scaling
            old_view_anchor = self.mapFromScene(self._zoom_scene_anchor)

            # Scale the view using the clamped factor
            self.scale(actual_zoom_factor, actual_zoom_factor)

            # Get the view coordinates of the anchor point after scaling
            new_view_anchor = self.mapFromScene(self._zoom_scene_anchor)

            # Calculate the pan required to move the anchor point back to its original view position
            pan_delta = new_view_anchor - old_view_anchor

            # Apply the corrective pan
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + pan_delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + pan_delta.y())

            event.accept()
            return

        super().mouseMoveEvent(event)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        """
        Overrides the default background drawing to render a grid.
        
        Args:
            painter: The QPainter instance to use for drawing.
            rect: The exposed rectangle area that needs to be redrawn.
        """
        super().drawBackground(painter, rect)

        # --- Grid Properties (Updated with user values) ---
        grid_size = 16
        major_line_every = 8
        major_line_size = grid_size * major_line_every
        
        # --- Colors (Updated with user values) ---
        color_minor = QColor(24, 24, 24)
        color_major = QColor(32, 32, 32)

        # --- Pens (Updated with user values) ---
        pen_minor = QPen(color_minor, 1.0)
        pen_major = QPen(color_major, 1.0)

        # Calculate the start points, aligned to the grid.
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        # --- Prepare lines for batch drawing (more efficient) ---
        lines_minor = []
        lines_major = []

        # --- Vertical Lines ---
        for x in range(left, int(rect.right()), grid_size):
            line = QLineF(x, rect.top(), x, rect.bottom())
            if x % major_line_size == 0:
                lines_major.append(line)
            else:
                lines_minor.append(line)
        
        # --- Horizontal Lines ---
        for y in range(top, int(rect.bottom()), grid_size):
            line = QLineF(rect.left(), y, rect.right(), y)
            if y % major_line_size == 0:
                lines_major.append(line)
            else:
                lines_minor.append(line)

        # --- Draw the lines ---
        painter.setPen(pen_minor)
        painter.drawLines(lines_minor)

        painter.setPen(pen_major)
        painter.drawLines(lines_major)


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
