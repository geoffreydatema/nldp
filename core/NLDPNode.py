from PySide6.QtWidgets import QGraphicsItem, QStyle, QLineEdit, QGraphicsProxyWidget
from PySide6.QtGui import QColor, QPen, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF
from . import constants, NLDPWire, NLDPSocket
from .widgets import NLDPLineEditWidget, NLDPFileBrowserWidget

class NLDPNode(QGraphicsItem):
    """
    Represents a single node in the NLDP graph.
    Builds its visual layout and sockets from a structured 'layout' list.
    """
    def __init__(self, title="New Node", layout=None, show_border=False, color=None, x=0, y=0, width=8, view=None):
        """
        Initializes the node.
        """
        super().__init__()

        # --- Configuration ---
        self.grid_size = 16
        self.layout = layout if layout is not None else []
        self.width = width * self.grid_size # Default width, can be overridden later
        # Height is determined by the title bar + number of rows in the layout
        self.height = (len(self.layout) + 1) * self.grid_size
        self.title = title
        self.show_border = show_border
        self.view = view
        
        # --- Engine State ---
        self.is_dirty = True

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
        self.static_fields = {} # Now stores values for both STATIC and DYNAMIC rows
        self.output_values = {}
        self._build_from_layout()

        # --- Interaction State ---
        self._is_dragging = False
        self._drag_offset = QPointF()

        # Set flags for interaction
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setPos(x, y)

    def cook(self):
        """
        The final evaluation method that orchestrates the cooking process.
        This should not be overridden by child classes.
        """
        if not self.is_dirty:
            return

        print(f"Cooking node: {self.title}")
        
        # 1. Gather all inputs, which triggers recursive evaluation of dependencies.
        inputs = self._gather_inputs()
        
        # 2. Call the developer's custom logic.
        outputs = self.evaluate(inputs)
        
        # 3. Store the results.
        self._store_outputs(outputs)
        
        # 4. Mark the node as clean.
        self.is_dirty = False

    def evaluate(self, inputs):
        """
        The method to be overridden by developers for custom node logic.
        It receives all input values and should return a dictionary of output values.
        """
        print(f"  - Evaluating: {self.title}")
        print(f"  - Inputs: {inputs}")
        # This base method does nothing and returns an empty dictionary.
        return {}

    def _gather_inputs(self):
        """
        Gathers all input values for the node, unifying all input types
        and performing data type conversion.
        """
        gathered_inputs = {}
        for i, row_data in enumerate(self.layout):
            field_type = row_data.get('field_type')
            data_type = row_data.get('data_type')
            value = None

            if field_type in [constants.FIELD_TYPE_INPUT, constants.FIELD_TYPE_DYNAMIC]:
                socket = self.sockets.get(i)
                if socket and socket.connections:
                    upstream_socket = socket.connections[0]
                    upstream_node = upstream_socket.parentItem()
                    upstream_node.cook()
                    
                    for j, s in upstream_node.sockets.items():
                        if s == upstream_socket:
                            value = upstream_node.output_values[j]['value']
                            break
                elif field_type == constants.FIELD_TYPE_DYNAMIC:
                    value = self.static_fields[i]['value']
            
            elif field_type == constants.FIELD_TYPE_STATIC:
                value = self.static_fields[i]['value']
            
            # --- Data Type Conversion ---
            if value is not None:
                try:
                    if data_type == constants.DTYPE_INT:
                        gathered_inputs[i] = int(float(value))
                    elif data_type == constants.DTYPE_FLOAT:
                        gathered_inputs[i] = float(value)
                    elif data_type == constants.DTYPE_FILE:
                        gathered_inputs[i] = value
                    else: # Default to string
                        gathered_inputs[i] = str(value)
                except (ValueError, TypeError):
                    gathered_inputs[i] = None # Conversion failed
            else:
                gathered_inputs[i] = None

        return gathered_inputs

    def _store_outputs(self, outputs):
        """
        Stores the computed output values in the node's data model.
        """
        for i, value in outputs.items():
            if i in self.output_values:
                self.output_values[i]['value'] = value

    def mark_dirty(self):
        """
        Marks this node as dirty and propagates the dirty state downstream.
        """
        if self.is_dirty:
            return
        
        self.is_dirty = True
        
        for socket in self.get_output_sockets():
            for connection in socket.connections:
                downstream_node = connection.parentItem()
                downstream_node.mark_dirty()

    def _build_from_layout(self):
        """
        Creates sockets and UI fields based on the layout definition.
        """
        for i, row_data in enumerate(self.layout):
            field_type = row_data.get('field_type')
            label = row_data.get('label', '')
            data_type = row_data.get('data_type')
            y_pos = self.title_bar_height + (i * self.grid_size) + (self.grid_size / 2)

            if field_type == constants.FIELD_TYPE_INPUT:
                socket = NLDPSocket(parent=self)
                socket.set_properties(constants.SOCKET_TYPE_INPUT, label, data_type)
                socket.setPos(0, y_pos)
                self.sockets[i] = socket

            elif field_type == constants.FIELD_TYPE_DYNAMIC:
                socket = NLDPSocket(parent=self)
                socket.set_properties(constants.SOCKET_TYPE_INPUT, label, data_type)
                socket.setPos(0, y_pos)
                self.sockets[i] = socket
                self.static_fields[i] = {'label': label, 'value': row_data.get('default_value')}
                self._create_proxy_widget(i, row_data, y_pos, self._update_static_field_value)

            elif field_type == constants.FIELD_TYPE_OUTPUT:
                socket = NLDPSocket(parent=self)
                socket.set_properties(constants.SOCKET_TYPE_OUTPUT, label, data_type)
                socket.setPos(self.width, y_pos)
                self.sockets[i] = socket
                self.output_values[i] = {'label': label, 'value': None}
            
            elif field_type == constants.FIELD_TYPE_STATIC:
                self.static_fields[i] = {'label': label, 'value': row_data.get('default_value', '')}
                self._create_proxy_widget(i, row_data, y_pos, self._update_static_field_value)
            
            elif field_type == 'custom_widget':
                self._create_proxy_widget(i, row_data, y_pos)

    def _create_proxy_widget(self, index, row_data, y_pos, update_callback=None):
        """
        Creates and positions a proxy widget based on the layout definition.
        """
        widget_type = row_data.get('widget_type')
        widget = row_data.get('widget') # Check for a pre-made widget
        
        if widget is None and widget_type == constants.WIDGET_LINEEDIT:
            widget = NLDPLineEditWidget(default_value=row_data.get('default_value', ''), data_type=row_data.get('data_type'))
            widget.textChanged.connect(lambda text, i=index: update_callback(i, text))
            if self.view:
                widget.editingFinished.connect(self.view.cook_graph)

        elif widget is None and widget_type == constants.WIDGET_FILE_BROWSER:
            widget = NLDPFileBrowserWidget(view=self.view)
            widget.setText(str(row_data.get('default_value', '')))
            widget.textChanged().connect(lambda text, i=index: update_callback(i, text))
            if self.view:
                widget.path_selected.connect(self.view.cook_graph)
                widget.line_edit.editingFinished.connect(self.view.cook_graph)

        if widget:
            proxy_widget = QGraphicsProxyWidget(self)
            proxy_widget.setWidget(widget)
            
            field_width = self.width / 2
            widget.setFixedHeight(15)
            proxy_widget.setGeometry(QRectF(self.width - field_width, y_pos - 7, field_width - 8, 15))

    def _update_static_field_value(self, index, text):
        """
        Updates the internal data model for a static or dynamic field and marks the node as dirty.
        """
        self.static_fields[index]['value'] = text
        self.mark_dirty()

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
        font.setPointSize(8) # Smaller font for labels
        painter.setFont(font)
        
        for i, row_data in enumerate(self.layout):
            y_pos = self.title_bar_height + (i * self.grid_size)
            row_rect = QRectF(0, y_pos, self.width, self.grid_size)
            label = row_data.get('label', '')

            if row_data['field_type'] in [constants.FIELD_TYPE_INPUT, constants.FIELD_TYPE_DYNAMIC]:
                painter.drawText(row_rect.adjusted(12, 0, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            
            elif row_data['field_type'] == constants.FIELD_TYPE_OUTPUT:
                painter.drawText(row_rect.adjusted(0, 0, -12, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

            elif row_data['field_type'] == constants.FIELD_TYPE_STATIC:
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
            is_alt_move = (view is not None and
                             hasattr(view, '_backtick_pressed') and
                             view._backtick_pressed)

            if is_title_bar_click or is_alt_move:
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
        super().mouseReleaseEvent(event)
