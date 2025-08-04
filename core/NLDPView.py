from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsPathItem, QMenu
from PySide6.QtGui import QColor, QPainter, QPen, QPainterPath, QCursor
from PySide6.QtCore import Qt, QRectF, QLineF, QPoint, QPointF, QEvent
from . import constants, NLDPNode, NLDPWire, NLDPSocket
from standard import NLDPInputFloatNode, NLDPOutputOutputNode, NLDPMathAddNode

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
        self._ignore_next_context_menu = False
        self._last_pan_point = QPoint()
        self._last_zoom_point = QPoint()
        self._zoom_scene_anchor = QPointF()
        
        # --- Wire Drawing State ---
        self.drawing_wire = None
        self.start_socket = None

        # --- Keyboard State ---
        self._backtick_pressed = False # For alternate node moving
        
        # --- Menu State ---
        self._editor_menu = None

        # --- Zoom Limits ---
        self.MIN_ZOOM = 0.2
        self.MAX_ZOOM = 5.0

        # Default anchor is under the mouse, for wheel-based zooming.
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def _on_editor_menu_closed(self):
        """
        Ensures the menu state is cleaned up whenever the menu is closed.
        """
        if self._editor_menu:
            self._install_menu_event_filter(self._editor_menu, remove=True)
            self._editor_menu = None

    def _install_menu_event_filter(self, menu, remove=False):
        """
        Recursively installs or removes the event filter on a menu and all its submenus.
        """
        if remove:
            menu.removeEventFilter(self)
        else:
            menu.installEventFilter(self)
        
        for action in menu.actions():
            if action.menu():
                self._install_menu_event_filter(action.menu(), remove=remove)

    def eventFilter(self, watched, event):
        """
        Filters events for the editor menu to catch the spacebar release.
        """
        if isinstance(watched, QMenu) and event.type() == QEvent.Type.KeyRelease and \
           event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            
            if self._editor_menu:
                action = self._editor_menu.activeAction()
                self._editor_menu.close()
                
                if action and not action.menu(): # Only trigger if it's not a submenu
                    action.trigger()

            return True # Event was handled
        return super().eventFilter(watched, event)

    def contextMenuEvent(self, event):
        """
        Handles right-click events to show the appropriate context menu.
        """
        if self._ignore_next_context_menu:
            self._ignore_next_context_menu = False
            event.accept()
            return

        menu = QMenu(self)
        
        # --- Menu Styling ---
        menu_stylesheet = """
            QMenu {
                background-color: #d98c00;
                color: white;
                border: 0;
                margin: 4px;
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
        
        if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            # --- Contextual Actions Menu ---
            item_under_cursor = self.itemAt(event.pos())
            node_under_cursor = None
            if isinstance(item_under_cursor, NLDPNode):
                node_under_cursor = item_under_cursor
            elif isinstance(item_under_cursor, NLDPSocket):
                node_under_cursor = item_under_cursor.parentItem()

            if node_under_cursor:
                self.scene().clearSelection()
                node_under_cursor.setSelected(True)

                evaluate_action = menu.addAction("Evaluate")
                read_values_action = menu.addAction("Read Values")
                delete_action = menu.addAction("Delete Node(s)")
                
                action = menu.exec(event.globalPos())
                
                if action == delete_action:
                    self._delete_selected_items()
                elif action == evaluate_action:
                    self._evaluate_graph()
                elif action == read_values_action:
                    print(f"--- Reading Values for: {node_under_cursor.title} ---")
                    print("Static Fields:", node_under_cursor.static_fields)
                    print("Output Values:", node_under_cursor.output_values)
                    if hasattr(node_under_cursor, 'dead_end_values'):
                        print("Dead-End Values:", node_under_cursor.dead_end_values)
                    print("---------------------------------------")
            else:
                placeholder_action = menu.addAction("Placeholder Action")
                menu.exec(event.globalPos())

        else:
            # --- Add Node Menu (using the new layout system) ---
            scene_pos = self.mapToScene(event.pos())
    
            input_menu = menu.addMenu("Input")
            output_menu = menu.addMenu("Output")
            math_menu = menu.addMenu("Math")
            
            value_node_action = input_menu.addAction("Value")
            output_node_action = output_menu.addAction("Output")
            add_node_action = math_menu.addAction("Add")
            
            action = menu.exec(event.globalPos())
            
            if action == value_node_action:
                self.scene().addItem(NLDPInputFloatNode(x=scene_pos.x(), y=scene_pos.y()))
            elif action == output_node_action:
                self.scene().addItem(NLDPOutputOutputNode(x=scene_pos.x(), y=scene_pos.y()))
            elif action == add_node_action:
                self.scene().addItem(NLDPMathAddNode(x=scene_pos.x(), y=scene_pos.y()))

    def _evaluate_graph(self):
        """
        Initiates the evaluation of the selected node using the dirty-flag system.
        """
        selected_nodes = [item for item in self.scene().selectedItems() if isinstance(item, NLDPNode)]
        if not selected_nodes:
            print("No node selected to evaluate.")
            return
        
        target_node = selected_nodes[0]
        
        print("\n--- Starting Evaluation ---")
        # The recursive pull system handles the evaluation order automatically.
        target_node.cook()
        
        print(f"\nFinal output of '{target_node.title}':")
        if hasattr(target_node, 'dead_end_values'):
             print(f"Result: {target_node.dead_end_values}")
        else:
            print("Output values:", target_node.output_values)
        print("-------------------------\n")

    def is_circular_connection(self, start_socket, end_socket):
        """
        Checks if creating a wire between two sockets would create a cycle.
        """
        output_socket = start_socket if start_socket.socket_type == constants.SOCKET_TYPE_OUTPUT else end_socket
        input_socket = end_socket if end_socket.socket_type == constants.SOCKET_TYPE_INPUT else start_socket
        
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
        Tracks key presses for various editor actions.
        """
        if event.key() == Qt.Key.Key_QuoteLeft: # Backtick key
            self._backtick_pressed = True
        elif event.key() == Qt.Key.Key_Delete:
            self._delete_selected_items()
        elif event.key() == Qt.Key.Key_Space and not event.isAutoRepeat() and self._editor_menu is None:
            # --- Show Editor Menu ---
            self._editor_menu = QMenu(self)
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
            self._editor_menu.setStyleSheet(menu_stylesheet)
            self._editor_menu.aboutToHide.connect(self._on_editor_menu_closed)
            
            file_menu = self._editor_menu.addMenu("File")
            new_action = file_menu.addAction("New")
            exit_action = file_menu.addAction("Exit")
            
            new_action.triggered.connect(self.scene().clear)
            exit_action.triggered.connect(QApplication.instance().quit)
            
            self._install_menu_event_filter(self._editor_menu) # Recursively install filter
            self._editor_menu.popup(QCursor.pos())
        
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """
        Tracks key releases for various editor actions.
        """
        if event.key() == Qt.Key.Key_QuoteLeft and not event.isAutoRepeat(): # Backtick key
            self._backtick_pressed = False
        elif event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            if self._editor_menu:
                # The event filter will handle the action, but we still need to close the menu
                self._editor_menu.close()
        
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
            self._ignore_next_context_menu = True # Set the flag to prevent menu on release
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
                
                input_socket = end_item if end_item.socket_type == constants.SOCKET_TYPE_INPUT else self.start_socket
                
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
                
                # Mark the downstream node as dirty
                input_socket.parentItem().mark_dirty()

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
