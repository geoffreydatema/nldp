from PySide6.QtWidgets import QGraphicsItem, QStyle, QLineEdit, QGraphicsProxyWidget
from PySide6.QtGui import QColor, QPen, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF
from . import constants, NLDPWire, NLDPSocket

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

            if row_type == constants.ROW_TYPE_INPUT:
                socket = NLDPSocket(parent=self)
                socket.set_properties(constants.SOCKET_TYPE_INPUT, label, QColor(255, 165, 0))
                socket.setPos(0, y_pos)
                self.sockets[i] = socket
                
                # Store the initial value for this input
                self.input_values[i] = {'label': label, 'value': row_data.get('default_value')}

                # If a default value is provided, create an editable field
                if 'default_value' in row_data:
                    self._create_proxy_widget(i, row_data, y_pos, self._update_input_value)

            elif row_type == constants.ROW_TYPE_OUTPUT:
                socket = NLDPSocket(parent=self)
                socket.set_properties(constants.SOCKET_TYPE_OUTPUT, label, QColor(255, 165, 0))
                socket.setPos(self.width, y_pos)
                self.sockets[i] = socket
                # Initialize the output value
                self.output_values[i] = {'label': label, 'value': None}
            
            elif row_type == constants.ROW_TYPE_STATIC_FIELD:
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
        return [s for s in self.sockets.values() if s.socket_type == constants.SOCKET_TYPE_OUTPUT]

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

            if row_data['type'] == constants.ROW_TYPE_INPUT:
                painter.drawText(row_rect.adjusted(12, 0, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            
            elif row_data['type'] == constants.ROW_TYPE_OUTPUT:
                painter.drawText(row_rect.adjusted(0, 0, -12, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

            elif row_data['type'] == constants.ROW_TYPE_STATIC_FIELD:
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
