import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
    QStyle,
    QGraphicsPathItem,
    QMenu,
    QLineEdit,
    QGraphicsProxyWidget
)
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath
from PySide6.QtCore import Qt, QRectF, QLineF, QPoint, QPointF

SOCKET_TYPE_INPUT = 0
SOCKET_TYPE_OUTPUT = 1
ROW_TYPE_INPUT = 2
ROW_TYPE_OUTPUT = 3
ROW_TYPE_STATIC_FIELD = 4

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
    Builds its visual layout and sockets from a structured 'layout' list.
    """
    def __init__(self, title="New Node", layout=None, show_border=False, color=None, x=0, y=0):
        """
        Initializes the node.

        Args:
            title (str): The name to be displayed in the node's title bar.
            layout (list[dict]): A list of dictionaries defining the node's rows.
            show_border (bool): Whether to display the static design border.
            color (tuple | list): An (R, G, B) tuple or list for the node's body color.
            x (int | float): The initial x-position of the node in the scene.
            y (int | float): The initial y-position of the node in the scene.
        """
        super().__init__()

        # --- Configuration ---
        self.grid_size = 16
        self.layout = layout if layout is not None else []
        self.width = 8 * self.grid_size # Default width, can be overridden later
        # Height is determined by the title bar + number of rows in the layout
        self.height = (len(self.layout) + 1) * self.grid_size
        self.title = title
        self.show_border = show_border
        
        # --- Visual Properties ---
        self.corner_radius = 8.0
        self.title_bar_height = 1 * self.grid_size
        
        # --- Color Management ---
        if isinstance(color, (tuple, list)) and len(color) == 3:
            self.color_body = QColor(*color)
        else:
            self.color_body = QColor(50, 50, 50)
        self.color_title_bar = self.color_body.lighter(130)
        self.color_title_text = QColor(220, 220, 220)
        self.color_label_text = QColor(200, 200, 200)
        
        # --- Border Pens ---
        border_thickness = 1.5
        self.color_border = QColor(110, 110, 110)
        self.pen_border = QPen(self.color_border, border_thickness)
        self.color_border_selected = QColor(240, 240, 240)
        self.pen_border_selected = QPen(self.color_border_selected, border_thickness)

        # --- Data and UI Components ---
        self.sockets = {}
        self.static_fields = {}
        self.input_values = {}
        self.output_values = {}
        self._build_from_layout()

        # --- Interaction State ---
        self._is_dragging = False
        self._drag_offset = QPointF()

        # Set flags for interaction
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setPos(x, y)

    def _build_from_layout(self):
        """
        Creates sockets and UI fields based on the layout definition.
        """
        for i, row_data in enumerate(self.layout):
            row_type = row_data.get('type')
            label = row_data.get('label', '')
            y_pos = self.title_bar_height + (i * self.grid_size) + (self.grid_size / 2)

            if row_type == ROW_TYPE_INPUT:
                socket = NLDPSocket(parent=self)
                socket.set_properties(SOCKET_TYPE_INPUT, label, QColor(255, 165, 0))
                socket.setPos(0, y_pos)
                self.sockets[i] = socket
                
                # Store the initial value for this input
                self.input_values[i] = {'label': label, 'value': row_data.get('default_value')}

                # If a default value is provided, create an editable field
                if 'default_value' in row_data:
                    self._create_proxy_widget(i, row_data, y_pos, self._update_input_value)

            elif row_type == ROW_TYPE_OUTPUT:
                socket = NLDPSocket(parent=self)
                socket.set_properties(SOCKET_TYPE_OUTPUT, label, QColor(255, 165, 0))
                socket.setPos(self.width, y_pos)
                self.sockets[i] = socket
                # Initialize the output value
                self.output_values[i] = {'label': label, 'value': None}
            
            elif row_type == ROW_TYPE_STATIC_FIELD:
                self.static_fields[i] = {'label': label, 'value': row_data.get('default_value', '')}
                self._create_proxy_widget(i, row_data, y_pos, self._update_static_field_value)

    def _create_proxy_widget(self, index, row_data, y_pos, update_callback):
        """
        Creates and positions a QLineEdit proxy widget for a given row.
        """
        line_edit = QLineEdit(str(row_data.get('default_value', '')))
        line_edit.setStyleSheet("QLineEdit { background-color: #444; color: #eee; border: 1px solid #555; }")
        
        proxy_widget = QGraphicsProxyWidget(self)
        proxy_widget.setWidget(line_edit)
        
        field_width = self.width / 2 - 12
        proxy_widget.setGeometry(QRectF(self.width - field_width - 8, y_pos - 10, field_width, 20))

        line_edit.textChanged.connect(lambda text, i=index: update_callback(i, text))

    def _update_static_field_value(self, index, text):
        """
        Updates the internal data model for a static field.
        """
        self.static_fields[index]['value'] = text
        
    def _update_input_value(self, index, text):
        """
        Updates the internal data model for an input field.
        """
        self.input_values[index]['value'] = text

    def get_all_sockets(self):
        """
        Returns a list of all socket objects on this node.
        """
        return list(self.sockets.values())

    def get_output_sockets(self):
        """
        Returns a list of all output sockets on this node.
        """
        return [s for s in self.sockets.values() if s.socket_type == SOCKET_TYPE_OUTPUT]

    def boundingRect(self):
        """
        Returns the bounding rectangle, expanded to include sockets.
        """
        margin = self.pen_border_selected.width() / 2
        socket_radius = 5.0 
        return QRectF(0 - margin - socket_radius, 0 - margin - socket_radius,
                      self.width + (margin + socket_radius) * 2,
                      self.height + (margin + socket_radius) * 2)

    def paint(self, painter, option, widget=None):
        """
        Draws the node body, title, labels, and fields.
        Sockets and proxy widgets are child items and draw themselves.
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
        title_rounded_path = QPainterPath()
        title_rounded_path.addRoundedRect(QRectF(0, 0, self.width, self.title_bar_height), self.corner_radius, self.corner_radius)
        painter.drawPath(title_rounded_path)
        unrounder_rect = QRectF(0, self.corner_radius, self.width, self.title_bar_height - self.corner_radius)
        painter.drawRect(unrounder_rect)

        # --- Title Text ---
        painter.setPen(self.color_title_text)
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        text_padding = 8
        text_rect = QRectF(text_padding, 0, self.width - text_padding, self.title_bar_height)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title)

        # --- Draw Row Labels ---
        painter.setPen(self.color_label_text)
        font.setPointSize(9)
        painter.setFont(font)
        
        for i, row_data in enumerate(self.layout):
            y_pos = self.title_bar_height + (i * self.grid_size)
            row_rect = QRectF(0, y_pos, self.width, self.grid_size)
            label = row_data.get('label', '')

            if row_data['type'] == ROW_TYPE_INPUT:
                painter.drawText(row_rect.adjusted(12, 0, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            
            elif row_data['type'] == ROW_TYPE_OUTPUT:
                painter.drawText(row_rect.adjusted(0, 0, -12, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

            elif row_data['type'] == ROW_TYPE_STATIC_FIELD:
                painter.drawText(row_rect.adjusted(12, 0, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

        # --- Border ---
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
            for socket in self.get_all_sockets():
                for connection in socket.connections:
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
        Handles right-click events to show the appropriate context menu.
        """
        menu = QMenu(self)
        
        # --- Menu Styling ---
        menu_stylesheet = """
            QMenu {
                background-color: #d98c00;
                color: white;
                border: 0;
                margin: 2px;
            }
            QMenu::pane {
                border: 0;
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
        
        if self._spacebar_pressed:
            # --- Editor Actions Menu ---
            file_menu = menu.addMenu("File")
            new_action = file_menu.addAction("New")
            exit_action = file_menu.addAction("Exit")
            
            action = menu.exec(event.globalPos())

            self._spacebar_pressed = False

            if action == new_action:
                self.scene().clear()
            elif action == exit_action:
                QApplication.instance().quit()

        elif event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            # --- Contextual Actions Menu ---
            item_under_cursor = self.itemAt(event.pos())
            node_under_cursor = None
            if isinstance(item_under_cursor, NLDPNode):
                node_under_cursor = item_under_cursor
            elif isinstance(item_under_cursor, NLDPSocket):
                node_under_cursor = item_under_cursor.parentItem()

            if node_under_cursor:
                delete_action = menu.addAction("Delete Node(s)")
                action = menu.exec(event.globalPos())
                if action == delete_action:
                    self._delete_selected_items()
            else:
                placeholder_action = menu.addAction("Placeholder Action")
                menu.exec(event.globalPos())

        else:
            # --- Add Node Menu (using the new layout system) ---
            scene_pos = self.mapToScene(event.pos())
            
            test_menu = menu.addMenu("Test")
            
            # Define layouts for the test nodes
            layout1 = [{'type': ROW_TYPE_INPUT, 'label': 'In A'},
                       {'type': ROW_TYPE_INPUT, 'label': 'In B'},
                       {'type': ROW_TYPE_OUTPUT, 'label': 'Out'}]
            node1_action = test_menu.addAction("Simple I/O Node")
            
            layout2 = [{'type': ROW_TYPE_INPUT, 'label': 'Source'},
                       {'type': ROW_TYPE_STATIC_FIELD, 'label': 'Factor', 'default_value': 0.75},
                       {'type': ROW_TYPE_OUTPUT, 'label': 'Result A'},
                       {'type': ROW_TYPE_OUTPUT, 'label': 'Result B'}]
            node2_action = test_menu.addAction("Processing Node")
            
            layout3 = [{'type': ROW_TYPE_OUTPUT, 'label': 'Data'}]
            node3_action = test_menu.addAction("Output Only Node")
            
            action = menu.exec(event.globalPos())
            
            if action == node1_action:
                self.scene().addItem(NLDPNode(title="Simple I/O", layout=layout1, x=scene_pos.x(), y=scene_pos.y()))
            elif action == node2_action:
                self.scene().addItem(NLDPNode(title="Processing", layout=layout2, x=scene_pos.x(), y=scene_pos.y(), color=(20, 90, 20)))
            elif action == node3_action:
                self.scene().addItem(NLDPNode(title="Output Only", layout=layout3, x=scene_pos.x(), y=scene_pos.y(), color=(20, 20, 90)))


    def is_circular_connection(self, start_socket, end_socket):
        """
        Checks if creating a wire between two sockets would create a cycle.
        """
        output_socket = start_socket if start_socket.socket_type == SOCKET_TYPE_OUTPUT else end_socket
        input_socket = end_socket if end_socket.socket_type == SOCKET_TYPE_INPUT else start_socket
        
        start_node = output_socket.parentItem()
        end_node = input_socket.parentItem()

        nodes_to_visit = [end_node]
        visited_nodes = {end_node}

        while nodes_to_visit:
            current_node = nodes_to_visit.pop(0)
            
            if current_node == start_node:
                return True

            for socket in current_node.get_output_sockets():
                for connection in socket.connections:
                    next_node = connection.parentItem()
                    if next_node not in visited_nodes:
                        visited_nodes.add(next_node)
                        nodes_to_visit.append(next_node)
        
        return False

    def _delete_selected_items(self):
        """
        Deletes all currently selected nodes and wires from the scene.
        """
        selected_items = self.scene().selectedItems()
        if not selected_items:
            return

        wires_to_remove = set()
        nodes_to_remove = []

        for item in selected_items:
            if isinstance(item, NLDPNode):
                nodes_to_remove.append(item)
                for socket in item.get_all_sockets():
                    for connected_socket in socket.connections:
                        for scene_item in self.scene().items():
                            if isinstance(scene_item, NLDPWire):
                                if (scene_item.start_socket == socket and scene_item.end_socket == connected_socket) or \
                                   (scene_item.start_socket == connected_socket and scene_item.end_socket == socket):
                                    wires_to_remove.add(scene_item)
            elif isinstance(item, NLDPWire):
                wires_to_remove.add(item)

        for wire in wires_to_remove:
            self.scene().removeItem(wire)
        for node in nodes_to_remove:
            self.scene().removeItem(node)

    def keyPressEvent(self, event):
        """
        Tracks when the spacebar is pressed or when items are deleted.
        """
        if event.key() == Qt.Key.Key_Space:
            self._spacebar_pressed = True
        elif event.key() == Qt.Key.Key_Delete:
            self._delete_selected_items()
        
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
                item_to_select.setSelected(not item_to_select.isSelected())
                event.accept()
                return
        
        if event.button() == Qt.MouseButton.LeftButton:
            # --- Rubber Band Selection ---
            self.setCursor(Qt.CursorShape.CrossCursor)
            super().mousePressEvent(event)
        
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
            self.drawing_wire.hide()
            end_item = self.itemAt(event.position().toPoint())
            
            is_valid_target = isinstance(end_item, NLDPSocket) and self.start_socket != end_item
            is_valid_type = is_valid_target and self.start_socket.socket_type != end_item.socket_type
            is_not_circular = is_valid_type and not self.is_circular_connection(self.start_socket, end_item)

            if is_valid_target and is_valid_type and is_not_circular:
                
                input_socket = end_item if end_item.socket_type == SOCKET_TYPE_INPUT else self.start_socket
                
                if input_socket.connections:
                    old_partner_socket = input_socket.connections[0]
                    for item in self.scene().items():
                        if isinstance(item, NLDPWire) and \
                           ((item.start_socket == input_socket and item.end_socket == old_partner_socket) or \
                            (item.start_socket == old_partner_socket and item.end_socket == input_socket)):
                            self.scene().removeItem(item)
                            break
                
                wire = NLDPWire(self.start_socket, end_item)
                self.scene().addItem(wire)

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




if __name__ == "__main__":
    # --- Application Setup ---
    app = QApplication(sys.argv)

    # --- Create and Show Window ---
    window = NLDPWindow()
    window.show()

    # --- Start Event Loop ---
    sys.exit(app.exec())
