from PyQt6.QtWidgets import (QHeaderView, QMenu, QCheckBox, QWidgetAction, 
                           QWidget, QVBoxLayout, QLineEdit, QHBoxLayout, QPushButton, QTableWidget, QMessageBox)
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QColor, QFont, QPolygon, QPainterPath, QBrush

class FilterHeader(QHeaderView):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.filter_buttons = []
        self.active_filters = {}  # Track active filters for each column
        self.columns_with_bars = set()  # Track which columns show bar charts
        self.bar_delegates = {}  # Store delegates for columns with bars
        self.setSectionsClickable(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_header_context_menu)
        self.main_window = None  # Store reference to main window
        self.filter_icon_color = QColor("#3498DB")  # Bright blue color for filter icon

    def toggle_bar_chart(self, column_index):
        """Toggle bar chart visualization for a column"""
        table = self.parent()
        if not table:
            return

        if column_index in self.columns_with_bars:
            # Remove bars
            self.columns_with_bars.remove(column_index)
            if column_index in self.bar_delegates:
                table.setItemDelegateForColumn(column_index, None)
                del self.bar_delegates[column_index]
        else:
            # Add bars
            self.columns_with_bars.add(column_index)
            
            # Get all values for normalization
            values = []
            for row in range(table.rowCount()):
                item = table.item(row, column_index)
                if item:
                    try:
                        value = float(item.text().replace(',', ''))
                        values.append(value)
                    except ValueError:
                        continue

            if not values:
                return

            # Calculate min and max for normalization
            min_val = min(values)
            max_val = max(values)
            
            # Import BarChartDelegate here to avoid circular imports
            from sqlshell.ui.bar_chart_delegate import BarChartDelegate
            
            # Create and set up delegate
            delegate = BarChartDelegate(table)
            delegate.set_range(min_val, max_val)
            self.bar_delegates[column_index] = delegate
            table.setItemDelegateForColumn(column_index, delegate)

        # Update the view
        table.viewport().update()

    def show_header_context_menu(self, pos):
        """Show context menu for header section"""
        logical_index = self.logicalIndexAt(pos)
        if logical_index < 0:
            return

        # Create context menu
        context_menu = QMenu(self)
        context_menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #BDC3C7;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #3498DB;
                color: white;
            }
        """)

        # Add sort actions
        sort_asc_action = context_menu.addAction("Sort Ascending")
        sort_desc_action = context_menu.addAction("Sort Descending")
        context_menu.addSeparator()
        
        # Add count rows action
        count_rows_action = context_menu.addAction("Count Rows")
        
        # Add explain column action
        explain_action = context_menu.addAction("Explain Column")
        
        # Add encode text action
        encode_action = context_menu.addAction("Encode Text")
        
        context_menu.addSeparator()
        filter_action = context_menu.addAction("Filter...")
        
        # Add bar chart action if column is numeric
        table = self.parent()
        if table and table.rowCount() > 0:
            try:
                # Check if column contains numeric values
                sample_value = table.item(0, logical_index).text()
                float(sample_value.replace(',', ''))  # Try converting to float
                
                context_menu.addSeparator()
                toggle_bar_action = context_menu.addAction(
                    "Remove Bar Chart" if logical_index in self.columns_with_bars 
                    else "Add Bar Chart"
                )
            except (ValueError, AttributeError):
                toggle_bar_action = None
        else:
            toggle_bar_action = None

        # Show menu and get selected action
        action = context_menu.exec(self.mapToGlobal(pos))

        if not action:
            return

        table = self.parent()
        if not table:
            return

        if action == sort_asc_action:
            table.sortItems(logical_index, Qt.SortOrder.AscendingOrder)
        elif action == sort_desc_action:
            table.sortItems(logical_index, Qt.SortOrder.DescendingOrder)
        elif action == filter_action:
            self.show_filter_menu(logical_index)
        elif action == toggle_bar_action:
            self.toggle_bar_chart(logical_index)
        elif action == explain_action:
            # Call the explain_column method on the main window
            if self.main_window and hasattr(self.main_window, "explain_column"):
                # Get the column name from the table (if it has a current dataframe)
                current_tab = self.main_window.get_current_tab()
                if current_tab and hasattr(current_tab, "current_df") and current_tab.current_df is not None:
                    if logical_index < len(current_tab.current_df.columns):
                        column_name = current_tab.current_df.columns[logical_index]
                        self.main_window.explain_column(column_name)
        elif action == encode_action:
            # Call the encode_text method on the main window
            if self.main_window and hasattr(self.main_window, "encode_text"):
                # Get the column name from the table (if it has a current dataframe)
                current_tab = self.main_window.get_current_tab()
                if current_tab and hasattr(current_tab, "current_df") and current_tab.current_df is not None:
                    if logical_index < len(current_tab.current_df.columns):
                        column_name = current_tab.current_df.columns[logical_index]
                        self.main_window.encode_text(column_name)
        elif action == count_rows_action:
            # Get the current tab and show row count
            current_tab = self.main_window.get_current_tab()
            if current_tab and hasattr(current_tab, "current_df") and current_tab.current_df is not None:
                row_count = len(current_tab.current_df)
                QMessageBox.information(self, "Row Count", f"Total rows: {row_count:,}")

    def set_main_window(self, window):
        """Set the reference to the main window"""
        self.main_window = window
        
    def paintSection(self, painter, rect, logical_index):
        """Override paint section to add filter indicator"""
        super().paintSection(painter, rect, logical_index)
        
        if logical_index in self.active_filters:
            # Draw background highlight for filtered columns
            highlight_color = QColor(52, 152, 219, 30)  # Light blue background
            painter.fillRect(rect, highlight_color)
            
            # Make icon larger and more visible
            icon_size = min(rect.height() - 8, 24)  # Larger icon, but not too large
            margin = 6
            icon_rect = QRect(
                rect.right() - icon_size - margin,
                rect.top() + (rect.height() - icon_size) // 2,
                icon_size,
                icon_size
            )
            
            # Draw filter icon with improved visibility
            painter.save()
            
            # Set up the pen for better visibility
            pen = painter.pen()
            pen.setWidth(3)  # Thicker lines
            pen.setColor(self.filter_icon_color)
            painter.setPen(pen)
            
            # Calculate points for larger funnel shape
            points = [
                QPoint(icon_rect.left(), icon_rect.top()),
                QPoint(icon_rect.right(), icon_rect.top()),
                QPoint(icon_rect.center().x() + icon_size//3, icon_rect.center().y()),
                QPoint(icon_rect.center().x() + icon_size//3, icon_rect.bottom()),
                QPoint(icon_rect.center().x() - icon_size//3, icon_rect.bottom()),
                QPoint(icon_rect.center().x() - icon_size//3, icon_rect.center().y()),
                QPoint(icon_rect.left(), icon_rect.top())
            ]
            
            # Create and fill path
            path = QPainterPath()
            path.moveTo(float(points[0].x()), float(points[0].y()))
            for point in points[1:]:
                path.lineTo(float(point.x()), float(point.y()))
            
            # Fill with semi-transparent blue
            painter.fillPath(path, QBrush(QColor(52, 152, 219, 120)))  # More opaque fill
            
            # Draw outline
            painter.drawPolyline(QPolygon(points))
            
            # If multiple values are filtered, add a number
            if len(self.active_filters[logical_index]) > 1:
                # Draw number with better visibility
                number_rect = QRect(icon_rect.left(), icon_rect.top(),
                                  icon_rect.width(), icon_rect.height())
                painter.setFont(QFont("Arial", icon_size//2, QFont.Weight.Bold))
                
                # Draw text shadow for better contrast
                painter.setPen(QColor("white"))
                painter.drawText(number_rect.adjusted(1, 1, 1, 1),
                               Qt.AlignmentFlag.AlignCenter,
                               str(len(self.active_filters[logical_index])))
                
                # Draw main text
                painter.setPen(self.filter_icon_color)
                painter.drawText(number_rect, Qt.AlignmentFlag.AlignCenter,
                               str(len(self.active_filters[logical_index])))
            
            painter.restore()
            
            # Draw a more visible indicator at the bottom of the header section
            painter.save()
            indicator_height = 3  # Thicker indicator line
            indicator_rect = QRect(rect.left(), rect.bottom() - indicator_height,
                                 rect.width(), indicator_height)
            painter.fillRect(indicator_rect, self.filter_icon_color)
            painter.restore()
        
    def show_filter_menu(self, logical_index):
        if not self.parent() or not isinstance(self.parent(), QTableWidget):
            return
            
        table = self.parent()
        unique_values = set()
        
        # Collect unique values from the column
        for row in range(table.rowCount()):
            item = table.item(row, logical_index)
            if item and not table.isRowHidden(row):
                unique_values.add(item.text())
        
        # Create and show the filter menu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #BDC3C7;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #3498DB;
                color: white;
            }
            QCheckBox {
                padding: 5px;
            }
            QScrollArea {
                border: none;
            }
        """)
        
        # Add search box at the top
        search_widget = QWidget(menu)
        search_layout = QVBoxLayout(search_widget)
        search_edit = QLineEdit(search_widget)
        search_edit.setPlaceholderText("Search values...")
        search_layout.addWidget(search_edit)
        
        # Add action for search widget
        search_action = QWidgetAction(menu)
        search_action.setDefaultWidget(search_widget)
        menu.addAction(search_action)
        menu.addSeparator()
        
        # Add "Select All" checkbox
        select_all = QCheckBox("Select All", menu)
        select_all.setChecked(True)
        select_all_action = QWidgetAction(menu)
        select_all_action.setDefaultWidget(select_all)
        menu.addAction(select_all_action)
        menu.addSeparator()
        
        # Create scrollable area for checkboxes
        scroll_widget = QWidget(menu)
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(2)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add checkboxes for unique values
        value_checkboxes = {}
        for value in sorted(unique_values):
            checkbox = QCheckBox(str(value), scroll_widget)
            # Set checked state based on active filters
            checkbox.setChecked(logical_index not in self.active_filters or 
                              value in self.active_filters[logical_index])
            value_checkboxes[value] = checkbox
            scroll_layout.addWidget(checkbox)
        
        # Add scrollable area to menu
        scroll_action = QWidgetAction(menu)
        scroll_action.setDefaultWidget(scroll_widget)
        menu.addAction(scroll_action)
        
        # Connect search box to filter checkboxes
        def filter_checkboxes(text):
            for value, checkbox in value_checkboxes.items():
                checkbox.setVisible(text.lower() in str(value).lower())
        
        search_edit.textChanged.connect(filter_checkboxes)
        
        # Connect select all to other checkboxes
        def toggle_all(state):
            for checkbox in value_checkboxes.values():
                if not checkbox.isHidden():  # Only toggle visible checkboxes
                    checkbox.setChecked(state)
        
        select_all.stateChanged.connect(toggle_all)
        
        # Add Apply and Clear buttons
        menu.addSeparator()
        apply_button = QPushButton("Apply Filter", menu)
        apply_button.setStyleSheet("""
            QPushButton {
                background-color: #2ECC71;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #27AE60;
            }
        """)
        
        clear_button = QPushButton("Clear Filter", menu)
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        
        button_widget = QWidget(menu)
        button_layout = QHBoxLayout(button_widget)
        button_layout.addWidget(apply_button)
        button_layout.addWidget(clear_button)
        
        button_action = QWidgetAction(menu)
        button_action.setDefaultWidget(button_widget)
        menu.addAction(button_action)
        
        def apply_filter():
            # Get selected values
            selected_values = {value for value, checkbox in value_checkboxes.items() 
                             if checkbox.isChecked()}
            
            if len(selected_values) < len(unique_values):
                # Store active filter only if not all values are selected
                self.active_filters[logical_index] = selected_values
            else:
                # Remove filter if all values are selected
                self.active_filters.pop(logical_index, None)
            
            # Apply all active filters
            self.apply_all_filters(table)
            
            menu.close()
            self.updateSection(logical_index)  # Redraw section to show/hide filter icon
        
        def clear_filter():
            # Remove filter for this column
            if logical_index in self.active_filters:
                del self.active_filters[logical_index]
            
            # Apply remaining filters
            self.apply_all_filters(table)
            
            menu.close()
            self.updateSection(logical_index)  # Redraw section to hide filter icon
        
        apply_button.clicked.connect(apply_filter)
        clear_button.clicked.connect(clear_filter)
        
        # Show menu under the header section
        header_pos = self.mapToGlobal(self.geometry().bottomLeft())
        header_pos.setX(header_pos.x() + self.sectionPosition(logical_index))
        menu.exec(header_pos)
        
    def apply_all_filters(self, table):
        """Apply all active filters to the table"""
        # Show all rows first
        for row in range(table.rowCount()):
            table.setRowHidden(row, False)
        
        # Apply each active filter
        for col_idx, allowed_values in self.active_filters.items():
            for row in range(table.rowCount()):
                item = table.item(row, col_idx)
                if item and not table.isRowHidden(row):
                    table.setRowHidden(row, item.text() not in allowed_values)
        
        # Update status bar with visible row count
        if self.main_window:
            visible_rows = sum(1 for row in range(table.rowCount()) 
                             if not table.isRowHidden(row))
            total_filters = len(self.active_filters)
            filter_text = f" ({total_filters} filter{'s' if total_filters != 1 else ''} active)" if total_filters > 0 else ""
            self.main_window.statusBar().showMessage(
                f"Showing {visible_rows:,} rows{filter_text}") 