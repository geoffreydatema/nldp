import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QStyle,
    QGraphicsPathItem,
    QMenu
)
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath
from PySide6.QtCore import Qt, QRectF, QLineF, QPoint, QPointF

SOCKET_TYPE_INPUT = 0
SOCKET_TYPE_OUTPUT = 1

class NLDPSocket(QGraphicsItem):
    """
    Represents a connection point (socket) on an NLDPNode.
    It is a child item of a node, so its position is relative to the node.
    """
    def __init__(self, parent, socket_type, radius=5.0, color=None):
        """
        Initializes the socket.

        Args:
            parent (QGraphicsItem): The parent NLDPNode of this socket.
            socket_type (str): The logical type of the socket (e.g., "INPUT", "OUTPUT").
            radius (float): The radius of the socket circle.
            color (tuple | list): An (R, G, B) tuple or list for the socket color.
        """
        super().__init__(parent)

        # --- Logical Properties ---
        self.socket_type = socket_type
        self.connections = []

        # --- Visual Properties ---
        self.radius = radius
        if isinstance(color, (tuple, list)) and len(color) == 3:
            self.color_fill = QColor(*color)
        else:
            # Default to orange if no valid color is provided
            self.color_fill = QColor(255, 165, 0)

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
        # Sockets will have no border for a cleaner look
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(0, 0), self.radius, self.radius)


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


class NLDPNode(QGraphicsItem):
    """
    Represents a single node in the NLDP graph.
    Handles drawing, interaction, and management of its sockets.
    """
    def __init__(self, title="New Node", width_units=8, height_units=12,
                 show_border=False, color=None, x=0, y=0,
                 left_sockets=0, right_sockets=0, top_sockets=0, bottom_sockets=0,
                 socket_radius=5.0, socket_color=None):
        """
        Initializes the node.

        Args:
            title (str): The name to be displayed in the node's title bar.
            width_units (int): The width of the node in grid units.
            height_units (int): The height of the node in grid units.
            show_border (bool): Whether to display the static design border.
            color (tuple | list): An (R, G, B) tuple or list for the node's body color.
            x (int | float): The initial x-position of the node in the scene.
            y (int | float): The initial y-position of the node in the scene.
            left_sockets (int): Number of sockets on the left.
            right_sockets (int): Number of sockets on the right.
            top_sockets (int): Number of sockets on the top.
            bottom_sockets (int): Number of sockets on the bottom.
            socket_radius (float): The radius for all sockets on this node.
            socket_color (tuple | list): The color for all sockets on this node.
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
        if isinstance(color, (tuple, list)) and len(color) == 3:
            self.color_body = QColor(*color)
        else:
            self.color_body = QColor(50, 50, 50)
        self.color_title_bar = self.color_body.lighter(130)
        self.color_title_text = QColor(220, 220, 220)
        
        # --- Border Pens ---
        border_thickness = 1.5
        self.color_border = QColor(110, 110, 110)
        self.pen_border = QPen(self.color_border, border_thickness)
        self.color_border_selected = QColor(240, 240, 240)
        self.pen_border_selected = QPen(self.color_border_selected, border_thickness)

        # --- Sockets ---
        self.socket_radius = socket_radius
        self.socket_color = socket_color
        self.left_sockets = []
        self.right_sockets = []
        self.top_sockets = []
        self.bottom_sockets = []
        self._create_sockets(left_sockets, right_sockets, top_sockets, bottom_sockets)

        # --- Interaction State ---
        self._is_dragging = False
        self._drag_offset = QPointF()

        # Set flags for interaction
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setPos(x, y)

    def _create_sockets(self, num_left, num_right, num_top, num_bottom):
        """
        Creates and positions the sockets on the node.
        """
        # --- Vertical Sockets (Left/Right) ---
        available_v_slots = (self.height / self.grid_size) - 1
        num_left = min(int(available_v_slots), num_left)
        num_right = min(int(available_v_slots), num_right)

        y_start = self.title_bar_height + self.grid_size / 2
        
        for i in range(num_left):
            socket = NLDPSocket(parent=self, socket_type=SOCKET_TYPE_INPUT, radius=self.socket_radius, color=self.socket_color)
            y_pos = y_start + (i * self.grid_size)
            socket.setPos(0, y_pos)
            self.left_sockets.append(socket)

        for i in range(num_right):
            socket = NLDPSocket(parent=self, socket_type=SOCKET_TYPE_OUTPUT, radius=self.socket_radius, color=self.socket_color)
            y_pos = y_start + (i * self.grid_size)
            socket.setPos(self.width, y_pos)
            self.right_sockets.append(socket)
            
        # --- Horizontal Sockets (Top/Bottom) ---
        available_h_slots = self.width / self.grid_size
        num_top = min(int(available_h_slots), num_top)
        num_bottom = min(int(available_h_slots), num_bottom)

        # Calculate starting x-position from the right edge
        x_start_right = self.width - (self.grid_size / 2)

        for i in range(num_top):
            socket = NLDPSocket(parent=self, socket_type=SOCKET_TYPE_INPUT, radius=self.socket_radius, color=self.socket_color)
            x_pos = x_start_right - (i * self.grid_size)
            socket.setPos(x_pos, 0)
            self.top_sockets.append(socket)
            
        for i in range(num_bottom):
            socket = NLDPSocket(parent=self, socket_type=SOCKET_TYPE_OUTPUT, radius=self.socket_radius, color=self.socket_color)
            x_pos = x_start_right - (i * self.grid_size)
            socket.setPos(x_pos, self.height)
            self.bottom_sockets.append(socket)

    def get_all_sockets(self):
        """
        Returns a list of all sockets on this node.
        """
        return self.left_sockets + self.right_sockets + self.top_sockets + self.bottom_sockets

    def boundingRect(self):
        """
        Returns the bounding rectangle, expanded to include sockets.
        """
        margin = self.pen_border_selected.width() / 2
        socket_margin = self.socket_radius
        return QRectF(0 - margin - socket_margin, 0 - margin - socket_margin,
                      self.width + (margin + socket_margin) * 2,
                      self.height + (margin + socket_margin) * 2)

    def paint(self, painter, option, widget=None):
        """
        Draws the node. Sockets are child items and draw themselves.
        """
        body_path = QPainterPath()
        body_rect = QRectF(0, 0, self.width, self.height)
        body_path.addRoundedRect(body_rect, self.corner_radius, self.corner_radius)
        painter.setBrush(self.color_body)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(body_path)

        painter.setBrush(self.color_title_bar)
        painter.setPen(Qt.PenStyle.NoPen)
        title_rounded_path = QPainterPath()
        title_rounded_path.addRoundedRect(QRectF(0, 0, self.width, self.title_bar_height), self.corner_radius, self.corner_radius)
        painter.drawPath(title_rounded_path)
        unrounder_rect = QRectF(0, self.corner_radius, self.width, self.title_bar_height - self.corner_radius)
        painter.drawRect(unrounder_rect)

        painter.setPen(self.color_title_text)
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        text_padding = 8
        text_rect = QRectF(text_padding, 0, self.width - text_padding, self.title_bar_height)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title)

        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if self.show_border or is_selected:
            border_path = QPainterPath()
            border_rect = QRectF(0, 0, self.width, self.height)
            border_path.addRoundedRect(border_rect, self.corner_radius, self.corner_radius)
            current_pen = self.pen_border_selected if is_selected else self.pen_border
            painter.setPen(current_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(border_path)

    def mousePressEvent(self, event):
        """
        Handles mouse press events to initiate dragging.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            title_bar_rect = QRectF(0, 0, self.width, self.title_bar_height)
            is_title_bar_click = title_bar_rect.contains(event.pos())

            view = self.scene().views()[0] if self.scene() and self.scene().views() else None
            is_space_drag = (view is not None and
                             hasattr(view, '_spacebar_pressed') and
                             view._spacebar_pressed)

            if is_title_bar_click or is_space_drag:
                # If this is a move operation, clear the scene's selection
                # and select only this node.
                if self.scene():
                    self.scene().clearSelection()
                self.setSelected(True)

                self._is_dragging = True
                self._drag_offset = self.pos() - event.scenePos()
                event.accept()
                return
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Handles mouse move events to drag the node and update its wires.
        """
        if self._is_dragging:
            self.setPos(event.scenePos() + self._drag_offset)
            # --- Update connected wires ---
            for socket in self.get_all_sockets():
                for connection in socket.connections:
                    # Find the wire associated with this connection
                    for item in self.scene().items():
                        if isinstance(item, NLDPWire) and \
                           ((item.start_socket == socket and item.end_socket == connection) or \
                            (item.start_socket == connection and item.end_socket == socket)):
                            item.update_path()
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
    Implements custom background drawing, panning, zooming, and wire creation/deletion.
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
        self._is_cutting = False # For wire deletion
        self._last_pan_point = QPoint()
        self._last_zoom_point = QPoint()
        self._zoom_scene_anchor = QPointF()
        
        # --- Wire Drawing State ---
        self.drawing_wire = None
        self.start_socket = None

        # --- Keyboard State ---
        self._spacebar_pressed = False

        # --- Zoom Limits ---
        self.MIN_ZOOM = 0.2
        self.MAX_ZOOM = 5.0

        # Default anchor is under the mouse, for wheel-based zooming.
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def contextMenuEvent(self, event):
        """
        Handles right-click events to show the 'Add Node' menu.
        """
        menu = QMenu(self)
        
        # --- Menu Styling (Updated with user's preferences) ---
        menu_stylesheet = """
            QMenu {
                background-color: #d98c00;
                color: white;
                border: 0;
                margin: 4px;
            }
            QMenu::item {
                padding: 2px 24px;
            }
            QMenu::item:selected {
                background-color: #d99c2b;
            }
            QMenu::right-arrow {
                image: none;
            }
        """
        menu.setStyleSheet(menu_stylesheet)
        
        # --- First Test Category ---
        test_menu = menu.addMenu("Test")
        add_node1_action = test_menu.addAction("Simple I/O Node")
        add_node2_action = test_menu.addAction("Processing Node")
        add_node3_action = test_menu.addAction("Output Only Node")

        # --- Second Test Category ---
        more_tests_menu = menu.addMenu("More Tests")
        add_node4_action = more_tests_menu.addAction("Top/Bottom Node")
        add_node5_action = more_tests_menu.addAction("Wide Node")
        
        # Execute the menu and get the chosen action
        action = menu.exec(event.globalPos())
        scene_pos = self.mapToScene(event.pos())
        
        # Add a new node if an action was selected
        if action == add_node1_action:
            new_node = NLDPNode(title="Simple I/O", x=scene_pos.x(), y=scene_pos.y(), left_sockets=2, right_sockets=1)
            self.scene().addItem(new_node)
        elif action == add_node2_action:
            new_node = NLDPNode(title="Processing", x=scene_pos.x(), y=scene_pos.y(), left_sockets=1, right_sockets=2, color=(20, 90, 20))
            self.scene().addItem(new_node)
        elif action == add_node3_action:
            new_node = NLDPNode(title="Output Only", x=scene_pos.x(), y=scene_pos.y(), right_sockets=1, color=(20, 20, 90))
            self.scene().addItem(new_node)
        elif action == add_node4_action:
            new_node = NLDPNode(title="Top/Bottom", x=scene_pos.x(), y=scene_pos.y(), top_sockets=2, bottom_sockets=2, color=(90, 90, 20))
            self.scene().addItem(new_node)
        elif action == add_node5_action:
            new_node = NLDPNode(title="Wide Node", width_units=12, height_units=4, x=scene_pos.x(), y=scene_pos.y(), left_sockets=1, right_sockets=1, color=(90, 20, 90))
            self.scene().addItem(new_node)


    def is_circular_connection(self, start_socket, end_socket):
        """
        Checks if creating a wire between two sockets would create a cycle.

        Args:
            start_socket (NLDPSocket): The proposed starting socket.
            end_socket (NLDPSocket): The proposed ending socket.

        Returns:
            bool: True if a cycle would be created, False otherwise.
        """
        # Determine the start and end nodes for the traversal
        output_socket = start_socket if start_socket.socket_type == SOCKET_TYPE_OUTPUT else end_socket
        input_socket = end_socket if end_socket.socket_type == SOCKET_TYPE_INPUT else start_socket
        
        start_node = output_socket.parentItem()
        end_node = input_socket.parentItem()

        # Use a breadth-first search to traverse downstream from the end_node
        nodes_to_visit = [end_node]
        visited_nodes = {end_node}

        while nodes_to_visit:
            current_node = nodes_to_visit.pop(0)
            
            # If we reach the start_node, we have found a cycle
            if current_node == start_node:
                return True

            # Get all output sockets from the current node
            output_sockets = current_node.right_sockets + current_node.bottom_sockets
            for socket in output_sockets:
                for connection in socket.connections:
                    next_node = connection.parentItem()
                    if next_node not in visited_nodes:
                        visited_nodes.add(next_node)
                        nodes_to_visit.append(next_node)
        
        return False

    def keyPressEvent(self, event):
        """
        Tracks when the spacebar is pressed or when items are deleted.
        """
        if event.key() == Qt.Key.Key_Space:
            self._spacebar_pressed = True
        elif event.key() == Qt.Key.Key_Delete:
            selected_items = self.scene().selectedItems()
            if not selected_items:
                super().keyPressEvent(event)
                return

            # Use a set to avoid trying to remove the same wire multiple times
            wires_to_remove = set()
            nodes_to_remove = []

            for item in selected_items:
                if isinstance(item, NLDPNode):
                    nodes_to_remove.append(item)
                    # Find all wires connected to this node's sockets
                    for socket in item.get_all_sockets():
                        for connected_socket in socket.connections:
                            # Find the wire that connects these two sockets
                            for scene_item in self.scene().items():
                                if isinstance(scene_item, NLDPWire):
                                    if (scene_item.start_socket == socket and scene_item.end_socket == connected_socket) or \
                                       (scene_item.start_socket == connected_socket and scene_item.end_socket == socket):
                                        wires_to_remove.add(scene_item)
                elif isinstance(item, NLDPWire):
                    wires_to_remove.add(item)

            # Remove all identified items from the scene
            for wire in wires_to_remove:
                self.scene().removeItem(wire)
            for node in nodes_to_remove:
                self.scene().removeItem(node)

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """
        Tracks when the spacebar is released.
        """
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._spacebar_pressed = False
        super().keyReleaseEvent(event)

    def wheelEvent(self, event):
        """
        Handles mouse wheel events for zooming, respecting zoom limits.
        """
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        current_scale = self.transform().m11()
        new_scale = current_scale * zoom_factor

        if self.MIN_ZOOM <= new_scale <= self.MAX_ZOOM:
            self.scale(zoom_factor, zoom_factor)
        
        event.accept()

    def mousePressEvent(self, event):
        """
        Handles mouse press events to initiate various interactions.
        """
        # --- Wire Cutting ---
        is_cutting = (event.button() == Qt.MouseButton.LeftButton and 
                      event.modifiers() == Qt.KeyboardModifier.ControlModifier)
        if is_cutting:
            self._is_cutting = True
            self.setCursor(Qt.CursorShape.CrossCursor)
            # Immediately check for a wire to delete on click
            item_to_cut = self.itemAt(event.position().toPoint())
            if isinstance(item_to_cut, NLDPWire):
                self.scene().removeItem(item_to_cut)
            event.accept()
            return

        # --- Wire Drawing ---
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, NLDPSocket):
            self.start_socket = item
            self.drawing_wire = QGraphicsPathItem()
            pen = QPen(QColor(200, 200, 200), 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            self.drawing_wire.setPen(pen)
            self.scene().addItem(self.drawing_wire)
            self.setCursor(Qt.CursorShape.CrossCursor)
            event.accept()
            return
            
        # --- Panning and Zooming ---
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
            self._zoom_scene_anchor = self.mapToScene(event.position().toPoint())
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
            event.accept()
            return

        # --- Multi-Select ---
        is_shift_select = (event.button() == Qt.MouseButton.LeftButton and
                           event.modifiers() == Qt.KeyboardModifier.ShiftModifier)
        if is_shift_select:
            item_to_select = self.itemAt(event.position().toPoint())
            if isinstance(item_to_select, NLDPNode):
                # Toggle the selection state of the item without clearing others
                item_to_select.setSelected(not item_to_select.isSelected())
                event.accept()
                return
        
        if event.button() == Qt.MouseButton.LeftButton:
            # --- Rubber Band Selection ---
            # If no other action is taken, a left-click drag will start a rubber band selection.
            # Change the cursor to indicate this.
            self.setCursor(Qt.CursorShape.CrossCursor)
            super().mousePressEvent(event)
        
        # Right-clicks are handled by contextMenuEvent, so we don't call super() for them here.
        # This prevents the default right-click drag/select behavior.

    def mouseMoveEvent(self, event):
        """
        Handles mouse move events for various interactions.
        """
        # --- Wire Cutting ---
        if self._is_cutting:
            item_to_cut = self.itemAt(event.position().toPoint())
            if isinstance(item_to_cut, NLDPWire):
                self.scene().removeItem(item_to_cut)
            event.accept()
            return

        # --- Wire Drawing ---
        if self.drawing_wire:
            start_pos = self.start_socket.scenePos()
            end_pos = self.mapToScene(event.position().toPoint())
            
            path = QPainterPath()
            path.moveTo(start_pos)
            
            dx = end_pos.x() - start_pos.x()
            dy = end_pos.y() - start_pos.y()
        
            control_point1 = QPointF(start_pos.x() + dx * 0.5, start_pos.y())
            control_point2 = QPointF(start_pos.x() + dx * 0.5, end_pos.y())

            path.cubicTo(control_point1, control_point2, end_pos)
            self.drawing_wire.setPath(path)
            event.accept()
            return

        # --- Panning and Zooming ---
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

            zoom_factor_delta = 1 + (delta.x() * 0.005)

            current_scale = self.transform().m11()
            potential_new_scale = current_scale * zoom_factor_delta
            clamped_new_scale = max(self.MIN_ZOOM, min(potential_new_scale, self.MAX_ZOOM))

            if clamped_new_scale != current_scale:
                actual_zoom_factor = clamped_new_scale / current_scale
                old_view_anchor = self.mapFromScene(self._zoom_scene_anchor)
                self.scale(actual_zoom_factor, actual_zoom_factor)
                new_view_anchor = self.mapFromScene(self._zoom_scene_anchor)
                pan_delta = new_view_anchor - old_view_anchor
                self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + pan_delta.x())
                self.verticalScrollBar().setValue(self.verticalScrollBar().value() + pan_delta.y())

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Handles mouse release events to stop an interaction.
        """
        # --- Wire Cutting ---
        if self._is_cutting and event.button() == Qt.MouseButton.LeftButton:
            self._is_cutting = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        # --- Wire Drawing ---
        if self.drawing_wire:
            # Hide the ghost wire to check what's underneath
            self.drawing_wire.hide()
            end_item = self.itemAt(event.position().toPoint())
            
            # Check for a valid connection
            is_valid_target = isinstance(end_item, NLDPSocket) and self.start_socket != end_item
            is_valid_type = is_valid_target and self.start_socket.socket_type != end_item.socket_type
            is_not_circular = is_valid_type and not self.is_circular_connection(self.start_socket, end_item)

            if is_valid_target and is_valid_type and is_not_circular:
                
                # Determine which socket is the input
                input_socket = end_item if end_item.socket_type == SOCKET_TYPE_INPUT else self.start_socket
                
                # --- Enforce single connection for INPUT sockets ---
                if input_socket.connections:
                    # Get the old socket it was connected to
                    old_partner_socket = input_socket.connections[0]
                    # Find and remove the old wire from the scene
                    for item in self.scene().items():
                        if isinstance(item, NLDPWire) and \
                           ((item.start_socket == input_socket and item.end_socket == old_partner_socket) or \
                            (item.start_socket == old_partner_socket and item.end_socket == input_socket)):
                            self.scene().removeItem(item)
                            break # Found and removed the old wire
                
                # --- Create a permanent wire ---
                wire = NLDPWire(self.start_socket, end_item)
                self.scene().addItem(wire)

            # Clean up the ghost wire
            self.scene().removeItem(self.drawing_wire)
            self.drawing_wire = None
            self.start_socket = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        # --- Panning and Zooming ---
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
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            event.accept()
            return
        
        # Reset cursor after a rubber band selection
        self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseReleaseEvent(event)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        """
        Overrides the default background drawing to render a grid.
        """
        super().drawBackground(painter, rect)
        grid_size = 16
        major_line_every = 8
        major_line_size = grid_size * major_line_every
        
        color_minor = QColor(24, 24, 24)
        color_major = QColor(32, 32, 32)

        pen_minor = QPen(color_minor, 1.0)
        pen_major = QPen(color_major, 1.0)

        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        lines_minor = []
        lines_major = []

        for x in range(left, int(rect.right()), grid_size):
            line = QLineF(x, rect.top(), x, rect.bottom())
            if x % major_line_size == 0:
                lines_major.append(line)
            else:
                lines_minor.append(line)
        
        for y in range(top, int(rect.bottom()), grid_size):
            line = QLineF(rect.left(), y, rect.right(), y)
            if y % major_line_size == 0:
                lines_major.append(line)
            else:
                lines_minor.append(line)

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
        node = NLDPNode(
            title="ALPHA",
            width_units=8,
            height_units=4,
            left_sockets=2,
            right_sockets=1
        )
        self.scene.addItem(node)

        node2 = NLDPNode(
            title="BETA",
            x=16*16,
            width_units=7,
            height_units=13,
            left_sockets=4,
            right_sockets=1
        )
        self.scene.addItem(node2)

        node3 = NLDPNode(
            title="GAMMA",
            y=8*16,
            width_units=8,
            height_units=4,
            left_sockets=1,
            right_sockets=1,
            top_sockets=2,
            bottom_sockets=1
        )
        self.scene.addItem(node3)


if __name__ == "__main__":
    # --- Application Setup ---
    app = QApplication(sys.argv)

    # --- Create and Show Window ---
    window = NLDPWindow()
    window.show()

    # --- Start Event Loop ---
    sys.exit(app.exec())
