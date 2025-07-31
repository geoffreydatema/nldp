import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QStyle
)
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath
from PySide6.QtCore import Qt, QRectF, QLineF, QPoint, QPointF

class NLDPNode(QGraphicsItem):
    """
    Represents a single node in the NLDP graph.
    Handles drawing, interaction, and basic properties.
    """
    def __init__(self, title="New Node", width_units=8, height_units=12, show_border=False, color=None, x=0, y=0):
        """
        Initializes the node.

        Args:
            title (str): The name to be displayed in the node's title bar.
            width_units (int): The width of the node in grid units.
            height_units (int): The height of the node in grid units.
            show_border (bool): Whether to display the static design border.
            color (tuple | list): An (R, G, B) tuple or list for the node's body color.
        """
        super().__init__()

        # --- Configuration ---
        self.grid_size = 16
        # Enforce minimum size to prevent drawing errors
        width_units = max(1, width_units)
        height_units = max(2, height_units)
        self.width = width_units * self.grid_size
        self.height = height_units * self.grid_size
        self.title = title
        self.show_border = show_border
        
        # --- Visual Properties ---
        self.corner_radius = 8.0
        self.title_bar_height = 1 * self.grid_size # 1 grid unit
        
        # --- Color Management ---
        # Set the main body color from a tuple/list, defaulting to grey.
        if isinstance(color, (tuple, list)) and len(color) == 3:
            self.color_body = QColor(*color)
        else:
            self.color_body = QColor(50, 50, 50)
            
        # Automatically calculate the title bar color to be a lighter shade.
        self.color_title_bar = self.color_body.lighter(130)
        
        self.color_title_text = QColor(220, 220, 220)
        
        # --- Border Pens ---
        border_thickness = 1.5
        self.color_border = QColor(110, 110, 110)
        self.pen_border = QPen(self.color_border, border_thickness)
        
        self.color_border_selected = QColor(240, 240, 240) # Light grey for selection
        self.pen_border_selected = QPen(self.color_border_selected, border_thickness)

        # --- Interaction State ---
        self._is_dragging = False
        self._drag_offset = QPointF()

        # Set flags for interaction
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        # We handle movement manually, so ItemIsMovable is NOT set.
        self.setAcceptHoverEvents(True) # Needed for cursor changes
        
        # Set initial position
        self.setPos(x, y)

    def boundingRect(self):
        """
        Must be implemented. Returns the bounding rectangle of the item.
        """
        # Add a small margin to the bounding rect for the border pen
        margin = self.pen_border_selected.width() / 2
        return QRectF(0 - margin, 0 - margin, self.width + margin*2, self.height + margin*2)

    def paint(self, painter, option, widget=None):
        """
        Draws the node.
        """
        # --- Body ---
        body_path = QPainterPath()
        body_rect = QRectF(0, 0, self.width, self.height)
        body_path.addRoundedRect(body_rect, self.corner_radius, self.corner_radius)
        painter.setBrush(self.color_body)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(body_path)

        # --- Title Bar ---
        painter.setBrush(self.color_title_bar)
        painter.setPen(Qt.PenStyle.NoPen)
        # First, draw a rounded rect for the full title bar area
        title_rounded_path = QPainterPath()
        title_rounded_path.addRoundedRect(QRectF(0, 0, self.width, self.title_bar_height), self.corner_radius, self.corner_radius)
        painter.drawPath(title_rounded_path)
        # Second, draw a sharp-cornered rect over the bottom half to hide the lower curves
        unrounder_rect = QRectF(0, self.corner_radius, self.width, self.title_bar_height - self.corner_radius)
        painter.drawRect(unrounder_rect)

        # --- Title Text ---
        painter.setPen(self.color_title_text)
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        # Add some left padding to the text rectangle
        text_padding = 8
        text_rect = QRectF(text_padding, 0, self.width - text_padding, self.title_bar_height)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title)

        # --- Border ---
        # The border is drawn last, on top of everything else.
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        
        if self.show_border or is_selected:
            border_path = QPainterPath()
            border_rect = QRectF(0, 0, self.width, self.height)
            border_path.addRoundedRect(border_rect, self.corner_radius, self.corner_radius)
            
            # Use the selection pen if selected, otherwise use the default border pen
            current_pen = self.pen_border_selected if is_selected else self.pen_border
            painter.setPen(current_pen)
            
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(border_path)


    def mousePressEvent(self, event):
        """
        Handles mouse press events to initiate dragging from the title bar.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            title_bar_rect = QRectF(0, 0, self.width, self.title_bar_height)
            if title_bar_rect.contains(event.pos()):
                self._is_dragging = True
                self._drag_offset = self.pos() - event.scenePos()
                # Ensure the item is selected when dragging from the title bar
                if not self.isSelected():
                    self.setSelected(True)
                event.accept()
                return
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Handles mouse move events to drag the node.
        """
        if self._is_dragging:
            self.setPos(event.scenePos() + self._drag_offset)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Handles mouse release events to stop dragging.
        """
        if self._is_dragging and event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()
            return
            
        super().mouseReleaseEvent(event)


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

        # --- Add a test node ---
        node = NLDPNode(title="Test Node", width_units=8, height_units=8)
        node2 = NLDPNode(title="Test Node", width_units=8, height_units=12, x=16*10)
        self.scene.addItem(node)
        self.scene.addItem(node2)


if __name__ == "__main__":
    # --- Application Setup ---
    app = QApplication(sys.argv)

    # --- Create and Show Window ---
    window = NLDPWindow()
    window.show()

    # --- Start Event Loop ---
    sys.exit(app.exec())
