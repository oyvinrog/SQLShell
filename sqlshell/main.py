import sys
import os
import json

# Ensure proper path setup for resources when running directly
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

import duckdb
import sqlite3
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTextEdit, QPushButton, QFileDialog,
                           QLabel, QSplitter, QListWidget, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox, QPlainTextEdit,
                           QCompleter, QFrame, QToolButton, QSizePolicy, QTabWidget,
                           QStyleFactory, QToolBar, QStatusBar, QLineEdit, QMenu,
                           QCheckBox, QWidgetAction, QMenuBar, QInputDialog,
                           QStyledItemDelegate)
from PyQt6.QtCore import Qt, QAbstractTableModel, QRegularExpression, QRect, QSize, QStringListModel, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat, QPainter, QTextFormat, QTextCursor, QIcon, QPalette, QLinearGradient, QBrush, QPixmap, QPolygon, QPainterPath
import numpy as np
from datetime import datetime

from sqlshell import create_test_data
from sqlshell.splash_screen import AnimatedSplashScreen
from sqlshell.syntax_highlighter import SQLSyntaxHighlighter
from sqlshell.editor import LineNumberArea, SQLEditor

class BarChartDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.min_val = 0
        self.max_val = 1
        self.bar_color = QColor("#3498DB")

    def set_range(self, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val

    def paint(self, painter, option, index):
        # Draw the default background
        super().paint(painter, option, index)
        
        try:
            text = index.data()
            value = float(text.replace(',', ''))
            
            # Calculate normalized value
            range_val = self.max_val - self.min_val if self.max_val != self.min_val else 1
            normalized = (value - self.min_val) / range_val
            
            # Define bar dimensions
            bar_height = 16
            max_bar_width = 100
            bar_width = max(5, int(max_bar_width * normalized))
            
            # Calculate positions
            text_width = option.fontMetrics.horizontalAdvance(text) + 10
            bar_x = option.rect.left() + text_width + 10
            bar_y = option.rect.center().y() - bar_height // 2
            
            # Draw the bar
            bar_rect = QRect(bar_x, bar_y, bar_width, bar_height)
            painter.fillRect(bar_rect, self.bar_color)
            
            # Draw the text
            text_rect = QRect(option.rect.left() + 4, option.rect.top(),
                            text_width, option.rect.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            
        except (ValueError, AttributeError):
            # If not a number, just draw the text
            super().paint(painter, option, index)

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

class SQLShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.conn = None
        self.current_connection_type = None
        self.loaded_tables = {}  # Keep track of loaded tables
        self.table_columns = {}  # Keep track of table columns
        self.current_df = None  # Store the current DataFrame for filtering
        self.filter_widgets = []  # Store filter line edits
        self.current_project_file = None  # Store the current project file path
        
        # Define color scheme
        self.colors = {
            'primary': "#2C3E50",       # Dark blue-gray
            'secondary': "#3498DB",     # Bright blue
            'accent': "#1ABC9C",        # Teal
            'background': "#ECF0F1",    # Light gray
            'text': "#2C3E50",          # Dark blue-gray
            'text_light': "#7F8C8D",    # Medium gray
            'success': "#2ECC71",       # Green
            'warning': "#F39C12",       # Orange
            'error': "#E74C3C",         # Red
            'dark_bg': "#34495E",       # Darker blue-gray
            'light_bg': "#F5F5F5",      # Very light gray
            'border': "#BDC3C7"         # Light gray border
        }
        
        self.init_ui()
        self.apply_stylesheet()

    def apply_stylesheet(self):
        """Apply custom stylesheet to the application"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['background']};
            }}
            
            QWidget {{
                color: {self.colors['text']};
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }}
            
            QLabel {{
                font-size: 13px;
                padding: 2px;
            }}
            
            QLabel#header_label {{
                font-size: 16px;
                font-weight: bold;
                color: {self.colors['primary']};
                padding: 8px 0;
            }}
            
            QPushButton {{
                background-color: {self.colors['secondary']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
                min-height: 30px;
            }}
            
            QPushButton:hover {{
                background-color: #2980B9;
            }}
            
            QPushButton:pressed {{
                background-color: #1F618D;
            }}
            
            QPushButton#primary_button {{
                background-color: {self.colors['accent']};
            }}
            
            QPushButton#primary_button:hover {{
                background-color: #16A085;
            }}
            
            QPushButton#primary_button:pressed {{
                background-color: #0E6655;
            }}
            
            QPushButton#danger_button {{
                background-color: {self.colors['error']};
            }}
            
            QPushButton#danger_button:hover {{
                background-color: #CB4335;
            }}
            
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
            
            QToolButton:hover {{
                background-color: rgba(52, 152, 219, 0.2);
            }}
            
            QFrame#sidebar {{
                background-color: {self.colors['primary']};
                border-radius: 0px;
            }}
            
            QFrame#content_panel {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid {self.colors['border']};
            }}
            
            QListWidget {{
                background-color: white;
                border-radius: 4px;
                border: 1px solid {self.colors['border']};
                padding: 4px;
                outline: none;
            }}
            
            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
            }}
            
            QListWidget::item:selected {{
                background-color: {self.colors['secondary']};
                color: white;
            }}
            
            QListWidget::item:hover:!selected {{
                background-color: #E3F2FD;
            }}
            
            QTableWidget {{
                background-color: white;
                alternate-background-color: #F8F9FA;
                border-radius: 4px;
                border: 1px solid {self.colors['border']};
                gridline-color: #E0E0E0;
                outline: none;
            }}
            
            QTableWidget::item {{
                padding: 4px;
            }}
            
            QTableWidget::item:selected {{
                background-color: rgba(52, 152, 219, 0.2);
                color: {self.colors['text']};
            }}
            
            QHeaderView::section {{
                background-color: {self.colors['primary']};
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
            
            QSplitter::handle {{
                background-color: {self.colors['border']};
            }}
            
            QStatusBar {{
                background-color: {self.colors['primary']};
                color: white;
                padding: 8px;
            }}
            
            QPlainTextEdit, QTextEdit {{
                background-color: white;
                border-radius: 4px;
                border: 1px solid {self.colors['border']};
                padding: 8px;
                selection-background-color: #BBDEFB;
                selection-color: {self.colors['text']};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
            }}
        """)

    def init_ui(self):
        self.setWindowTitle('SQL Shell')
        self.setGeometry(100, 100, 1400, 800)
        
        # Create menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        
        # Project management actions
        new_project_action = file_menu.addAction('New Project')
        new_project_action.setShortcut('Ctrl+N')
        new_project_action.triggered.connect(self.new_project)
        
        open_project_action = file_menu.addAction('Open Project...')
        open_project_action.setShortcut('Ctrl+O')
        open_project_action.triggered.connect(self.open_project)
        
        save_project_action = file_menu.addAction('Save Project')
        save_project_action.setShortcut('Ctrl+S')
        save_project_action.triggered.connect(self.save_project)
        
        save_project_as_action = file_menu.addAction('Save Project As...')
        save_project_as_action.setShortcut('Ctrl+Shift+S')
        save_project_as_action.triggered.connect(self.save_project_as)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('Exit')
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        
        # Create custom status bar
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left panel for table list
        left_panel = QFrame()
        left_panel.setObjectName("sidebar")
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)
        
        # Database info section
        db_header = QLabel("DATABASE")
        db_header.setObjectName("header_label")
        db_header.setStyleSheet("color: white;")
        left_layout.addWidget(db_header)
        
        self.db_info_label = QLabel("No database connected")
        self.db_info_label.setStyleSheet("color: white; background-color: rgba(255, 255, 255, 0.1); padding: 8px; border-radius: 4px;")
        left_layout.addWidget(self.db_info_label)
        
        # Database action buttons
        db_buttons_layout = QHBoxLayout()
        db_buttons_layout.setSpacing(8)
        
        self.open_db_btn = QPushButton('Open Database')
        self.open_db_btn.setIcon(QIcon.fromTheme("document-open"))
        self.open_db_btn.clicked.connect(self.open_database)
        
        self.test_btn = QPushButton('Load Test Data')
        self.test_btn.clicked.connect(self.load_test_data)
        
        db_buttons_layout.addWidget(self.open_db_btn)
        db_buttons_layout.addWidget(self.test_btn)
        left_layout.addLayout(db_buttons_layout)
        
        # Tables section
        tables_header = QLabel("TABLES")
        tables_header.setObjectName("header_label")
        tables_header.setStyleSheet("color: white; margin-top: 16px;")
        left_layout.addWidget(tables_header)
        
        # Table actions
        table_actions_layout = QHBoxLayout()
        table_actions_layout.setSpacing(8)
        
        self.browse_btn = QPushButton('Load Files')
        self.browse_btn.setIcon(QIcon.fromTheme("document-new"))
        self.browse_btn.clicked.connect(self.browse_files)
        
        self.remove_table_btn = QPushButton('Remove')
        self.remove_table_btn.setObjectName("danger_button")
        self.remove_table_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_table_btn.clicked.connect(self.remove_selected_table)
        
        table_actions_layout.addWidget(self.browse_btn)
        table_actions_layout.addWidget(self.remove_table_btn)
        left_layout.addLayout(table_actions_layout)
        
        # Tables list with custom styling
        self.tables_list = QListWidget()
        self.tables_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 4px;
                color: white;
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QListWidget::item:hover:!selected {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.tables_list.itemClicked.connect(self.show_table_preview)
        self.tables_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tables_list.customContextMenuRequested.connect(self.show_tables_context_menu)
        left_layout.addWidget(self.tables_list)
        
        # Add spacer at the bottom
        left_layout.addStretch()
        
        # Right panel for query and results
        right_panel = QFrame()
        right_panel.setObjectName("content_panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(16)
        
        # Query section header
        query_header = QLabel("SQL QUERY")
        query_header.setObjectName("header_label")
        right_layout.addWidget(query_header)
        
        # Create splitter for query and results
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(8)
        splitter.setChildrenCollapsible(False)
        
        # Top part - Query section
        query_widget = QFrame()
        query_widget.setObjectName("content_panel")
        query_layout = QVBoxLayout(query_widget)
        query_layout.setContentsMargins(16, 16, 16, 16)
        query_layout.setSpacing(12)
        
        # Query input
        self.query_edit = SQLEditor()
        # Apply syntax highlighting to the query editor
        self.sql_highlighter = SQLSyntaxHighlighter(self.query_edit.document())
        query_layout.addWidget(self.query_edit)
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.execute_btn = QPushButton('Execute Query')
        self.execute_btn.setObjectName("primary_button")
        self.execute_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.execute_btn.clicked.connect(self.execute_query)
        self.execute_btn.setToolTip("Execute Query (Ctrl+Enter)")
        
        self.clear_btn = QPushButton('Clear')
        self.clear_btn.setIcon(QIcon.fromTheme("edit-clear"))
        self.clear_btn.clicked.connect(self.clear_query)
        
        button_layout.addWidget(self.execute_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        query_layout.addLayout(button_layout)
        
        # Bottom part - Results section
        results_widget = QFrame()
        results_widget.setObjectName("content_panel")
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(16, 16, 16, 16)
        results_layout.setSpacing(12)
        
        # Results header with row count and export options
        results_header_layout = QHBoxLayout()
        
        results_title = QLabel("RESULTS")
        results_title.setObjectName("header_label")
        
        self.row_count_label = QLabel("")
        self.row_count_label.setStyleSheet(f"color: {self.colors['text_light']}; font-style: italic;")
        
        results_header_layout.addWidget(results_title)
        results_header_layout.addWidget(self.row_count_label)
        results_header_layout.addStretch()
        
        # Export buttons
        export_layout = QHBoxLayout()
        export_layout.setSpacing(8)
        
        self.export_excel_btn = QPushButton('Export to Excel')
        self.export_excel_btn.setIcon(QIcon.fromTheme("x-office-spreadsheet"))
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        
        self.export_parquet_btn = QPushButton('Export to Parquet')
        self.export_parquet_btn.setIcon(QIcon.fromTheme("document-save"))
        self.export_parquet_btn.clicked.connect(self.export_to_parquet)
        
        export_layout.addWidget(self.export_excel_btn)
        export_layout.addWidget(self.export_parquet_btn)
        
        results_header_layout.addLayout(export_layout)
        results_layout.addLayout(results_header_layout)
        
        # Table widget for results with modern styling
        self.results_table = QTableWidget()
        self.results_table.setSortingEnabled(True)
        self.results_table.setAlternatingRowColors(True)
        
        # Set custom header for filtering
        header = FilterHeader(self.results_table)
        header.set_main_window(self)  # Set reference to main window
        self.results_table.setHorizontalHeader(header)
        header.setStretchLastSection(True)
        header.setSectionsMovable(True)
        
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setShowGrid(True)
        self.results_table.setGridStyle(Qt.PenStyle.SolidLine)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        results_layout.addWidget(self.results_table)

        # Add widgets to splitter
        splitter.addWidget(query_widget)
        splitter.addWidget(results_widget)
        
        # Set initial sizes for splitter
        splitter.setSizes([300, 500])
        
        right_layout.addWidget(splitter)

        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 4)

        # Status bar
        self.statusBar().showMessage('Ready | Ctrl+Enter: Execute Query | Ctrl+K: Toggle Comment')
        
        # Show keyboard shortcuts in a tooltip for the query editor
        self.query_edit.setToolTip(
            "Keyboard Shortcuts:\n"
            "Ctrl+Enter: Execute Query\n"
            "Ctrl+K: Toggle Comment\n"
            "Tab: Insert 4 spaces\n"
            "Ctrl+Space: Show autocomplete"
        )

    def populate_table(self, df):
        """Populate the results table with DataFrame data using memory-efficient chunking"""
        try:
            # Store the current DataFrame for filtering
            self.current_df = df.copy()
            
            # Remember which columns had bar charts
            header = self.results_table.horizontalHeader()
            if isinstance(header, FilterHeader):
                columns_with_bars = header.columns_with_bars.copy()
            else:
                columns_with_bars = set()
            
            # Clear existing data
            self.results_table.clearContents()
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(0)
            
            if df.empty:
                self.statusBar().showMessage("Query returned no results")
                return
                
            # Set up the table dimensions
            row_count = len(df)
            col_count = len(df.columns)
            self.results_table.setColumnCount(col_count)
            
            # Set column headers
            headers = [str(col) for col in df.columns]
            self.results_table.setHorizontalHeaderLabels(headers)
            
            # Calculate chunk size (adjust based on available memory)
            CHUNK_SIZE = 1000
            
            # Process data in chunks to avoid memory issues with large datasets
            for chunk_start in range(0, row_count, CHUNK_SIZE):
                chunk_end = min(chunk_start + CHUNK_SIZE, row_count)
                chunk = df.iloc[chunk_start:chunk_end]
                
                # Add rows for this chunk
                self.results_table.setRowCount(chunk_end)
                
                for row_idx, (_, row_data) in enumerate(chunk.iterrows(), start=chunk_start):
                    for col_idx, value in enumerate(row_data):
                        formatted_value = self.format_value(value)
                        item = QTableWidgetItem(formatted_value)
                        self.results_table.setItem(row_idx, col_idx, item)
                        
                # Process events to keep UI responsive
                QApplication.processEvents()
            
            # Optimize column widths
            self.results_table.resizeColumnsToContents()
            
            # Restore bar charts for columns that previously had them
            header = self.results_table.horizontalHeader()
            if isinstance(header, FilterHeader):
                for col_idx in columns_with_bars:
                    if col_idx < col_count:  # Only if column still exists
                        header.toggle_bar_chart(col_idx)
            
            # Update status
            memory_usage = df.memory_usage(deep=True).sum() / (1024 * 1024)  # Convert to MB
            self.statusBar().showMessage(
                f"Loaded {row_count:,} rows, {col_count} columns. Memory usage: {memory_usage:.1f} MB"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error",
                f"Failed to populate results table:\n\n{str(e)}")
            self.statusBar().showMessage("Failed to display results")

    def apply_filters(self):
        """Apply filters to the table based on filter inputs"""
        if self.current_df is None or not self.filter_widgets:
            return
            
        try:
            # Start with the original DataFrame
            filtered_df = self.current_df.copy()
            
            # Apply each non-empty filter
            for col_idx, filter_widget in enumerate(self.filter_widgets):
                filter_text = filter_widget.text().strip()
                if filter_text:
                    col_name = self.current_df.columns[col_idx]
                    # Convert column to string for filtering
                    filtered_df[col_name] = filtered_df[col_name].astype(str)
                    filtered_df = filtered_df[filtered_df[col_name].str.contains(filter_text, case=False, na=False)]
            
            # Update table with filtered data
            row_count = len(filtered_df)
            for row_idx in range(row_count):
                for col_idx, value in enumerate(filtered_df.iloc[row_idx]):
                    formatted_value = self.format_value(value)
                    item = QTableWidgetItem(formatted_value)
                    self.results_table.setItem(row_idx, col_idx, item)
            
            # Hide rows that don't match filter
            for row_idx in range(row_count + 1, self.results_table.rowCount()):
                self.results_table.hideRow(row_idx)
            
            # Show all filtered rows
            for row_idx in range(1, row_count + 1):
                self.results_table.showRow(row_idx)
            
            # Update status
            self.statusBar().showMessage(f"Showing {row_count:,} rows after filtering")
            
        except Exception as e:
            self.statusBar().showMessage(f"Error applying filters: {str(e)}")

    def format_value(self, value):
        """Format cell values efficiently"""
        if pd.isna(value):
            return "NULL"
        elif isinstance(value, (float, np.floating)):
            if value.is_integer():
                return str(int(value))
            return f"{value:.6g}"  # Use general format with up to 6 significant digits
        elif isinstance(value, (pd.Timestamp, datetime)):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, (np.integer, int)):
            return str(value)
        elif isinstance(value, bool):
            return str(value)
        elif isinstance(value, (bytes, bytearray)):
            return value.hex()
        return str(value)

    def browse_files(self):
        if not self.conn:
            # Create a default in-memory DuckDB connection if none exists
            self.conn = duckdb.connect(':memory:')
            self.current_connection_type = 'duckdb'
            self.db_info_label.setText("Connected to: in-memory DuckDB")
            
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Data Files",
            "",
            "Data Files (*.xlsx *.xls *.csv *.parquet);;Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;Parquet Files (*.parquet);;All Files (*)"
        )
        
        for file_name in file_names:
            try:
                if file_name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_name)
                elif file_name.endswith('.csv'):
                    df = pd.read_csv(file_name)
                elif file_name.endswith('.parquet'):
                    df = pd.read_parquet(file_name)
                else:
                    raise ValueError("Unsupported file format")
                
                # Generate table name from file name
                base_name = os.path.splitext(os.path.basename(file_name))[0]
                table_name = self.sanitize_table_name(base_name)
                
                # Ensure unique table name
                original_name = table_name
                counter = 1
                while table_name in self.loaded_tables:
                    table_name = f"{original_name}_{counter}"
                    counter += 1
                
                # Handle table creation based on database type
                if self.current_connection_type == 'sqlite':
                    # For SQLite, create a table from the DataFrame
                    df.to_sql(table_name, self.conn, index=False, if_exists='replace')
                else:
                    # For DuckDB, register the DataFrame as a view
                    self.conn.register(table_name, df)
                
                self.loaded_tables[table_name] = file_name
                
                # Store column names
                self.table_columns[table_name] = df.columns.tolist()
                
                # Update UI
                self.tables_list.addItem(f"{table_name} ({os.path.basename(file_name)})")
                self.statusBar().showMessage(f'Loaded {file_name} as table "{table_name}"')
                
                # Show preview of loaded data
                preview_df = df.head()
                self.populate_table(preview_df)
                
                # Update results title to show preview
                results_title = self.findChild(QLabel, "header_label", Qt.FindChildOption.FindChildrenRecursively)
                if results_title and results_title.text() == "RESULTS":
                    results_title.setText(f"PREVIEW: {table_name}")
                
                # Update completer with new table and column names
                self.update_completer()
                
            except Exception as e:
                error_msg = f'Error loading file {os.path.basename(file_name)}: {str(e)}'
                self.statusBar().showMessage(error_msg)
                QMessageBox.critical(self, "Error", error_msg)
                self.results_table.setRowCount(0)
                self.results_table.setColumnCount(0)
                self.row_count_label.setText("")

    def sanitize_table_name(self, name):
        # Replace invalid characters with underscores
        import re
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure it starts with a letter
        if not name[0].isalpha():
            name = 'table_' + name
        return name.lower()

    def remove_selected_table(self):
        current_item = self.tables_list.currentItem()
        if current_item:
            table_name = current_item.text().split(' (')[0]
            if table_name in self.loaded_tables:
                # Remove from DuckDB
                self.conn.execute(f'DROP VIEW IF EXISTS {table_name}')
                # Remove from our tracking
                del self.loaded_tables[table_name]
                if table_name in self.table_columns:
                    del self.table_columns[table_name]
                # Remove from list widget
                self.tables_list.takeItem(self.tables_list.row(current_item))
                self.statusBar().showMessage(f'Removed table "{table_name}"')
                self.results_table.setRowCount(0)
                self.results_table.setColumnCount(0)
                self.row_count_label.setText("")
                
                # Update completer
                self.update_completer()

    def open_database(self):
        """Open a database connection with proper error handling and resource management"""
        try:
            if self.conn:
                # Close existing connection before opening new one
                if self.current_connection_type == "duckdb":
                    self.conn.close()
                else:  # sqlite
                    self.conn.close()
                self.conn = None
                self.current_connection_type = None
            
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Open Database",
                "",
                "All Database Files (*.db *.sqlite *.sqlite3);;All Files (*)"
            )
            
            if filename:
                if self.is_sqlite_db(filename):
                    self.conn = sqlite3.connect(filename)
                    self.current_connection_type = "sqlite"
                else:
                    self.conn = duckdb.connect(filename)
                    self.current_connection_type = "duckdb"
                
                self.load_database_tables()
                self.statusBar().showMessage(f"Connected to database: {filename}")
                
        except (sqlite3.Error, duckdb.Error) as e:
            QMessageBox.critical(self, "Database Connection Error",
                f"Failed to open database:\n\n{str(e)}")
            self.statusBar().showMessage("Failed to open database")
            self.conn = None
            self.current_connection_type = None

    def is_sqlite_db(self, filename):
        """Check if the file is a SQLite database"""
        try:
            with open(filename, 'rb') as f:
                header = f.read(16)
                return header[:16] == b'SQLite format 3\x00'
        except:
            return False

    def load_database_tables(self):
        """Load all tables from the current database"""
        try:
            if self.current_connection_type == 'sqlite':
                query = "SELECT name FROM sqlite_master WHERE type='table'"
                cursor = self.conn.cursor()
                tables = cursor.execute(query).fetchall()
                for (table_name,) in tables:
                    self.loaded_tables[table_name] = 'database'
                    self.tables_list.addItem(f"{table_name} (database)")
                    
                    # Get column names for each table
                    try:
                        column_query = f"PRAGMA table_info({table_name})"
                        columns = cursor.execute(column_query).fetchall()
                        self.table_columns[table_name] = [col[1] for col in columns]  # Column name is at index 1
                    except Exception:
                        self.table_columns[table_name] = []
            else:  # duckdb
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
                result = self.conn.execute(query).fetchdf()
                for table_name in result['table_name']:
                    self.loaded_tables[table_name] = 'database'
                    self.tables_list.addItem(f"{table_name} (database)")
                    
                    # Get column names for each table
                    try:
                        column_query = f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}' AND table_schema='main'"
                        columns = self.conn.execute(column_query).fetchdf()
                        self.table_columns[table_name] = columns['column_name'].tolist()
                    except Exception:
                        self.table_columns[table_name] = []
                        
            # Update the completer with table and column names
            self.update_completer()
        except Exception as e:
            self.statusBar().showMessage(f'Error loading tables: {str(e)}')

    def update_completer(self):
        """Update the completer with table and column names"""
        # Collect all table names and column names
        completion_words = list(self.loaded_tables.keys())
        
        # Add column names with table name prefix (for joins)
        for table, columns in self.table_columns.items():
            completion_words.extend(columns)
            completion_words.extend([f"{table}.{col}" for col in columns])
            
        # Update the completer in the query editor
        self.query_edit.update_completer_model(completion_words)

    def execute_query(self):
        try:
            query = self.query_edit.toPlainText().strip()
            if not query:
                QMessageBox.warning(self, "Empty Query", "Please enter a SQL query to execute.")
                return

            start_time = datetime.now()
            
            try:
                if self.current_connection_type == "duckdb":
                    result = self.conn.execute(query).fetchdf()
                else:  # sqlite
                    result = pd.read_sql_query(query, self.conn)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                self.populate_table(result)
                self.statusBar().showMessage(f"Query executed successfully. Time: {execution_time:.2f}s. Rows: {len(result)}")
                
            except (duckdb.Error, sqlite3.Error) as e:
                error_msg = str(e)
                if "syntax error" in error_msg.lower():
                    QMessageBox.critical(self, "SQL Syntax Error", 
                        f"There is a syntax error in your query:\n\n{error_msg}")
                elif "no such table" in error_msg.lower():
                    QMessageBox.critical(self, "Table Not Found", 
                        f"The referenced table does not exist:\n\n{error_msg}")
                elif "no such column" in error_msg.lower():
                    QMessageBox.critical(self, "Column Not Found", 
                        f"The referenced column does not exist:\n\n{error_msg}")
                else:
                    QMessageBox.critical(self, "Database Error", 
                        f"An error occurred while executing the query:\n\n{error_msg}")
                self.statusBar().showMessage("Query execution failed")
                
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error",
                f"An unexpected error occurred:\n\n{str(e)}")
            self.statusBar().showMessage("Query execution failed")

    def clear_query(self):
        """Clear the query editor with animation"""
        # Save current text for animation
        current_text = self.query_edit.toPlainText()
        if not current_text:
            return
        
        # Clear the editor
        self.query_edit.clear()
        
        # Show success message
        self.statusBar().showMessage('Query cleared', 2000)  # Show for 2 seconds

    def show_table_preview(self, item):
        """Show a preview of the selected table"""
        if item:
            table_name = item.text().split(' (')[0]
            try:
                if self.current_connection_type == 'sqlite':
                    preview_df = pd.read_sql_query(f'SELECT * FROM "{table_name}" LIMIT 5', self.conn)
                else:
                    preview_df = self.conn.execute(f'SELECT * FROM {table_name} LIMIT 5').fetchdf()
                    
                self.populate_table(preview_df)
                self.statusBar().showMessage(f'Showing preview of table "{table_name}"')
                
                # Update the results title to show which table is being previewed
                results_title = self.findChild(QLabel, "header_label", Qt.FindChildOption.FindChildrenRecursively)
                if results_title and results_title.text() == "RESULTS":
                    results_title.setText(f"PREVIEW: {table_name}")
                
            except Exception as e:
                self.results_table.setRowCount(0)
                self.results_table.setColumnCount(0)
                self.row_count_label.setText("")
                self.statusBar().showMessage('Error showing table preview')
                
                # Show error message with modern styling
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Error showing preview: {str(e)}",
                    QMessageBox.StandardButton.Ok
                )

    def load_test_data(self):
        """Generate and load test data"""
        try:
            # Ensure we have a DuckDB connection
            if not self.conn or self.current_connection_type != 'duckdb':
                self.conn = duckdb.connect(':memory:')
                self.current_connection_type = 'duckdb'
                self.db_info_label.setText("Connected to: in-memory DuckDB")

            # Show loading indicator
            self.statusBar().showMessage('Generating test data...')
            
            # Create test data directory if it doesn't exist
            os.makedirs('test_data', exist_ok=True)
            
            # Generate test data
            sales_df = create_test_data.create_sales_data()
            customer_df = create_test_data.create_customer_data()
            product_df = create_test_data.create_product_data()
            
            # Save test data
            sales_df.to_excel('test_data/sample_sales_data.xlsx', index=False)
            customer_df.to_parquet('test_data/customer_data.parquet', index=False)
            product_df.to_excel('test_data/product_catalog.xlsx', index=False)
            
            # Load the files into DuckDB
            self.conn.register('sample_sales_data', sales_df)
            self.conn.register('product_catalog', product_df)
            self.conn.register('customer_data', customer_df)
            
            # Update loaded tables tracking
            self.loaded_tables['sample_sales_data'] = 'test_data/sample_sales_data.xlsx'
            self.loaded_tables['product_catalog'] = 'test_data/product_catalog.xlsx'
            self.loaded_tables['customer_data'] = 'test_data/customer_data.parquet'
            
            # Store column names
            self.table_columns['sample_sales_data'] = sales_df.columns.tolist()
            self.table_columns['product_catalog'] = product_df.columns.tolist()
            self.table_columns['customer_data'] = customer_df.columns.tolist()
            
            # Update UI
            self.tables_list.clear()
            for table_name, file_path in self.loaded_tables.items():
                self.tables_list.addItem(f"{table_name} ({os.path.basename(file_path)})")
            
            # Set the sample query
            sample_query = """
SELECT 
    DISTINCT
    c.customername     
FROM 
    sample_sales_data s
    INNER JOIN customer_data c ON c.customerid = s.customerid
    INNER JOIN product_catalog p ON p.productid = s.productid
LIMIT 10
"""
            self.query_edit.setPlainText(sample_query.strip())
            
            # Update completer
            self.update_completer()
            
            # Show success message
            self.statusBar().showMessage('Test data loaded successfully')
            
            # Show a preview of the sales data
            self.show_table_preview(self.tables_list.item(0))
            
        except Exception as e:
            self.statusBar().showMessage(f'Error loading test data: {str(e)}')
            QMessageBox.critical(self, "Error", f"Failed to load test data: {str(e)}")

    def export_to_excel(self):
        if self.results_table.rowCount() == 0:
            QMessageBox.warning(self, "No Data", "There is no data to export.")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(self, "Save as Excel", "", "Excel Files (*.xlsx);;All Files (*)")
        if not file_name:
            return
        
        try:
            # Show loading indicator
            self.statusBar().showMessage('Exporting data to Excel...')
            
            # Convert table data to DataFrame
            df = self.get_table_data_as_dataframe()
            df.to_excel(file_name, index=False)
            
            # Generate table name from file name
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            table_name = self.sanitize_table_name(base_name)
            
            # Ensure unique table name
            original_name = table_name
            counter = 1
            while table_name in self.loaded_tables:
                table_name = f"{original_name}_{counter}"
                counter += 1
            
            # Register the table in DuckDB
            self.conn.register(table_name, df)
            
            # Update tracking
            self.loaded_tables[table_name] = file_name
            self.table_columns[table_name] = df.columns.tolist()
            
            # Update UI
            self.tables_list.addItem(f"{table_name} ({os.path.basename(file_name)})")
            self.statusBar().showMessage(f'Data exported to {file_name} and loaded as table "{table_name}"')
            
            # Update completer with new table and column names
            self.update_completer()
            
            # Show success message
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"Data has been exported to:\n{file_name}\nand loaded as table: {table_name}",
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
            self.statusBar().showMessage('Error exporting data')

    def export_to_parquet(self):
        if self.results_table.rowCount() == 0:
            QMessageBox.warning(self, "No Data", "There is no data to export.")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(self, "Save as Parquet", "", "Parquet Files (*.parquet);;All Files (*)")
        if not file_name:
            return
        
        try:
            # Show loading indicator
            self.statusBar().showMessage('Exporting data to Parquet...')
            
            # Convert table data to DataFrame
            df = self.get_table_data_as_dataframe()
            df.to_parquet(file_name, index=False)
            
            # Generate table name from file name
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            table_name = self.sanitize_table_name(base_name)
            
            # Ensure unique table name
            original_name = table_name
            counter = 1
            while table_name in self.loaded_tables:
                table_name = f"{original_name}_{counter}"
                counter += 1
            
            # Register the table in DuckDB
            self.conn.register(table_name, df)
            
            # Update tracking
            self.loaded_tables[table_name] = file_name
            self.table_columns[table_name] = df.columns.tolist()
            
            # Update UI
            self.tables_list.addItem(f"{table_name} ({os.path.basename(file_name)})")
            self.statusBar().showMessage(f'Data exported to {file_name} and loaded as table "{table_name}"')
            
            # Update completer with new table and column names
            self.update_completer()
            
            # Show success message
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"Data has been exported to:\n{file_name}\nand loaded as table: {table_name}",
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
            self.statusBar().showMessage('Error exporting data')

    def get_table_data_as_dataframe(self):
        """Helper function to convert table widget data to a DataFrame"""
        headers = [self.results_table.horizontalHeaderItem(i).text() for i in range(self.results_table.columnCount())]
        data = []
        for row in range(self.results_table.rowCount()):
            row_data = []
            for column in range(self.results_table.columnCount()):
                item = self.results_table.item(row, column)
                row_data.append(item.text() if item else '')
            data.append(row_data)
        return pd.DataFrame(data, columns=headers)

    def keyPressEvent(self, event):
        """Handle global keyboard shortcuts"""
        # Execute query with Ctrl+Enter or Cmd+Enter (for Mac)
        if event.key() == Qt.Key.Key_Return and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.execute_btn.click()  # Simply click the button instead of animating
            return
        
        # Clear query with Ctrl+L
        if event.key() == Qt.Key.Key_L and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.clear_btn.click()  # Simply click the button instead of animating
            return
        
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """Ensure proper cleanup of database connections when closing the application"""
        try:
            # Check for unsaved changes
            if self.has_unsaved_changes():
                reply = QMessageBox.question(self, 'Save Changes',
                    'Do you want to save your changes before closing?',
                    QMessageBox.StandardButton.Save | 
                    QMessageBox.StandardButton.Discard | 
                    QMessageBox.StandardButton.Cancel)
                
                if reply == QMessageBox.StandardButton.Save:
                    self.save_project()
                elif reply == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return
            
            # Close database connections
            if self.conn:
                if self.current_connection_type == "duckdb":
                    self.conn.close()
                else:  # sqlite
                    self.conn.close()
            event.accept()
        except Exception as e:
            QMessageBox.warning(self, "Cleanup Warning", 
                f"Warning: Could not properly close database connection:\n{str(e)}")
            event.accept()

    def has_unsaved_changes(self):
        """Check if there are unsaved changes in the project"""
        if not self.current_project_file:
            return bool(self.loaded_tables or self.query_edit.toPlainText().strip())
        
        try:
            # Load the last saved state
            with open(self.current_project_file, 'r') as f:
                saved_data = json.load(f)
            
            # Compare current state with saved state
            current_data = {
                'tables': {
                    name: {
                        'file_path': path,
                        'columns': self.table_columns.get(name, [])
                    }
                    for name, path in self.loaded_tables.items()
                },
                'query': self.query_edit.toPlainText(),
                'connection_type': self.current_connection_type
            }
            
            return current_data != saved_data
            
        except Exception:
            # If there's any error reading the saved file, assume there are unsaved changes
            return True

    def show_tables_context_menu(self, position):
        """Show context menu for tables list"""
        item = self.tables_list.itemAt(position)
        if not item:
            return

        # Get table name without the file info in parentheses
        table_name = item.text().split(' (')[0]

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

        # Add menu actions
        select_from_action = context_menu.addAction("Select from")
        add_to_editor_action = context_menu.addAction("Just add to editor")

        # Show menu and get selected action
        action = context_menu.exec(self.tables_list.mapToGlobal(position))

        if action == select_from_action:
            # Insert "SELECT * FROM table_name" at cursor position
            cursor = self.query_edit.textCursor()
            cursor.insertText(f"SELECT * FROM {table_name}")
            self.query_edit.setFocus()
        elif action == add_to_editor_action:
            # Just insert the table name at cursor position
            cursor = self.query_edit.textCursor()
            cursor.insertText(table_name)
            self.query_edit.setFocus()

    def new_project(self):
        """Create a new project by clearing current state"""
        if self.conn:
            reply = QMessageBox.question(self, 'New Project',
                                       'Are you sure you want to start a new project? All unsaved changes will be lost.',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                # Close existing connection
                if self.current_connection_type == "duckdb":
                    self.conn.close()
                else:  # sqlite
                    self.conn.close()
                
                # Reset state
                self.conn = None
                self.current_connection_type = None
                self.loaded_tables.clear()
                self.table_columns.clear()
                self.tables_list.clear()
                self.query_edit.clear()
                self.results_table.setRowCount(0)
                self.results_table.setColumnCount(0)
                self.current_project_file = None
                self.setWindowTitle('SQL Shell')
                self.statusBar().showMessage('New project created')

    def save_project(self):
        """Save the current project"""
        if not self.current_project_file:
            self.save_project_as()
            return
            
        self.save_project_to_file(self.current_project_file)

    def save_project_as(self):
        """Save the current project to a new file"""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            "",
            "SQL Shell Project (*.sqls);;All Files (*)"
        )
        
        if file_name:
            if not file_name.endswith('.sqls'):
                file_name += '.sqls'
            self.save_project_to_file(file_name)
            self.current_project_file = file_name
            self.setWindowTitle(f'SQL Shell - {os.path.basename(file_name)}')

    def save_project_to_file(self, file_name):
        """Save project data to a file"""
        try:
            project_data = {
                'tables': {},
                'query': self.query_edit.toPlainText(),
                'connection_type': self.current_connection_type
            }
            
            # Save table information
            for table_name, file_path in self.loaded_tables.items():
                # For database tables and query results, store the special identifier
                if file_path in ['database', 'query_result']:
                    source_path = file_path
                else:
                    # For file-based tables, store the absolute path
                    source_path = os.path.abspath(file_path)
                
                project_data['tables'][table_name] = {
                    'file_path': source_path,
                    'columns': self.table_columns.get(table_name, [])
                }
            
            with open(file_name, 'w') as f:
                json.dump(project_data, f, indent=4)
                
            self.statusBar().showMessage(f'Project saved to {file_name}')
            
        except Exception as e:
            QMessageBox.critical(self, "Error",
                f"Failed to save project:\n\n{str(e)}")

    def open_project(self):
        """Open a project file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "SQL Shell Project (*.sqls);;All Files (*)"
        )
        
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    project_data = json.load(f)
                
                # Start fresh
                self.new_project()
                
                # Create connection if needed
                if not self.conn:
                    self.conn = duckdb.connect(':memory:')
                    self.current_connection_type = 'duckdb'
                    self.db_info_label.setText("Connected to: in-memory DuckDB")
                
                # Load tables
                for table_name, table_info in project_data['tables'].items():
                    file_path = table_info['file_path']
                    try:
                        if file_path == 'database':
                            # For tables from database, we need to recreate them from their data
                            # Execute a SELECT to get the data and recreate the table
                            query = f"SELECT * FROM {table_name}"
                            df = pd.read_sql_query(query, self.conn)
                            self.conn.register(table_name, df)
                            self.loaded_tables[table_name] = 'database'
                            self.tables_list.addItem(f"{table_name} (database)")
                        elif file_path == 'query_result':
                            # For tables from query results, we'll need to re-run the query
                            # For now, just note it as a query result table
                            self.loaded_tables[table_name] = 'query_result'
                            self.tables_list.addItem(f"{table_name} (query result)")
                        elif os.path.exists(file_path):
                            # Load the file based on its extension
                            if file_path.endswith(('.xlsx', '.xls')):
                                df = pd.read_excel(file_path)
                            elif file_path.endswith('.csv'):
                                df = pd.read_csv(file_path)
                            elif file_path.endswith('.parquet'):
                                df = pd.read_parquet(file_path)
                            else:
                                continue
                            
                            # Register the table
                            self.conn.register(table_name, df)
                            self.loaded_tables[table_name] = file_path
                            self.tables_list.addItem(f"{table_name} ({os.path.basename(file_path)})")
                        else:
                            QMessageBox.warning(self, "Warning",
                                f"Could not find file for table {table_name}: {file_path}")
                            continue
                            
                        # Store the columns
                        self.table_columns[table_name] = table_info['columns']
                            
                    except Exception as e:
                        QMessageBox.warning(self, "Warning",
                            f"Failed to load table {table_name}:\n{str(e)}")
                
                # Restore query
                if 'query' in project_data:
                    self.query_edit.setPlainText(project_data['query'])
                
                # Update UI
                self.current_project_file = file_name
                self.setWindowTitle(f'SQL Shell - {os.path.basename(file_name)}')
                self.statusBar().showMessage(f'Project loaded from {file_name}')
                self.update_completer()
                
            except Exception as e:
                QMessageBox.critical(self, "Error",
                    f"Failed to open project:\n\n{str(e)}")

def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))
    
    # Ensure we have a valid working directory with pool.db
    package_dir = os.path.dirname(os.path.abspath(__file__))
    working_dir = os.getcwd()
    
    # If pool.db doesn't exist in current directory, copy it from package
    if not os.path.exists(os.path.join(working_dir, 'pool.db')):
        import shutil
        package_db = os.path.join(package_dir, 'pool.db')
        if os.path.exists(package_db):
            shutil.copy2(package_db, working_dir)
        else:
            package_db = os.path.join(os.path.dirname(package_dir), 'pool.db')
            if os.path.exists(package_db):
                shutil.copy2(package_db, working_dir)
    
    # Show splash screen
    splash = AnimatedSplashScreen()
    splash.show()
    
    # Create and show main window after delay
    timer = QTimer()
    window = SQLShell()
    timer.timeout.connect(lambda: show_main_window())
    timer.start(2000)  # 2 second delay
    
    def show_main_window():
        window.show()
        splash.finish(window)
        timer.stop()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 