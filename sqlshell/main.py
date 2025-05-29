import sys
import os
import json
import argparse
from pathlib import Path
import tempfile

# Ensure proper path setup for resources when running directly
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTextEdit, QPushButton, QFileDialog,
                           QLabel, QSplitter, QListWidget, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox, QPlainTextEdit,
                           QCompleter, QFrame, QToolButton, QSizePolicy, QTabWidget,
                           QStyleFactory, QToolBar, QStatusBar, QLineEdit, QMenu,
                           QCheckBox, QWidgetAction, QMenuBar, QInputDialog, QProgressDialog,
                           QListWidgetItem, QDialog, QGraphicsDropShadowEffect, QTreeWidgetItem,
                           QComboBox)
from PyQt6.QtCore import Qt, QAbstractTableModel, QRegularExpression, QRect, QSize, QStringListModel, QPropertyAnimation, QEasingCurve, QTimer, QPoint, QMimeData
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat, QPainter, QTextFormat, QTextCursor, QIcon, QPalette, QLinearGradient, QBrush, QPixmap, QPolygon, QPainterPath, QDrag
import numpy as np
from datetime import datetime
import psutil

from sqlshell import create_test_data
from sqlshell.splash_screen import AnimatedSplashScreen
from sqlshell.syntax_highlighter import SQLSyntaxHighlighter
from sqlshell.editor import LineNumberArea, SQLEditor
from sqlshell.ui import FilterHeader, BarChartDelegate
from sqlshell.db import DatabaseManager, ExportManager
from sqlshell.query_tab import QueryTab
from sqlshell.styles import (get_application_stylesheet, get_tab_corner_stylesheet, 
                           get_context_menu_stylesheet,
                           get_header_label_stylesheet, get_db_info_label_stylesheet, 
                           get_tables_header_stylesheet, get_row_count_label_stylesheet)
from sqlshell.menus import setup_menubar
from sqlshell.table_list import DraggableTablesList

class SQLShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.export_manager = ExportManager(self.db_manager)
        self.current_df = None  # Store the current DataFrame for filtering
        self.filter_widgets = []  # Store filter line edits
        self.current_project_file = None  # Store the current project file path
        self.recent_projects = []  # Store list of recent projects
        self.max_recent_projects = 10  # Maximum number of recent projects to track
        self.tabs = []  # Store list of all tabs
        
        # User preferences
        self.auto_load_recent_project = True  # Default to auto-loading most recent project
        
        # File tracking for quick access
        self.recent_files = []  # Store list of recently opened files
        self.frequent_files = {}  # Store file paths with usage counts
        self.max_recent_files = 15  # Maximum number of recent files to track
        
        # Load recent projects from settings
        self.load_recent_projects()
        
        # Load recent and frequent files from settings
        self.load_recent_files()
        
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
        
        # Create initial tab
        self.add_tab()
        
        # Load most recent project if enabled and available
        if self.auto_load_recent_project:
            self.load_most_recent_project()

    def apply_stylesheet(self):
        """Apply custom stylesheet to the application"""
        self.setStyleSheet(get_application_stylesheet(self.colors))

    def init_ui(self):
        self.setWindowTitle('SQL Shell')
        
        # Get screen geometry for smart sizing
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        # Calculate adaptive window size based on screen size
        # Use 85% of screen size for larger screens, fixed size for smaller screens
        if screen_width >= 1920 and screen_height >= 1080:  # Larger screens
            window_width = int(screen_width * 0.85)
            window_height = int(screen_height * 0.85)
            self.setGeometry(
                (screen_width - window_width) // 2,  # Center horizontally
                (screen_height - window_height) // 2,  # Center vertically
                window_width, 
                window_height
            )
        else:  # Default for smaller screens
            self.setGeometry(100, 100, 1400, 800)
        
        # Remember if the window was maximized
        self.was_maximized = False
        
        # Set application icon
        icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            # Fallback to the main logo if the icon isn't found
            main_logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sqlshell_logo.png")
            if os.path.exists(main_logo_path):
                self.setWindowIcon(QIcon(main_logo_path))
        
        # Setup menus
        setup_menubar(self)
        
        # Update quick access menu
        if hasattr(self, 'quick_access_menu'):
            self.update_quick_access_menu()
        
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
        db_header.setStyleSheet(get_header_label_stylesheet())
        left_layout.addWidget(db_header)
        
        self.db_info_label = QLabel("No database connected")
        self.db_info_label.setStyleSheet(get_db_info_label_stylesheet())
        left_layout.addWidget(self.db_info_label)
        
        # Database action buttons
        db_buttons_layout = QHBoxLayout()
        db_buttons_layout.setSpacing(8)
        
        self.load_btn = QPushButton('Load')
        self.load_btn.setIcon(QIcon.fromTheme("document-open"))
        self.load_btn.clicked.connect(self.show_load_dialog)
        
        self.quick_access_btn = QPushButton('Quick Access')
        self.quick_access_btn.setIcon(QIcon.fromTheme("document-open-recent"))
        self.quick_access_btn.clicked.connect(self.show_quick_access_menu)
        
        db_buttons_layout.addWidget(self.load_btn)
        db_buttons_layout.addWidget(self.quick_access_btn)
        left_layout.addLayout(db_buttons_layout)
        
        # Tables section
        tables_header = QLabel("TABLES")
        tables_header.setObjectName("header_label")
        tables_header.setStyleSheet(get_tables_header_stylesheet())
        left_layout.addWidget(tables_header)
        
        # Tables info label
        tables_info = QLabel("Right-click on tables to profile columns, analyze structure, and discover distributions. Select multiple tables to analyze foreign key relationships.")
        tables_info.setWordWrap(True)
        tables_info.setStyleSheet("color: #7FB3D5; font-size: 11px; margin-top: 2px; margin-bottom: 5px;")
        left_layout.addWidget(tables_info)
        
        # Tables list with custom styling
        self.tables_list = DraggableTablesList(self)
        self.tables_list.itemClicked.connect(self.show_table_preview)
        self.tables_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tables_list.customContextMenuRequested.connect(self.show_tables_context_menu)
        left_layout.addWidget(self.tables_list)
        
        # Add spacer at the bottom
        left_layout.addStretch()
        
        # Right panel for query tabs and results
        right_panel = QFrame()
        right_panel.setObjectName("content_panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(16)
        
        # Query section header
        query_header = QLabel("SQL QUERY")
        query_header.setObjectName("header_label")
        right_layout.addWidget(query_header)
        
        # Create a drop area for tables above the tab widget
        self.tab_drop_area = QFrame()
        self.tab_drop_area.setFixedHeight(30)
        self.tab_drop_area.setObjectName("tab_drop_area")
        
        # Add a label with hint text
        drop_area_layout = QHBoxLayout(self.tab_drop_area)
        drop_area_layout.setContentsMargins(10, 0, 10, 0)
        self.drop_hint_label = QLabel("Drag tables here to create new query tabs")
        self.drop_hint_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        self.drop_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_area_layout.addWidget(self.drop_hint_label)
        
        self.tab_drop_area.setStyleSheet("""
            #tab_drop_area {
                background-color: #f8f9fa;
                border: 1px dashed #BDC3C7;
                border-radius: 4px;
                margin: 0 0 5px 0;
            }
            
            #tab_drop_area:hover {
                background-color: #E5F7FF;
                border: 1px dashed #3498DB;
            }
        """)
        self.tab_drop_area.setAcceptDrops(True)
        self.tab_drop_area.dragEnterEvent = self.tab_area_drag_enter
        self.tab_drop_area.dragMoveEvent = self.tab_area_drag_move
        self.tab_drop_area.dragLeaveEvent = self.tab_area_drag_leave
        self.tab_drop_area.dropEvent = self.tab_area_drop
        right_layout.addWidget(self.tab_drop_area)
        
        # Create tab widget for multiple queries
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # Connect double-click signal for direct tab renaming
        self.tab_widget.tabBarDoubleClicked.connect(self.handle_tab_double_click)
        
        # Add a "+" button to the tab bar
        self.tab_widget.setCornerWidget(self.create_tab_corner_widget())
        
        right_layout.addWidget(self.tab_widget)

        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 4)

        # Status bar
        self.statusBar().showMessage('Ready | Ctrl+Enter: Execute Query | Ctrl+K: Toggle Comment | Ctrl+T: New Tab | Ctrl+Shift+O: Quick Access Files')
        
    # Methods for handling drag and drop on the tab drop area
    def tab_area_drag_enter(self, event):
        """Handle drag enter events on the tab drop area"""
        # Accept only if from the tables list
        if event.source() == self.tables_list:
            # Extract table name(s) from the mime data
            mime_data = event.mimeData()
            if mime_data.hasText():
                table_names = mime_data.text().split(", ")
                if len(table_names) == 1:
                    self.drop_hint_label.setText(f"Release to create a new query tab for {table_names[0]}")
                else:
                    self.drop_hint_label.setText(f"Release to create {len(table_names)} new query tabs")
                
                self.drop_hint_label.setStyleSheet("color: #3498db; font-size: 11px; font-weight: bold;")
            
            # Highlight the drop area
            self.tab_drop_area.setStyleSheet("""
                #tab_drop_area {
                    background-color: #E5F7FF;
                    border: 2px dashed #3498DB;
                    border-radius: 4px;
                    margin: 0 0 5px 0;
                }
            """)
            self.tab_drop_area.setFixedHeight(40)
            event.acceptProposedAction()
        else:
            event.ignore()

    def tab_area_drag_move(self, event):
        """Handle drag move events on the tab drop area"""
        # Continue accepting drag moves
        if event.source() == self.tables_list:
            event.acceptProposedAction()
        else:
            event.ignore()

    def tab_area_drag_leave(self, event):
        """Handle drag leave events on the tab drop area"""
        # Reset the drop area
        self.tab_drop_area.setStyleSheet("""
            #tab_drop_area {
                background-color: #f8f9fa;
                border: 1px dashed #BDC3C7;
                border-radius: 4px;
                margin: 0 0 5px 0;
            }
        """)
        self.drop_hint_label.setText("Drag tables here to create new query tabs")
        self.drop_hint_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
        self.tab_drop_area.setFixedHeight(30)
        # No need to call a parent method

    def tab_area_drop(self, event):
        """Handle drop events on the tab drop area"""
        # Process the drop to create a new tab with SELECT query
        if event.source() == self.tables_list:
            mime_data = event.mimeData()
            if mime_data.hasText():
                table_names = mime_data.text().split(", ")
                
                for table_name in table_names:
                    # Check if this table needs to be reloaded first
                    if table_name in self.tables_list.tables_needing_reload:
                        # Reload the table immediately without asking
                        self.reload_selected_table(table_name)
                    
                    # Generate a title for the tab
                    tab_title = f"Query {table_name}"
                    # Create a new tab
                    new_tab = self.add_tab(tab_title)
                    # Set the SQL query
                    new_tab.set_query_text(f"SELECT * FROM {table_name}")
                
                self.statusBar().showMessage(f"Created new tab{'s' if len(table_names) > 1 else ''} for {', '.join(table_names)}")
                
                # Reset the drop area appearance
                self.tab_drop_area.setStyleSheet("""
                    #tab_drop_area {
                        background-color: #f8f9fa;
                        border: 1px dashed #BDC3C7;
                        border-radius: 4px;
                        margin: 0 0 5px 0;
                    }
                """)
                self.drop_hint_label.setText("Drag tables here to create new query tabs")
                self.drop_hint_label.setStyleSheet("color: #95a5a6; font-size: 11px;")
                self.tab_drop_area.setFixedHeight(30)
                
            event.acceptProposedAction()
        else:
            event.ignore()

    def create_tab_corner_widget(self):
        """Create a corner widget with a + button to add new tabs"""
        corner_widget = QWidget()
        layout = QHBoxLayout(corner_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        add_tab_btn = QToolButton()
        add_tab_btn.setText("+")
        add_tab_btn.setToolTip("Add new tab (Ctrl+T)")
        add_tab_btn.setStyleSheet(get_tab_corner_stylesheet())
        add_tab_btn.clicked.connect(self.add_tab)
        
        layout.addWidget(add_tab_btn)
        return corner_widget

    def populate_table(self, df):
        """Populate the results table with DataFrame data using memory-efficient chunking"""
        try:
            # Get the current tab
            current_tab = self.get_current_tab()
            if not current_tab:
                return
                
            # Store the current DataFrame for filtering
            current_tab.current_df = df.copy()
            self.current_df = df.copy()  # Keep this for compatibility with existing code
            
            # Remember which columns had bar charts
            header = current_tab.results_table.horizontalHeader()
            if isinstance(header, FilterHeader):
                columns_with_bars = header.columns_with_bars.copy()
            else:
                columns_with_bars = set()
            
            # Clear existing data
            current_tab.results_table.clearContents()
            current_tab.results_table.setRowCount(0)
            current_tab.results_table.setColumnCount(0)
            
            if df.empty:
                self.statusBar().showMessage("Query returned no results")
                return
                
            # Set up the table dimensions
            row_count = len(df)
            col_count = len(df.columns)
            current_tab.results_table.setColumnCount(col_count)
            
            # Set column headers
            headers = [str(col) for col in df.columns]
            current_tab.results_table.setHorizontalHeaderLabels(headers)
            
            # Calculate dynamic chunk size based on available memory
            import psutil
            available_memory = psutil.virtual_memory().available
            # Use 10% of available memory for chunking, with a minimum of 1000 rows
            memory_per_row = df.memory_usage(deep=True).sum() / len(df)
            CHUNK_SIZE = max(1000, min(10000, int(available_memory * 0.1 / memory_per_row)))
            
            # Add pagination controls if dataset is large
            if row_count > CHUNK_SIZE:
                # Remove any existing pagination widgets
                for i in reversed(range(current_tab.results_layout.count())):
                    item = current_tab.results_layout.itemAt(i)
                    widget = item.widget() if item is not None else None
                    if widget and widget.objectName() == "pagination_widget":
                        current_tab.results_layout.removeWidget(widget)
                        widget.setParent(None)
                        widget.deleteLater()

                # Create pagination widget
                pagination_widget = QWidget()
                pagination_widget.setObjectName("pagination_widget")
                pagination_layout = QHBoxLayout(pagination_widget)
                
                # Add page size selector
                page_size_label = QLabel("Rows per page:")
                page_size_combo = QComboBox()
                page_sizes = [1000, 5000, 10000, 50000, 100000]
                page_size_combo.addItems([str(size) for size in page_sizes])
                page_size_combo.setCurrentText(str(CHUNK_SIZE))
                
                # Add navigation buttons
                prev_btn = QPushButton("Previous")
                next_btn = QPushButton("Next")
                page_label = QLabel("Page 1")
                
                # Add widgets to layout
                pagination_layout.addWidget(page_size_label)
                pagination_layout.addWidget(page_size_combo)
                pagination_layout.addStretch()
                pagination_layout.addWidget(prev_btn)
                pagination_layout.addWidget(page_label)
                pagination_layout.addWidget(next_btn)
                
                # Add pagination widget to results layout
                current_tab.results_layout.addWidget(pagination_widget)
                
                # Store pagination state
                current_tab.pagination_state = {
                    'current_page': 0,
                    'page_size': CHUNK_SIZE,
                    'total_pages': (row_count + CHUNK_SIZE - 1) // CHUNK_SIZE,
                    'page_label': page_label,
                    'prev_btn': prev_btn,
                    'next_btn': next_btn,
                    'page_size_combo': page_size_combo
                }
                
                # Connect pagination signals
                def update_page_size(size):
                    current_tab.pagination_state['page_size'] = int(size)
                    current_tab.pagination_state['total_pages'] = (row_count + int(size) - 1) // int(size)
                    current_tab.pagination_state['current_page'] = 0
                    load_current_page()
                
                def load_current_page():
                    state = current_tab.pagination_state
                    start_idx = state['current_page'] * state['page_size']
                    end_idx = min(start_idx + state['page_size'], row_count)
                    
                    # Clear existing rows
                    current_tab.results_table.setRowCount(0)
                    
                    # Load current page
                    chunk = df.iloc[start_idx:end_idx]
                    current_tab.results_table.setRowCount(len(chunk))
                    
                    for row_idx, (_, row_data) in enumerate(chunk.iterrows()):
                        for col_idx, value in enumerate(row_data):
                            formatted_value = self.format_value(value)
                            item = QTableWidgetItem(formatted_value)
                            current_tab.results_table.setItem(row_idx, col_idx, item)
                    
                    # Update pagination controls
                    state['page_label'].setText(f"Page {state['current_page'] + 1} of {state['total_pages']}")
                    state['prev_btn'].setEnabled(state['current_page'] > 0)
                    state['next_btn'].setEnabled(state['current_page'] < state['total_pages'] - 1)
                    
                    # Process events to keep UI responsive
                    QApplication.processEvents()
                
                def next_page():
                    if current_tab.pagination_state['current_page'] < current_tab.pagination_state['total_pages'] - 1:
                        current_tab.pagination_state['current_page'] += 1
                        load_current_page()
                
                def prev_page():
                    if current_tab.pagination_state['current_page'] > 0:
                        current_tab.pagination_state['current_page'] -= 1
                        load_current_page()
                
                # Connect signals
                page_size_combo.currentTextChanged.connect(update_page_size)
                next_btn.clicked.connect(next_page)
                prev_btn.clicked.connect(prev_page)
                
                # Load first page
                load_current_page()
            else:
                # For smaller datasets, load all at once
                current_tab.results_table.setRowCount(row_count)
                
                for row_idx, (_, row_data) in enumerate(df.iterrows()):
                    for col_idx, value in enumerate(row_data):
                        formatted_value = self.format_value(value)
                        item = QTableWidgetItem(formatted_value)
                        current_tab.results_table.setItem(row_idx, col_idx, item)
                    
                    # Process events periodically to keep UI responsive
                    if row_idx % 1000 == 0:
                        QApplication.processEvents()
            
            # Optimize column widths
            current_tab.results_table.resizeColumnsToContents()
            
            # Restore bar charts for columns that previously had them
            header = current_tab.results_table.horizontalHeader()
            if isinstance(header, FilterHeader):
                for col_idx in columns_with_bars:
                    if col_idx < col_count:  # Only if column still exists
                        header.toggle_bar_chart(col_idx)
            
            # Update row count label
            current_tab.row_count_label.setText(f"{row_count:,} rows")
            
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
            # Display full number without scientific notation by using 'f' format
            # Format large numbers with commas for better readability
            if abs(value) >= 1000000:
                return f"{value:,.2f}"  # Format with commas and 2 decimal places
            return f"{value:.6f}"  # Use fixed-point notation with 6 decimal places
        elif isinstance(value, (pd.Timestamp, datetime)):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, (np.integer, int)):
            # Format large integers with commas for better readability
            return f"{value:,}"
        elif isinstance(value, bool):
            return str(value)
        elif isinstance(value, (bytes, bytearray)):
            return value.hex()
        return str(value)

    def browse_files(self):
        if not self.db_manager.is_connected():
            # Create a default in-memory DuckDB connection if none exists
            connection_info = self.db_manager.create_memory_connection()
            self.db_info_label.setText(connection_info)
            
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Data Files",
            "",
            "Data Files (*.xlsx *.xls *.csv *.parquet);;Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;Parquet Files (*.parquet);;All Files (*)"
        )
        
        for file_name in file_names:
            try:
                # Add to recent files
                self.add_recent_file(file_name)
                
                # Use the database manager to load the file
                table_name, df = self.db_manager.load_file(file_name)
                
                # Update UI using new method
                self.tables_list.add_table_item(table_name, os.path.basename(file_name))
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

    def remove_selected_table(self):
        current_item = self.tables_list.currentItem()
        if not current_item or self.tables_list.is_folder_item(current_item):
            return
            
        table_name = self.tables_list.get_table_name_from_item(current_item)
        if not table_name:
            return
            
        if self.db_manager.remove_table(table_name):
            # Remove from tree widget
            parent = current_item.parent()
            if parent:
                parent.removeChild(current_item)
            else:
                index = self.tables_list.indexOfTopLevelItem(current_item)
                if index >= 0:
                    self.tables_list.takeTopLevelItem(index)
                    
            self.statusBar().showMessage(f'Removed table "{table_name}"')
            
            # Get the current tab and clear its results table
            current_tab = self.get_current_tab()
            if current_tab:
                current_tab.results_table.setRowCount(0)
                current_tab.results_table.setColumnCount(0)
                current_tab.row_count_label.setText("")
            
            # Update completer
            self.update_completer()

    def open_database(self):
        """Open a database connection with proper error handling and resource management"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Open Database",
                "",
                "All Database Files (*.db *.sqlite *.sqlite3);;All Files (*)"
            )
            
            if filename:
                try:
                    # Add to recent files
                    self.add_recent_file(filename)
                    
                    # Clear existing database tables from the list widget
                    for i in range(self.tables_list.topLevelItemCount() - 1, -1, -1):
                        item = self.tables_list.topLevelItem(i)
                        if item and item.text(0).endswith('(database)'):
                            self.tables_list.takeTopLevelItem(i)
                    
                    # Use the database manager to open the database
                    self.db_manager.open_database(filename, load_all_tables=True)
                    
                    # Update UI with tables from the database
                    for table_name, source in self.db_manager.loaded_tables.items():
                        if source == 'database':
                            self.tables_list.add_table_item(table_name, "database")
                    
                    # Update the completer with table and column names
                    self.update_completer()
                    
                    # Update status bar
                    self.statusBar().showMessage(f"Connected to database: {filename}")
                    self.db_info_label.setText(self.db_manager.get_connection_info())
                    
                except Exception as e:
                    QMessageBox.critical(self, "Database Connection Error",
                        f"Failed to open database:\n\n{str(e)}")
                    self.statusBar().showMessage("Failed to open database")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                f"Unexpected error:\n\n{str(e)}")
            self.statusBar().showMessage("Error opening database")

    def update_completer(self):
        """Update the completer with table and column names in a non-blocking way"""
        try:
            # Check if any tabs exist
            if self.tab_widget.count() == 0:
                return
            
            # Import the suggestion manager
            from sqlshell.suggester_integration import get_suggestion_manager
            
            # Get the suggestion manager singleton
            suggestion_mgr = get_suggestion_manager()
            
            # Start a background update with a timer
            self.statusBar().showMessage("Updating auto-completion...", 2000)
            
            # Track query history and frequently used terms
            if not hasattr(self, 'query_history'):
                self.query_history = []
                self.completion_usage = {}  # Track usage frequency
            
            # Get schema information from the database manager
            try:
                # Get table and column information
                tables = set(self.db_manager.loaded_tables.keys())
                table_columns = self.db_manager.table_columns
                
                # Get column data types if available
                column_types = {}
                for table, columns in self.db_manager.table_columns.items():
                    for col in columns:
                        qualified_name = f"{table}.{col}"
                        # Try to infer type from sample data
                        if hasattr(self.db_manager, 'sample_data') and table in self.db_manager.sample_data:
                            sample = self.db_manager.sample_data[table]
                            if col in sample.columns:
                                # Get data type from pandas
                                col_dtype = str(sample[col].dtype)
                                column_types[qualified_name] = col_dtype
                                # Also store unqualified name
                                column_types[col] = col_dtype
                
                # Update the suggestion manager with schema information
                suggestion_mgr.update_schema(tables, table_columns, column_types)
                
            except Exception as e:
                self.statusBar().showMessage(f"Error getting completions: {str(e)}", 2000)
            
            # Get all completion words from basic system (for backward compatibility)
            try:
                completion_words = self.db_manager.get_all_table_columns()
            except Exception as e:
                self.statusBar().showMessage(f"Error getting completions: {str(e)}", 2000)
                completion_words = []
            
            # Add frequently used terms from query history with higher priority
            if hasattr(self, 'completion_usage') and self.completion_usage:
                # Get the most frequently used terms (top 100)
                frequent_terms = sorted(
                    self.completion_usage.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:100]
                
                # Add these to our completion words
                for term, count in frequent_terms:
                    suggestion_mgr.suggester.usage_counts[term] = count
                    if term not in completion_words:
                        completion_words.append(term)
            
            # Create a single shared model for all tabs to save memory
            model = QStringListModel(completion_words)
            
            # Keep a reference to the model to prevent garbage collection
            self._current_completer_model = model
            
            # First unregister all existing editors to avoid duplicates
            existing_editors = suggestion_mgr._editors.copy()
            for editor_id in existing_editors:
                suggestion_mgr.unregister_editor(editor_id)
            
            # Register editors with the suggestion manager and update their completer models
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if tab and hasattr(tab, 'query_edit'):
                    # Register this editor with the suggestion manager using a unique ID
                    editor_id = f"tab_{i}_{id(tab.query_edit)}"
                    suggestion_mgr.register_editor(tab.query_edit, editor_id)
                    
                    # Update the basic completer model for backward compatibility
                    try:
                        tab.query_edit.update_completer_model(model)
                    except Exception as e:
                        self.statusBar().showMessage(f"Error updating completer for tab {i}: {str(e)}", 2000)
            
            # Process events to keep UI responsive
            QApplication.processEvents()
            
            return True
            
        except Exception as e:
            # Catch any errors to prevent hanging
            self.statusBar().showMessage(f"Auto-completion update error: {str(e)}", 2000)
            return False

    def execute_query(self):
        try:
            # Get the current tab
            current_tab = self.get_current_tab()
            if not current_tab:
                return
                
            query = current_tab.get_query_text().strip()
            if not query:
                QMessageBox.warning(self, "Empty Query", "Please enter a SQL query to execute.")
                return

            # Check if the query references any tables that need to be loaded
            referenced_tables = self.extract_table_names_from_query(query)
            tables_to_load = [table for table in referenced_tables if table in self.tables_list.tables_needing_reload]
            
            # Load any tables that need to be loaded
            if tables_to_load:
                progress = QProgressDialog(f"Loading tables...", "Cancel", 0, len(tables_to_load), self)
                progress.setWindowTitle("Loading Tables")
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.show()
                
                for i, table_name in enumerate(tables_to_load):
                    if progress.wasCanceled():
                        self.statusBar().showMessage("Query canceled: table loading was interrupted")
                        return
                    
                    progress.setLabelText(f"Loading table: {table_name}")
                    progress.setValue(i)
                    QApplication.processEvents()
                    
                    self.reload_selected_table(table_name)
                
                progress.setValue(len(tables_to_load))
                progress.close()

            start_time = datetime.now()
            
            try:
                # Use the database manager to execute the query
                result = self.db_manager.execute_query(query)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                self.populate_table(result)
                self.statusBar().showMessage(f"Query executed successfully. Time: {execution_time:.2f}s. Rows: {len(result)}")
                
                # Record query for context-aware suggestions
                try:
                    from sqlshell.suggester_integration import get_suggestion_manager
                    suggestion_mgr = get_suggestion_manager()
                    suggestion_mgr.record_query(query)
                except Exception as e:
                    # Don't let suggestion errors affect query execution
                    print(f"Error recording query for suggestions: {e}")
                
                # Record query in history and update completion usage (legacy)
                self._update_query_history(query)
                
            except SyntaxError as e:
                QMessageBox.critical(self, "SQL Syntax Error", str(e))
                self.statusBar().showMessage("Query execution failed: syntax error")
            except ValueError as e:
                QMessageBox.critical(self, "Query Error", str(e))
                self.statusBar().showMessage("Query execution failed")
            except Exception as e:
                QMessageBox.critical(self, "Database Error", str(e))
                self.statusBar().showMessage("Query execution failed")
                
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error",
                f"An unexpected error occurred:\n\n{str(e)}")
            self.statusBar().showMessage("Query execution failed")
            
    def extract_table_names_from_query(self, query):
        """Extract table names from a SQL query using basic regex patterns"""
        import re
        
        # Convert to uppercase for easier pattern matching
        query_upper = query.upper()
        
        # Strip comments to avoid matching patterns inside comments
        query_upper = re.sub(r'--.*?$', '', query_upper, flags=re.MULTILINE)
        query_upper = re.sub(r'/\*.*?\*/', '', query_upper, flags=re.DOTALL)
        
        # Common SQL patterns that reference tables
        patterns = [
            r'FROM\s+["\[]?(\w+)["\]]?',                         # FROM clause
            r'JOIN\s+["\[]?(\w+)["\]]?',                         # JOIN clause
            r'UPDATE\s+["\[]?(\w+)["\]]?',                       # UPDATE statement
            r'INSERT\s+INTO\s+["\[]?(\w+)["\]]?',                # INSERT statement
            r'DELETE\s+FROM\s+["\[]?(\w+)["\]]?',                # DELETE statement
            r'CREATE\s+(?:TEMP|TEMPORARY)?\s*TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["\[]?(\w+)["\]]?', # CREATE TABLE
            r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?["\[]?(\w+)["\]]?',  # DROP TABLE
            r'ALTER\s+TABLE\s+["\[]?(\w+)["\]]?',                # ALTER TABLE
            r'WITH\s+(\w+)\s+AS',                                # Common Table Expressions
            r'MERGE\s+INTO\s+["\[]?(\w+)["\]]?'                  # MERGE statement
        ]
        
        tables = set()
        for pattern in patterns:
            matches = re.finditer(pattern, query_upper)
            for match in matches:
                # Get the table name from the matched group and strip any quotes
                table_name = match.group(1).strip('"[]`\'')
                
                # Skip SQL keywords
                if table_name in ('SELECT', 'WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 
                                 'UNION', 'INTERSECT', 'EXCEPT', 'WITH', 'AS', 'ON', 'USING'):
                    continue
                    
                # Add to our set of tables
                tables.add(table_name.lower())  # Convert to lowercase for case-insensitive comparison
                
        # Account for qualified table names (schema.table)
        qualified_tables = set()
        for table in tables:
            if '.' in table:
                qualified_tables.add(table.split('.')[-1])  # Add just the table part
                
        tables.update(qualified_tables)
        
        # Return all found table names in lowercase to match our table storage convention
        return tables

    def _update_query_history(self, query):
        """Update query history and track term usage for improved autocompletion"""
        import re
        
        # Initialize history if it doesn't exist
        if not hasattr(self, 'query_history'):
            self.query_history = []
            self.completion_usage = {}
        
        # Add query to history (limit to 100 queries)
        self.query_history.append(query)
        if len(self.query_history) > 100:
            self.query_history.pop(0)
        
        # Extract terms and patterns from the query to update usage frequency
        
        # Extract table and column names
        table_pattern = r'\b([a-zA-Z0-9_]+)\b\.([a-zA-Z0-9_]+)\b'
        qualified_columns = re.findall(table_pattern, query)
        for table, column in qualified_columns:
            qualified_name = f"{table}.{column}"
            self.completion_usage[qualified_name] = self.completion_usage.get(qualified_name, 0) + 1
            
            # Also count the table and column separately
            self.completion_usage[table] = self.completion_usage.get(table, 0) + 1
            self.completion_usage[column] = self.completion_usage.get(column, 0) + 1
        
        # Extract SQL keywords
        keyword_pattern = r'\b([A-Z_]{2,})\b'
        keywords = re.findall(keyword_pattern, query.upper())
        for keyword in keywords:
            self.completion_usage[keyword] = self.completion_usage.get(keyword, 0) + 1
        
        # Extract common SQL patterns
        patterns = [
            r'(SELECT\s+.*?\s+FROM)',
            r'(GROUP\s+BY\s+.*?(?:HAVING|ORDER|LIMIT|$))',
            r'(ORDER\s+BY\s+.*?(?:LIMIT|$))',
            r'(INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+JOIN).*?ON\s+.*?=\s+.*?(?:WHERE|JOIN|GROUP|ORDER|LIMIT|$)',
            r'(INSERT\s+INTO\s+.*?\s+VALUES)',
            r'(UPDATE\s+.*?\s+SET\s+.*?\s+WHERE)',
            r'(DELETE\s+FROM\s+.*?\s+WHERE)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Normalize pattern by removing extra whitespace and converting to uppercase
                normalized = re.sub(r'\s+', ' ', match).strip().upper()
                if len(normalized) < 50:  # Only track reasonably sized patterns
                    self.completion_usage[normalized] = self.completion_usage.get(normalized, 0) + 1
        
        # Schedule an update of the completion model (but not too often to avoid performance issues)
        if not hasattr(self, '_last_completer_update') or \
           (datetime.now() - self._last_completer_update).total_seconds() > 30:
            self._last_completer_update = datetime.now()
            
            # Use a timer to delay the update to avoid blocking the UI
            update_timer = QTimer()
            update_timer.setSingleShot(True)
            update_timer.timeout.connect(self.update_completer)
            update_timer.start(1000)  # Update after 1 second
            
    def clear_query(self):
        """Clear the query editor with animation"""
        # Get the current tab
        current_tab = self.get_current_tab()
        if not current_tab:
            return
            
        # Save current text for animation
        current_text = current_tab.get_query_text()
        if not current_text:
            return
        
        # Clear the editor
        current_tab.set_query_text("")
        
        # Show success message
        self.statusBar().showMessage('Query cleared', 2000)  # Show for 2 seconds

    def show_table_preview(self, item):
        """Show a preview of the selected table"""
        if not item or self.tables_list.is_folder_item(item):
            return
            
        # Get the current tab
        current_tab = self.get_current_tab()
        if not current_tab:
            return
            
        table_name = self.tables_list.get_table_name_from_item(item)
        if not table_name:
            return
        
        # Check if this table needs to be reloaded first
        if table_name in self.tables_list.tables_needing_reload:
            # Reload the table immediately without asking
            self.reload_selected_table(table_name)
                
        try:
            # Use the database manager to get a preview of the table
            preview_df = self.db_manager.get_table_preview(table_name)
                
            self.populate_table(preview_df)
            self.statusBar().showMessage(f'Showing preview of table "{table_name}"')
            
            # Update the results title to show which table is being previewed
            current_tab.results_title.setText(f"PREVIEW: {table_name}")
            
        except Exception as e:
            current_tab.results_table.setRowCount(0)
            current_tab.results_table.setColumnCount(0)
            current_tab.row_count_label.setText("")
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
            if not self.db_manager.is_connected() or self.db_manager.connection_type != 'duckdb':
                connection_info = self.db_manager.create_memory_connection()
                self.db_info_label.setText(connection_info)

            # Show loading indicator
            self.statusBar().showMessage('Generating test data...')
            
            # Create temporary directory for test data
            temp_dir = tempfile.mkdtemp(prefix='sqlshell_test_')
            
            # Generate test data
            sales_df = create_test_data.create_sales_data()
            customer_df = create_test_data.create_customer_data()
            large_customer_df = create_test_data.create_large_customer_data()
            product_df = create_test_data.create_product_data()
            large_numbers_df = create_test_data.create_large_numbers_data()
            california_housing_df = create_test_data.create_california_housing_data()
            
            # Save test data to temporary directory
            sales_path = os.path.join(temp_dir, 'sample_sales_data.xlsx')
            customer_path = os.path.join(temp_dir, 'customer_data.parquet')
            product_path = os.path.join(temp_dir, 'product_catalog.xlsx')
            large_numbers_path = os.path.join(temp_dir, 'large_numbers.xlsx')
            large_customer_path = os.path.join(temp_dir, 'large_customer_data.parquet')
            california_housing_path = os.path.join(temp_dir, 'california_housing_data.parquet')
            sales_df.to_excel(sales_path, index=False)
            customer_df.to_parquet(customer_path, index=False)
            product_df.to_excel(product_path, index=False)
            large_numbers_df.to_excel(large_numbers_path, index=False)
            large_customer_df.to_parquet(large_customer_path, index=False)
            california_housing_df.to_parquet(california_housing_path, index=False)

            # Register the tables in the database manager
            self.db_manager.register_dataframe(sales_df, 'sample_sales_data', sales_path)
            self.db_manager.register_dataframe(product_df, 'product_catalog', product_path)
            self.db_manager.register_dataframe(customer_df, 'customer_data', customer_path)
            self.db_manager.register_dataframe(large_numbers_df, 'large_numbers', large_numbers_path)
            self.db_manager.register_dataframe(large_customer_df, 'large_customer_data', large_customer_path)
            self.db_manager.register_dataframe(california_housing_df, 'california_housing_data', california_housing_path)
            
            # Update UI
            self.tables_list.clear()
            for table_name, file_path in self.db_manager.loaded_tables.items():
                # Use the new add_table_item method
                self.tables_list.add_table_item(table_name, os.path.basename(file_path))
            
            # Set the sample query in the current tab
            current_tab = self.get_current_tab()
            if current_tab:
                sample_query = """
-- Example query with tables containing large numbers
SELECT 
    ln.ID,
    ln.Category,
    ln.MediumValue,
    ln.LargeValue,
    ln.VeryLargeValue,
    ln.MassiveValue,
    ln.ExponentialValue,
    ln.Revenue,
    ln.Budget
FROM 
    large_numbers ln
WHERE 
    ln.LargeValue > 5000000000000
ORDER BY 
    ln.MassiveValue DESC
LIMIT 10
"""
                current_tab.set_query_text(sample_query.strip())
            
            # Update completer
            self.update_completer()
            
            # Show success message
            self.statusBar().showMessage('Test data loaded successfully')
            
            # Show a preview of the large numbers data
            large_numbers_item = self.tables_list.find_table_item("large_numbers")
            if large_numbers_item:
                self.show_table_preview(large_numbers_item)
            
        except Exception as e:
            self.statusBar().showMessage(f'Error loading test data: {str(e)}')
            QMessageBox.critical(self, "Error", f"Failed to load test data: {str(e)}")

    def export_to_excel(self):
        # Get the current tab
        current_tab = self.get_current_tab()
        if not current_tab:
            return
            
        if current_tab.results_table.rowCount() == 0:
            QMessageBox.warning(self, "No Data", "There is no data to export.")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(self, "Save as Excel", "", "Excel Files (*.xlsx);;All Files (*)")
        if not file_name:
            return
        
        try:
            # Show loading indicator
            self.statusBar().showMessage('Exporting data to Excel...')
            
            # Convert table data to DataFrame
            df = self.export_manager.convert_table_to_dataframe(current_tab.results_table)
            if df is None:
                raise Exception("Failed to convert table data to DataFrame")
            
            # Export using ExportManager
            table_name, metadata = self.export_manager.export_to_excel(df, file_name)
            
            # Update UI
            self.tables_list.add_table_item(table_name, os.path.basename(file_name))
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
        # Get the current tab
        current_tab = self.get_current_tab()
        if not current_tab:
            return
            
        if current_tab.results_table.rowCount() == 0:
            QMessageBox.warning(self, "No Data", "There is no data to export.")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(self, "Save as Parquet", "", "Parquet Files (*.parquet);;All Files (*)")
        if not file_name:
            return
        
        try:
            # Show loading indicator
            self.statusBar().showMessage('Exporting data to Parquet...')
            
            # Convert table data to DataFrame
            df = self.export_manager.convert_table_to_dataframe(current_tab.results_table)
            if df is None:
                raise Exception("Failed to convert table data to DataFrame")
            
            # Export using ExportManager
            table_name, metadata = self.export_manager.export_to_parquet(df, file_name)
            
            # Update UI
            self.tables_list.add_table_item(table_name, os.path.basename(file_name))
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
        """Helper function to convert table widget data to a DataFrame with proper data types"""
        current_tab = self.get_current_tab()
        if not current_tab:
            return pd.DataFrame()
        return self.export_manager.convert_table_to_dataframe(current_tab.results_table)

    def keyPressEvent(self, event):
        """Handle global keyboard shortcuts"""
        # Execute query with Ctrl+Enter or Cmd+Enter (for Mac)
        if event.key() == Qt.Key.Key_Return and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.execute_query()
            return
        
        # Add new tab with Ctrl+T
        if event.key() == Qt.Key.Key_T and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.add_tab()
            return
            
        # Close current tab with Ctrl+W
        if event.key() == Qt.Key.Key_W and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.close_current_tab()
            return
            
        # Duplicate tab with Ctrl+D
        if event.key() == Qt.Key.Key_D and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.duplicate_current_tab()
            return
            
        # Rename tab with Ctrl+R
        if event.key() == Qt.Key.Key_R and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.rename_current_tab()
            return
        
        # Show quick access menu with Ctrl+Shift+O
        if (event.key() == Qt.Key.Key_O and 
            (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and 
            (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
            self.show_quick_access_menu()
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
            
            # Save window state and settings
            self.save_recent_projects()
            
            # Close database connections
            self.db_manager.close_connection()
            event.accept()
        except Exception as e:
            QMessageBox.warning(self, "Cleanup Warning", 
                f"Warning: Could not properly close database connection:\n{str(e)}")
            event.accept()

    def has_unsaved_changes(self):
        """Check if there are unsaved changes in the project"""
        if not self.current_project_file:
            return (self.tab_widget.count() > 0 and any(self.tab_widget.widget(i).get_query_text().strip() 
                                                        for i in range(self.tab_widget.count()))) or bool(self.db_manager.loaded_tables)
        
        try:
            # Load the last saved state
            with open(self.current_project_file, 'r') as f:
                saved_data = json.load(f)
            
            # Prepare current tab data
            current_tabs_data = []
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                tab_data = {
                    'title': self.tab_widget.tabText(i),
                    'query': tab.get_query_text()
                }
                current_tabs_data.append(tab_data)
            
            # Compare current state with saved state
            current_data = {
                'tables': {
                    name: {
                        'file_path': path,
                        'columns': self.db_manager.table_columns.get(name, [])
                    }
                    for name, path in self.db_manager.loaded_tables.items()
                },
                'tabs': current_tabs_data,
                'connection_type': self.db_manager.connection_type
            }
            
            # Compare tables and connection type
            if (current_data['connection_type'] != saved_data.get('connection_type') or
                len(current_data['tables']) != len(saved_data.get('tables', {}))):
                return True
                
            # Compare tab data
            if 'tabs' not in saved_data or len(current_data['tabs']) != len(saved_data['tabs']):
                return True
                
            for i, tab_data in enumerate(current_data['tabs']):
                saved_tab = saved_data['tabs'][i]
                if (tab_data['title'] != saved_tab.get('title', '') or
                    tab_data['query'] != saved_tab.get('query', '')):
                    return True
            
            # If we get here, everything matches
            return False
            
        except Exception:
            # If there's any error reading the saved file, assume there are unsaved changes
            return True

    def show_tables_context_menu(self, position):
        """Show context menu for tables list"""
        # Check if we have multiple selected items
        selected_items = self.tables_list.selectedItems()
        if len(selected_items) > 1:
            # Filter out any folder items from selection
            table_items = [item for item in selected_items if not self.tables_list.is_folder_item(item)]
            
            if len(table_items) > 1:
                # Create context menu for multiple table selection
                context_menu = QMenu(self)
                context_menu.setStyleSheet(get_context_menu_stylesheet())
                
                # Add foreign key analysis option
                analyze_fk_action = context_menu.addAction(f"Analyze Foreign Keys Between {len(table_items)} Tables")
                analyze_fk_action.setIcon(QIcon.fromTheme("system-search"))
                
                # Show menu and get selected action
                action = context_menu.exec(self.tables_list.mapToGlobal(position))
                
                if action == analyze_fk_action:
                    self.analyze_foreign_keys_between_tables(table_items)
                
                return
        
        # Single item selection (original functionality)
        item = self.tables_list.itemAt(position)
        
        # If no item or it's a folder, let the tree widget handle it
        if not item or self.tables_list.is_folder_item(item):
            return

        # Get current tab
        current_tab = self.get_current_tab()
        if not current_tab:
            return

        # Get table name without the file info in parentheses
        table_name = self.tables_list.get_table_name_from_item(item)
        if not table_name:
            return

        # Create context menu
        context_menu = QMenu(self)
        context_menu.setStyleSheet(get_context_menu_stylesheet())

        # Add menu actions
        select_from_action = context_menu.addAction("Select from")
        add_to_editor_action = context_menu.addAction("Just add to editor")
        select_from_new_tab_action = context_menu.addAction("Select From in New Tab")
        
        # Add copy path actions
        context_menu.addSeparator()
        copy_path_action = context_menu.addAction("Copy Path")
        copy_relative_path_action = context_menu.addAction("Copy Relative Path")
        
        # Add entropy profiler action
        context_menu.addSeparator()
        analyze_entropy_action = context_menu.addAction("Analyze Column Importance")
        analyze_entropy_action.setIcon(QIcon.fromTheme("system-search"))
        
        # Add table profiler action
        profile_table_action = context_menu.addAction("Profile Table Structure")
        profile_table_action.setIcon(QIcon.fromTheme("edit-find"))
        
        # Add distributions profiler action
        profile_distributions_action = context_menu.addAction("Analyze Column Distributions")
        profile_distributions_action.setIcon(QIcon.fromTheme("accessories-calculator"))
        
        # Check if table needs reloading and add appropriate action
        if table_name in self.tables_list.tables_needing_reload:
            reload_action = context_menu.addAction("Reload Table")
            reload_action.setIcon(QIcon.fromTheme("view-refresh"))
        else:
            reload_action = context_menu.addAction("Refresh")
            reload_action.setIcon(QIcon.fromTheme("view-refresh"))
        
        # Add move to folder submenu
        move_menu = context_menu.addMenu("Move to Folder")
        move_menu.setIcon(QIcon.fromTheme("folder"))
        
        # Add "New Folder" option to move menu
        new_folder_action = move_menu.addAction("New Folder...")
        move_menu.addSeparator()
        
        # Add folders to the move menu
        for i in range(self.tables_list.topLevelItemCount()):
            top_item = self.tables_list.topLevelItem(i)
            if self.tables_list.is_folder_item(top_item):
                folder_action = move_menu.addAction(top_item.text(0))
                folder_action.setData(top_item)
        
        # Add root option
        move_menu.addSeparator()
        root_action = move_menu.addAction("Root (No Folder)")
        
        context_menu.addSeparator()
        rename_action = context_menu.addAction("Rename table...")
        delete_action = context_menu.addAction("Delete table")
        delete_action.setIcon(QIcon.fromTheme("edit-delete"))

        # Show menu and get selected action
        action = context_menu.exec(self.tables_list.mapToGlobal(position))

        if action == select_from_action:
            # Check if table needs reloading first
            if table_name in self.tables_list.tables_needing_reload:
                # Reload the table immediately without asking
                self.reload_selected_table(table_name)
                    
            # Insert "SELECT * FROM table_name" at cursor position
            cursor = current_tab.query_edit.textCursor()
            cursor.insertText(f"SELECT * FROM {table_name}")
            current_tab.query_edit.setFocus()
        elif action == add_to_editor_action:
            # Just insert the table name at cursor position
            cursor = current_tab.query_edit.textCursor()
            cursor.insertText(table_name)
            current_tab.query_edit.setFocus()
        elif action == select_from_new_tab_action:
            # Create a new tab with the selected table
            new_tab = self.add_tab(title=table_name)
            new_tab.set_query_text(f"SELECT * FROM {table_name}")
            new_tab.query_edit.setFocus()
        elif action == reload_action:
            self.reload_selected_table(table_name)
        elif action == analyze_entropy_action:
            # Call the entropy analysis method
            self.analyze_table_entropy(table_name)
        elif action == profile_table_action:
            # Call the table profile method
            self.profile_table_structure(table_name)
        elif action == profile_distributions_action:
            # Call the distributions profile method
            self.profile_distributions(table_name)
        elif action == rename_action:
            # Show rename dialog
            new_name, ok = QInputDialog.getText(
                self,
                "Rename Table",
                "Enter new table name:",
                QLineEdit.EchoMode.Normal,
                table_name
            )
            if ok and new_name:
                if self.rename_table(table_name, new_name):
                    # Update the item text
                    source = item.text(0).split(' (')[1][:-1]  # Get the source part
                    item.setText(0, f"{new_name} ({source})")
                    self.statusBar().showMessage(f'Table renamed to "{new_name}"')
        elif action == delete_action:
            # Show confirmation dialog
            reply = QMessageBox.question(
                self,
                "Delete Table",
                f"Are you sure you want to delete table '{table_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.remove_selected_table()
        elif action == new_folder_action:
            # Create a new folder and move the table there
            folder_name, ok = QInputDialog.getText(
                self,
                "New Folder",
                "Enter folder name:",
                QLineEdit.EchoMode.Normal
            )
            if ok and folder_name:
                folder = self.tables_list.create_folder(folder_name)
                self.tables_list.move_item_to_folder(item, folder)
                self.statusBar().showMessage(f'Moved table "{table_name}" to folder "{folder_name}"')
        elif action == root_action:
            # Move table to root (remove from any folder)
            parent = item.parent()
            if parent and self.tables_list.is_folder_item(parent):
                # Create a clone at root level
                source = item.text(0).split(' (')[1][:-1]  # Get the source part
                needs_reload = table_name in self.tables_list.tables_needing_reload
                # Remove from current parent
                parent.removeChild(item)
                # Add to root
                self.tables_list.add_table_item(table_name, source, needs_reload)
                self.statusBar().showMessage(f'Moved table "{table_name}" to root')
        elif action and action.parent() == move_menu:
            # Move to selected folder
            target_folder = action.data()
            if target_folder:
                self.tables_list.move_item_to_folder(item, target_folder)
                self.statusBar().showMessage(f'Moved table "{table_name}" to folder "{target_folder.text(0)}"')
        elif action == copy_path_action:
            # Get the full path from the table source
            if table_name in self.db_manager.loaded_tables:
                path = self.db_manager.loaded_tables[table_name]
                if path != 'database':  # Only copy if it's a file path
                    QApplication.clipboard().setText(path)
                    self.statusBar().showMessage(f"Copied full path to clipboard")
        elif action == copy_relative_path_action:
            # Get the relative path from the table source
            if table_name in self.db_manager.loaded_tables:
                path = self.db_manager.loaded_tables[table_name]
                if path != 'database':  # Only copy if it's a file path
                    try:
                        rel_path = os.path.relpath(path)
                        QApplication.clipboard().setText(rel_path)
                        self.statusBar().showMessage(f"Copied relative path to clipboard")
                    except ValueError:
                        self.statusBar().showMessage("Could not determine relative path")
                
    def analyze_foreign_keys_between_tables(self, table_items):
        """Analyze foreign key relationships between selected tables"""
        try:
            # Show a loading indicator
            table_count = len(table_items)
            self.statusBar().showMessage(f'Analyzing foreign key relationships between {table_count} tables...')
            
            # Extract table names from selected items
            table_names = []
            for item in table_items:
                table_name = self.tables_list.get_table_name_from_item(item)
                if table_name:
                    table_names.append(table_name)
            
            if len(table_names) < 2:
                QMessageBox.warning(self, "Not Enough Tables", 
                                    "At least two tables are required for foreign key analysis.")
                return
            
            # Check if any tables need to be reloaded
            tables_to_reload = [tn for tn in table_names if tn in self.tables_list.tables_needing_reload]
            for table_name in tables_to_reload:
                # Reload the table immediately
                self.reload_selected_table(table_name)
            
            # Fetch data for each table
            dfs = []
            for table_name in table_names:
                try:
                    # Get the data as a dataframe
                    query = f'SELECT * FROM "{table_name}"'
                    df = self.db_manager.execute_query(query)
                    
                    if df is not None and not df.empty:
                        # Sample large tables to improve performance
                        if len(df) > 10000:
                            self.statusBar().showMessage(f'Sampling {table_name} (using 10,000 rows from {len(df)} total)...')
                            df = df.sample(n=10000, random_state=42)
                        dfs.append(df)
                    else:
                        QMessageBox.warning(self, "Empty Table", 
                                            f"Table '{table_name}' has no data and will be skipped.")
                except Exception as e:
                    QMessageBox.warning(self, "Table Error", 
                                       f"Error loading table '{table_name}': {str(e)}\nThis table will be skipped.")
            
            if len(dfs) < 2:
                QMessageBox.warning(self, "Not Enough Tables", 
                                   "At least two tables with data are required for foreign key analysis.")
                return
            
            # Import the foreign key analyzer
            from sqlshell.utils.profile_foreign_keys import visualize_foreign_keys
            
            # Create and show the visualization
            self.statusBar().showMessage(f'Analyzing foreign key relationships between {len(dfs)} tables...')
            vis = visualize_foreign_keys(dfs, table_names)
            
            # Store a reference to prevent garbage collection
            self._fk_analysis_window = vis
            
            self.statusBar().showMessage(f'Foreign key analysis complete for {len(dfs)} tables')
            
        except Exception as e:
            QMessageBox.critical(self, "Analysis Error", f"Error analyzing foreign keys:\n\n{str(e)}")
            self.statusBar().showMessage(f'Error analyzing foreign keys: {str(e)}')

    def reload_selected_table(self, table_name=None):
        """Reload the data for a table from its source file"""
        try:
            # If table_name is not provided, get it from the selected item
            if not table_name:
                current_item = self.tables_list.currentItem()
                if not current_item:
                    return
                table_name = self.tables_list.get_table_name_from_item(current_item)
            
            # Show a loading indicator
            self.statusBar().showMessage(f'Reloading table "{table_name}"...')
            
            # Use the database manager to reload the table
            success, message = self.db_manager.reload_table(table_name)
            
            if success:
                # Show success message
                self.statusBar().showMessage(message)
                
                # Update completer with any new column names
                self.update_completer()
                
                # Mark the table as reloaded (remove the reload icon)
                self.tables_list.mark_table_reloaded(table_name)
                
                # Show a preview of the reloaded table
                table_item = self.tables_list.find_table_item(table_name)
                if table_item:
                    self.show_table_preview(table_item)
            else:
                # Show error message
                QMessageBox.warning(self, "Reload Failed", message)
                self.statusBar().showMessage(f'Failed to reload table: {message}')
                
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                f"Error reloading table:\n\n{str(e)}")
            self.statusBar().showMessage('Error reloading table')

    def new_project(self, skip_confirmation=False):
        """Create a new project by clearing current state"""
        if self.db_manager.is_connected() and not skip_confirmation:
            reply = QMessageBox.question(self, 'New Project',
                                      'Are you sure you want to start a new project? All unsaved changes will be lost.',
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                # Close existing connection
                self.db_manager.close_connection()
                
                # Clear all database tracking
                self.db_manager.loaded_tables = {}
                self.db_manager.table_columns = {}
                
                # Reset state
                self.tables_list.clear()
                
                # Clear all tabs except one
                while self.tab_widget.count() > 1:
                    self.close_tab(1)  # Always close tab at index 1 to keep at least one tab
                
                # Clear the remaining tab
                first_tab = self.get_tab_at_index(0)
                if first_tab:
                    first_tab.set_query_text("")
                    first_tab.results_table.setRowCount(0)
                    first_tab.results_table.setColumnCount(0)
                    first_tab.row_count_label.setText("")
                    first_tab.results_title.setText("RESULTS")
                
                self.current_project_file = None
                self.setWindowTitle('SQL Shell')
                self.db_info_label.setText("No database connected")
                self.statusBar().showMessage('New project created')
        elif skip_confirmation:
            # Skip confirmation and just clear everything
            if self.db_manager.is_connected():
                self.db_manager.close_connection()
            
            # Clear all database tracking
            self.db_manager.loaded_tables = {}
            self.db_manager.table_columns = {}
            
            # Reset state
            self.tables_list.clear()
            
            # Clear all tabs except one
            while self.tab_widget.count() > 1:
                self.close_tab(1)  # Always close tab at index 1 to keep at least one tab
            
            # Clear the remaining tab
            first_tab = self.get_tab_at_index(0)
            if first_tab:
                first_tab.set_query_text("")
                first_tab.results_table.setRowCount(0)
                first_tab.results_table.setColumnCount(0)
                first_tab.row_count_label.setText("")
                first_tab.results_title.setText("RESULTS")
            
            self.current_project_file = None
            self.setWindowTitle('SQL Shell')
            self.db_info_label.setText("No database connected")

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
            # Save tab information
            tabs_data = []
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                tab_data = {
                    'title': self.tab_widget.tabText(i),
                    'query': tab.get_query_text()
                }
                tabs_data.append(tab_data)
            
            project_data = {
                'tables': {},
                'folders': {},
                'tabs': tabs_data,
                'connection_type': self.db_manager.connection_type,
                'database_path': None  # Initialize to None
            }
            
            # If we have a database connection, save the path
            if self.db_manager.is_connected() and hasattr(self.db_manager, 'database_path'):
                project_data['database_path'] = self.db_manager.database_path
            
            # Helper function to recursively save folder structure
            def save_folder_structure(parent_item, parent_path=""):
                if parent_item is None:
                    # Handle top-level items
                    for i in range(self.tables_list.topLevelItemCount()):
                        item = self.tables_list.topLevelItem(i)
                        if self.tables_list.is_folder_item(item):
                            # It's a folder - add to folders and process its children
                            folder_name = item.text(0)
                            folder_id = f"folder_{i}"
                            project_data['folders'][folder_id] = {
                                'name': folder_name,
                                'parent': None,
                                'expanded': item.isExpanded()
                            }
                            save_folder_structure(item, folder_id)
                        else:
                            # It's a table - add to tables at root level
                            save_table_item(item)
                else:
                    # Process children of this folder
                    for i in range(parent_item.childCount()):
                        child = parent_item.child(i)
                        if self.tables_list.is_folder_item(child):
                            # It's a subfolder
                            folder_name = child.text(0)
                            folder_id = f"{parent_path}_sub_{i}"
                            project_data['folders'][folder_id] = {
                                'name': folder_name,
                                'parent': parent_path,
                                'expanded': child.isExpanded()
                            }
                            save_folder_structure(child, folder_id)
                        else:
                            # It's a table in this folder
                            save_table_item(child, parent_path)
            
            # Helper function to save table item
            def save_table_item(item, folder_id=None):
                table_name = self.tables_list.get_table_name_from_item(item)
                if not table_name or table_name not in self.db_manager.loaded_tables:
                    return
                    
                file_path = self.db_manager.loaded_tables[table_name]
                
                # For database tables and query results, store the special identifier
                if file_path in ['database', 'query_result']:
                    source_path = file_path
                else:
                    # For file-based tables, store the absolute path
                    source_path = os.path.abspath(file_path)
                
                project_data['tables'][table_name] = {
                    'file_path': source_path,
                    'columns': self.db_manager.table_columns.get(table_name, []),
                    'folder': folder_id
                }
            
            # Save the folder structure
            save_folder_structure(None)
            
            with open(file_name, 'w') as f:
                json.dump(project_data, f, indent=4)
                
            # Add to recent projects
            self.add_recent_project(os.path.abspath(file_name))
                
            self.statusBar().showMessage(f'Project saved to {file_name}')
            
        except Exception as e:
            QMessageBox.critical(self, "Error",
                f"Failed to save project:\n\n{str(e)}")

    def open_project(self, file_name=None):
        """Open a project file"""
        if not file_name:
            # Check for unsaved changes before showing file dialog
            if self.has_unsaved_changes():
                reply = QMessageBox.question(self, 'Save Changes',
                    'Do you want to save your changes before opening another project?',
                    QMessageBox.StandardButton.Save | 
                    QMessageBox.StandardButton.Discard | 
                    QMessageBox.StandardButton.Cancel)
                
                if reply == QMessageBox.StandardButton.Save:
                    self.save_project()
                elif reply == QMessageBox.StandardButton.Cancel:
                    return
            
            # Show file dialog after handling save prompt
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Open Project",
                "",
                "SQL Shell Project (*.sqls);;All Files (*)"
            )
        
        if file_name:
            try:
                # Create a progress dialog to keep UI responsive
                progress = QProgressDialog("Loading project...", "Cancel", 0, 100, self)
                progress.setWindowTitle("Opening Project")
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(500)  # Show after 500ms delay
                progress.setValue(0)
                
                # Load project data
                with open(file_name, 'r') as f:
                    project_data = json.load(f)
                
                # Update progress
                progress.setValue(10)
                QApplication.processEvents()
                
                # Start fresh
                self.new_project(skip_confirmation=True)
                progress.setValue(15)
                QApplication.processEvents()
                
                # Make sure all database tables are cleared from tracking
                self.db_manager.loaded_tables = {}
                self.db_manager.table_columns = {}
                
                # Check if there's a database path in the project
                has_database_path = 'database_path' in project_data and project_data['database_path']
                has_database_tables = any(table_info.get('file_path') == 'database' 
                                       for table_info in project_data.get('tables', {}).values())
                
                # Connect to database if needed
                progress.setLabelText("Connecting to database...")
                database_tables_loaded = False
                database_connection_message = None
                
                if has_database_path and has_database_tables:
                    database_path = project_data['database_path']
                    try:
                        if os.path.exists(database_path):
                            # Connect to the database
                            self.db_manager.open_database(database_path, load_all_tables=False)
                            self.db_info_label.setText(self.db_manager.get_connection_info())
                            self.statusBar().showMessage(f"Connected to database: {database_path}")
                            
                            # Mark database tables as loaded
                            database_tables_loaded = True
                        else:
                            database_tables_loaded = False
                            # Store the message instead of showing immediately
                            database_connection_message = (
                                "Database Not Found", 
                                f"The project's database file was not found at:\n{database_path}\n\n"
                                "Database tables will be shown but not accessible until you reconnect to the database.\n\n"
                                "Use the 'Open Database' button to connect to your database file."
                            )
                    except Exception as e:
                        database_tables_loaded = False
                        # Store the message instead of showing immediately
                        database_connection_message = (
                            "Database Connection Error",
                            f"Failed to connect to the project's database:\n{str(e)}\n\n"
                            "Database tables will be shown but not accessible until you reconnect to the database.\n\n"
                            "Use the 'Open Database' button to connect to your database file."
                        )
                else:
                    # Create connection if needed (we don't have a specific database to connect to)
                    database_tables_loaded = False
                    if not self.db_manager.is_connected():
                        connection_info = self.db_manager.create_memory_connection()
                        self.db_info_label.setText(connection_info)
                    elif 'connection_type' in project_data and project_data['connection_type'] != self.db_manager.connection_type:
                        # If connected but with a different database type than what was saved in the project
                        # Store the message instead of showing immediately
                        database_connection_message = (
                            "Database Type Mismatch",
                            f"The project was saved with a {project_data['connection_type']} database, but you're currently using {self.db_manager.connection_type}.\n\n"
                            "Some database-specific features may not work correctly. Consider reconnecting to the correct database type."
                        )
                
                progress.setValue(20)
                QApplication.processEvents()
                
                # First, recreate the folder structure
                folder_items = {}  # Store folder items by ID
                
                # Create folders first
                if 'folders' in project_data:
                    progress.setLabelText("Creating folders...")
                    # First pass: create top-level folders
                    for folder_id, folder_info in project_data['folders'].items():
                        if folder_info.get('parent') is None:
                            # Create top-level folder
                            folder = self.tables_list.create_folder(folder_info['name'])
                            folder_items[folder_id] = folder
                            # Set expanded state
                            folder.setExpanded(folder_info.get('expanded', True))
                    
                    # Second pass: create subfolders
                    for folder_id, folder_info in project_data['folders'].items():
                        parent_id = folder_info.get('parent')
                        if parent_id is not None and parent_id in folder_items:
                            # Create subfolder under parent
                            parent_folder = folder_items[parent_id]
                            subfolder = QTreeWidgetItem(parent_folder)
                            subfolder.setText(0, folder_info['name'])
                            subfolder.setIcon(0, QIcon.fromTheme("folder"))
                            subfolder.setData(0, Qt.ItemDataRole.UserRole, "folder")
                            # Make folder text bold
                            font = subfolder.font(0)
                            font.setBold(True)
                            subfolder.setFont(0, font)
                            # Set folder flags
                            subfolder.setFlags(subfolder.flags() | Qt.ItemFlag.ItemIsDropEnabled)
                            # Set expanded state
                            subfolder.setExpanded(folder_info.get('expanded', True))
                            folder_items[folder_id] = subfolder
                            
                progress.setValue(25)
                QApplication.processEvents()
                
                # Calculate progress steps for loading tables
                table_count = len(project_data.get('tables', {}))
                table_progress_start = 30
                table_progress_end = 70
                table_progress_step = (table_progress_end - table_progress_start) / max(1, table_count)
                current_progress = table_progress_start
                
                # Load tables
                for table_name, table_info in project_data.get('tables', {}).items():
                    if progress.wasCanceled():
                        break
                        
                    progress.setLabelText(f"Processing table: {table_name}")
                    file_path = table_info['file_path']
                    self.statusBar().showMessage(f"Processing table: {table_name} from {file_path}")
                    
                    try:
                        # Determine folder placement
                        folder_id = table_info.get('folder')
                        parent_folder = folder_items.get(folder_id) if folder_id else None
                        
                        if file_path == 'database':
                            # Different handling based on whether database connection is active
                            if database_tables_loaded:
                                # Store table info without loading data
                                self.db_manager.loaded_tables[table_name] = 'database'
                                if 'columns' in table_info:
                                    self.db_manager.table_columns[table_name] = table_info['columns']
                                    
                                # Create item without reload icon
                                if parent_folder:
                                    # Add to folder
                                    item = QTreeWidgetItem(parent_folder)
                                    item.setText(0, f"{table_name} (database)")
                                    item.setIcon(0, QIcon.fromTheme("x-office-spreadsheet"))
                                    item.setData(0, Qt.ItemDataRole.UserRole, "table")
                                else:
                                    # Add to root
                                    self.tables_list.add_table_item(table_name, "database", needs_reload=False)
                            else:
                                # No active database connection, just register the table name
                                self.db_manager.loaded_tables[table_name] = 'database'
                                if 'columns' in table_info:
                                    self.db_manager.table_columns[table_name] = table_info['columns']
                                
                                # Create item with reload icon
                                if parent_folder:
                                    # Add to folder
                                    item = QTreeWidgetItem(parent_folder)
                                    item.setText(0, f"{table_name} (database)")
                                    item.setIcon(0, QIcon.fromTheme("view-refresh"))
                                    item.setData(0, Qt.ItemDataRole.UserRole, "table")
                                    item.setToolTip(0, f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
                                    self.tables_list.tables_needing_reload.add(table_name)
                                else:
                                    # Add to root
                                    self.tables_list.add_table_item(table_name, "database", needs_reload=True)
                        elif file_path == 'query_result':
                            # For tables from query results, just note it as a query result table
                            self.db_manager.loaded_tables[table_name] = 'query_result'
                            
                            # Create item with reload icon
                            if parent_folder:
                                # Add to folder
                                item = QTreeWidgetItem(parent_folder)
                                item.setText(0, f"{table_name} (query result)")
                                item.setIcon(0, QIcon.fromTheme("view-refresh"))
                                item.setData(0, Qt.ItemDataRole.UserRole, "table")
                                item.setToolTip(0, f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
                                self.tables_list.tables_needing_reload.add(table_name)
                            else:
                                # Add to root
                                self.tables_list.add_table_item(table_name, "query result", needs_reload=True)
                        elif os.path.exists(file_path):
                            # Register the file as a table source but don't load data yet
                            self.db_manager.loaded_tables[table_name] = file_path
                            if 'columns' in table_info:
                                self.db_manager.table_columns[table_name] = table_info['columns']
                                
                            # Create item with reload icon
                            if parent_folder:
                                # Add to folder
                                item = QTreeWidgetItem(parent_folder)
                                item.setText(0, f"{table_name} ({os.path.basename(file_path)})")
                                item.setIcon(0, QIcon.fromTheme("view-refresh"))
                                item.setData(0, Qt.ItemDataRole.UserRole, "table")
                                item.setToolTip(0, f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
                                self.tables_list.tables_needing_reload.add(table_name)
                            else:
                                # Add to root
                                self.tables_list.add_table_item(table_name, os.path.basename(file_path), needs_reload=True)
                        else:
                            # File doesn't exist, but add to list with warning
                            self.db_manager.loaded_tables[table_name] = file_path
                            if 'columns' in table_info:
                                self.db_manager.table_columns[table_name] = table_info['columns']
                                
                            # Create item with reload icon and missing warning
                            if parent_folder:
                                # Add to folder
                                item = QTreeWidgetItem(parent_folder)
                                item.setText(0, f"{table_name} ({os.path.basename(file_path)} (missing))")
                                item.setIcon(0, QIcon.fromTheme("view-refresh"))
                                item.setData(0, Qt.ItemDataRole.UserRole, "table")
                                item.setToolTip(0, f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
                                self.tables_list.tables_needing_reload.add(table_name)
                            else:
                                # Add to root
                                self.tables_list.add_table_item(table_name, f"{os.path.basename(file_path)} (missing)", needs_reload=True)
                            
                    except Exception as e:
                        QMessageBox.warning(self, "Warning",
                            f"Failed to process table {table_name}:\n{str(e)}")
                
                    # Update progress for this table
                    current_progress += table_progress_step
                    progress.setValue(int(current_progress))
                    QApplication.processEvents()  # Keep UI responsive
                
                # Check if the operation was canceled
                if progress.wasCanceled():
                    self.statusBar().showMessage("Project loading was canceled")
                    progress.close()
                    return
                
                progress.setValue(75)
                progress.setLabelText("Setting up tabs...")
                QApplication.processEvents()
                
                # Load tabs in a more efficient way
                if 'tabs' in project_data and project_data['tabs']:
                    try:
                        # Temporarily disable signals
                        self.tab_widget.blockSignals(True)
                        
                        # First, pre-remove any existing tabs
                        while self.tab_widget.count() > 0:
                            widget = self.tab_widget.widget(0)
                            self.tab_widget.removeTab(0)
                            if widget in self.tabs:
                                self.tabs.remove(widget)
                            widget.deleteLater()
                        
                        # Then create all tab widgets at once (empty)
                        tab_count = len(project_data['tabs'])
                        tab_progress_step = 15 / max(1, tab_count)
                        progress.setValue(80)
                        QApplication.processEvents()
                        
                        # Create all tab widgets first without setting content
                        for i, tab_data in enumerate(project_data['tabs']):
                            # Create a new tab
                            tab = QueryTab(self)
                            self.tabs.append(tab)
                            
                            # Add to tab widget
                            title = tab_data.get('title', f'Query {i+1}')
                            self.tab_widget.addTab(tab, title)
                            
                            progress.setValue(int(80 + i * tab_progress_step/2))
                            QApplication.processEvents()
                        
                        # Now set the content for each tab
                        for i, tab_data in enumerate(project_data['tabs']):
                            # Get the tab and set its query text
                            tab = self.tab_widget.widget(i)
                            if tab and 'query' in tab_data:
                                tab.set_query_text(tab_data['query'])
                            
                            progress.setValue(int(87 + i * tab_progress_step/2))
                            QApplication.processEvents()
                        
                        # Re-enable signals
                        self.tab_widget.blockSignals(False)
                        
                        # Set current tab
                        if self.tab_widget.count() > 0:
                            self.tab_widget.setCurrentIndex(0)
                            
                    except Exception as e:
                        # If there's an error, ensure we restore signals
                        self.tab_widget.blockSignals(False)
                        self.statusBar().showMessage(f"Error loading tabs: {str(e)}")
                        # Create a single default tab if all fails
                        if self.tab_widget.count() == 0:
                            self.add_tab()
                else:
                    # Create default tab if no tabs in project
                    self.add_tab()
                
                progress.setValue(90)
                progress.setLabelText("Finishing up...")
                QApplication.processEvents()
                
                # Update UI
                self.current_project_file = file_name
                self.setWindowTitle(f'SQL Shell - {os.path.basename(file_name)}')
                
                # Add to recent projects
                self.add_recent_project(os.path.abspath(file_name))
                
                # Defer the auto-completer update to after loading is complete
                # This helps prevent UI freezing during project loading
                progress.setValue(95)
                QApplication.processEvents()
                
                # Use a timer to update the completer after the UI is responsive
                complete_timer = QTimer()
                complete_timer.setSingleShot(True)
                complete_timer.timeout.connect(self.update_completer)
                complete_timer.start(100)  # Short delay before updating completer
                
                # Queue another update for reliability - sometimes the first update might not fully complete
                failsafe_timer = QTimer()
                failsafe_timer.setSingleShot(True)
                failsafe_timer.timeout.connect(self.update_completer)
                failsafe_timer.start(2000)  # Try again after 2 seconds to ensure completion is loaded
                
                progress.setValue(100)
                QApplication.processEvents()
                
                # Show message about tables needing reload
                reload_count = len(self.tables_list.tables_needing_reload)
                if reload_count > 0:
                    self.statusBar().showMessage(
                        f'Project loaded from {file_name} with {table_count} tables. {reload_count} tables need to be reloaded (click reload icon).'
                    )
                else:
                    self.statusBar().showMessage(
                        f'Project loaded from {file_name} with {table_count} tables.'
                    )
                
                # Close progress dialog before showing message boxes
                progress.close()
                
                # Now show any database connection message we stored earlier
                if database_connection_message and not database_tables_loaded and has_database_tables:
                    title, message = database_connection_message
                    QMessageBox.warning(self, title, message)
                
            except Exception as e:
                QMessageBox.critical(self, "Error",
                    f"Failed to open project:\n\n{str(e)}")

    def rename_table(self, old_name, new_name):
        """Rename a table in the database and update tracking"""
        try:
            # Use the database manager to rename the table
            result = self.db_manager.rename_table(old_name, new_name)
            
            if result:
                # Update completer
                self.update_completer()
                return True
            
            return False
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rename table:\n\n{str(e)}")
            return False

    def load_recent_projects(self):
        """Load recent projects from settings file"""
        try:
            settings_file = os.path.join(os.path.expanduser('~'), '.sqlshell_settings.json')
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    self.recent_projects = settings.get('recent_projects', [])
                    
                    # Load user preferences
                    preferences = settings.get('preferences', {})
                    self.auto_load_recent_project = preferences.get('auto_load_recent_project', True)
                    
                    # Load window settings if available
                    window_settings = settings.get('window', {})
                    if window_settings:
                        self.restore_window_state(window_settings)
        except Exception:
            self.recent_projects = []

    def save_recent_projects(self):
        """Save recent projects to settings file"""
        try:
            settings_file = os.path.join(os.path.expanduser('~'), '.sqlshell_settings.json')
            settings = {}
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            settings['recent_projects'] = self.recent_projects
            
            # Save user preferences
            if 'preferences' not in settings:
                settings['preferences'] = {}
            settings['preferences']['auto_load_recent_project'] = self.auto_load_recent_project
            
            # Save window settings
            window_settings = self.save_window_state()
            settings['window'] = window_settings
            
            # Also save recent and frequent files data
            settings['recent_files'] = self.recent_files
            settings['frequent_files'] = self.frequent_files
            
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving recent projects: {e}")
            
    def save_window_state(self):
        """Save current window state"""
        window_settings = {
            'maximized': self.isMaximized(),
            'geometry': {
                'x': self.geometry().x(),
                'y': self.geometry().y(),
                'width': self.geometry().width(),
                'height': self.geometry().height()
            }
        }
        return window_settings
        
    def restore_window_state(self, window_settings):
        """Restore window state from settings"""
        try:
            # Check if we have valid geometry settings
            geometry = window_settings.get('geometry', {})
            if all(key in geometry for key in ['x', 'y', 'width', 'height']):
                x, y = geometry['x'], geometry['y']
                width, height = geometry['width'], geometry['height']
                
                # Ensure the window is visible on the current screen
                screen = QApplication.primaryScreen()
                screen_geometry = screen.availableGeometry()
                
                # Adjust if window would be off-screen
                if x < 0 or x + 100 > screen_geometry.width():
                    x = 100
                if y < 0 or y + 100 > screen_geometry.height():
                    y = 100
                    
                # Adjust if window is too large for the current screen
                if width > screen_geometry.width():
                    width = int(screen_geometry.width() * 0.85)
                if height > screen_geometry.height():
                    height = int(screen_geometry.height() * 0.85)
                
                self.setGeometry(x, y, width, height)
            
            # Set maximized state if needed
            if window_settings.get('maximized', False):
                self.showMaximized()
                self.was_maximized = True
                
        except Exception as e:
            print(f"Error restoring window state: {e}")
            # Fall back to default geometry
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            self.setGeometry(100, 100, 
                            min(1400, int(screen_geometry.width() * 0.85)), 
                            min(800, int(screen_geometry.height() * 0.85)))

    def add_recent_project(self, project_path):
        """Add a project to recent projects list"""
        if project_path in self.recent_projects:
            self.recent_projects.remove(project_path)
        self.recent_projects.insert(0, project_path)
        self.recent_projects = self.recent_projects[:self.max_recent_projects]
        self.save_recent_projects()
        self.update_recent_projects_menu()

    def update_recent_projects_menu(self):
        """Update the recent projects menu"""
        self.recent_projects_menu.clear()
        
        if not self.recent_projects:
            no_recent = self.recent_projects_menu.addAction("No Recent Projects")
            no_recent.setEnabled(False)
            return
            
        for project_path in self.recent_projects:
            if os.path.exists(project_path):
                action = self.recent_projects_menu.addAction(os.path.basename(project_path))
                action.setData(project_path)
                action.triggered.connect(lambda checked, path=project_path: self.open_recent_project(path))
        
        if self.recent_projects:
            self.recent_projects_menu.addSeparator()
            clear_action = self.recent_projects_menu.addAction("Clear Recent Projects")
            clear_action.triggered.connect(self.clear_recent_projects)

    def open_recent_project(self, project_path):
        """Open a project from the recent projects list"""
        if os.path.exists(project_path):
            # Check if current project has unsaved changes before loading the new one
            if self.has_unsaved_changes():
                reply = QMessageBox.question(self, 'Save Changes',
                    'Do you want to save your changes before loading another project?',
                    QMessageBox.StandardButton.Save | 
                    QMessageBox.StandardButton.Discard | 
                    QMessageBox.StandardButton.Cancel)
                
                if reply == QMessageBox.StandardButton.Save:
                    self.save_project()
                elif reply == QMessageBox.StandardButton.Cancel:
                    return
            
            # Now proceed with loading the project
            self.current_project_file = project_path
            self.open_project(project_path)
        else:
            QMessageBox.warning(self, "Warning",
                f"Project file not found:\n{project_path}")
            self.recent_projects.remove(project_path)
            self.save_recent_projects()
            self.update_recent_projects_menu()

    def clear_recent_projects(self):
        """Clear the list of recent projects"""
        self.recent_projects.clear()
        self.save_recent_projects()
        self.update_recent_projects_menu()

    def load_recent_files(self):
        """Load recent and frequent files from settings file"""
        try:
            settings_file = os.path.join(os.path.expanduser('~'), '.sqlshell_settings.json')
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    self.recent_files = settings.get('recent_files', [])
                    self.frequent_files = settings.get('frequent_files', {})
        except Exception:
            self.recent_files = []
            self.frequent_files = {}

    def save_recent_files(self):
        """Save recent and frequent files to settings file"""
        try:
            settings_file = os.path.join(os.path.expanduser('~'), '.sqlshell_settings.json')
            settings = {}
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            settings['recent_files'] = self.recent_files
            settings['frequent_files'] = self.frequent_files
            
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving recent files: {e}")

    def add_recent_file(self, file_path):
        """Add a file to recent files list and update frequent files count"""
        file_path = os.path.abspath(file_path)
        
        # Update recent files
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:self.max_recent_files]
        
        # Update frequency count
        if file_path in self.frequent_files:
            self.frequent_files[file_path] += 1
        else:
            self.frequent_files[file_path] = 1
        
        # Save to settings
        self.save_recent_files()
        
        # Update the quick access menu if it exists
        if hasattr(self, 'quick_access_menu'):
            self.update_quick_access_menu()

    def get_frequent_files(self, limit=10):
        """Get the most frequently used files"""
        sorted_files = sorted(
            self.frequent_files.items(), 
            key=lambda item: item[1], 
            reverse=True
        )
        return [path for path, count in sorted_files[:limit] if os.path.exists(path)]

    def clear_recent_files(self):
        """Clear the list of recent files"""
        self.recent_files.clear()
        self.save_recent_files()
        if hasattr(self, 'quick_access_menu'):
            self.update_quick_access_menu()

    def clear_frequent_files(self):
        """Clear the list of frequent files"""
        self.frequent_files.clear()
        self.save_recent_files()
        if hasattr(self, 'quick_access_menu'):
            self.update_quick_access_menu()

    def update_quick_access_menu(self):
        """Update the quick access menu with recent and frequent files"""
        if not hasattr(self, 'quick_access_menu'):
            return
            
        self.quick_access_menu.clear()
        
        # Add "Recent Files" section
        if self.recent_files:
            recent_section = self.quick_access_menu.addSection("Recent Files")
            
            for file_path in self.recent_files[:10]:  # Show top 10 recent files
                if os.path.exists(file_path):
                    file_name = os.path.basename(file_path)
                    action = self.quick_access_menu.addAction(file_name)
                    action.setData(file_path)
                    action.setToolTip(file_path)
                    action.triggered.connect(lambda checked, path=file_path: self.quick_open_file(path))
        
        # Add "Frequently Used Files" section
        frequent_files = self.get_frequent_files(10)  # Get top 10 frequent files
        if frequent_files:
            self.quick_access_menu.addSeparator()
            freq_section = self.quick_access_menu.addSection("Frequently Used Files")
            
            for file_path in frequent_files:
                file_name = os.path.basename(file_path)
                count = self.frequent_files.get(file_path, 0)
                action = self.quick_access_menu.addAction(f"{file_name} ({count} uses)")
                action.setData(file_path)
                action.setToolTip(file_path)
                action.triggered.connect(lambda checked, path=file_path: self.quick_open_file(path))
        
        # Add management options if we have any files
        if self.recent_files or self.frequent_files:
            self.quick_access_menu.addSeparator()
            clear_recent = self.quick_access_menu.addAction("Clear Recent Files")
            clear_recent.triggered.connect(self.clear_recent_files)
            
            clear_frequent = self.quick_access_menu.addAction("Clear Frequent Files")
            clear_frequent.triggered.connect(self.clear_frequent_files)
        else:
            # No files placeholder
            no_files = self.quick_access_menu.addAction("No Recent Files")
            no_files.setEnabled(False)

    def quick_open_file(self, file_path):
        """Open a file from the quick access menu"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", 
                f"The file no longer exists:\n{file_path}")
            
            # Remove from tracking
            if file_path in self.recent_files:
                self.recent_files.remove(file_path)
            if file_path in self.frequent_files:
                del self.frequent_files[file_path]
            self.save_recent_files()
            self.update_quick_access_menu()
            return
        
        try:
            # Determine file type
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Check if this is a Delta table directory
            is_delta_table = False
            if os.path.isdir(file_path):
                delta_path = Path(file_path)
                delta_log_path = delta_path / '_delta_log'
                if delta_log_path.exists():
                    is_delta_table = True
            
            if is_delta_table:
                # Delta table directory
                if not self.db_manager.is_connected():
                    # Create a default in-memory DuckDB connection if none exists
                    connection_info = self.db_manager.create_memory_connection()
                    self.db_info_label.setText(connection_info)
                
                # Use the database manager to load the Delta table
                table_name, df = self.db_manager.load_file(file_path)
                
                # Update UI using new method
                self.tables_list.add_table_item(table_name, os.path.basename(file_path))
                self.statusBar().showMessage(f'Loaded Delta table from {file_path} as "{table_name}"')
                
                # Show preview of loaded data
                preview_df = df.head()
                current_tab = self.get_current_tab()
                if current_tab:
                    self.populate_table(preview_df)
                    current_tab.results_title.setText(f"PREVIEW: {table_name}")
                
                # Update completer with new table and column names
                self.update_completer()
            elif file_ext in ['.db', '.sqlite', '.sqlite3']:
                # Database file
                # Clear existing database tables from the list widget
                for i in range(self.tables_list.topLevelItemCount() - 1, -1, -1):
                    item = self.tables_list.topLevelItem(i)
                    if item and item.text(0).endswith('(database)'):
                        self.tables_list.takeTopLevelItem(i)
                
                # Use the database manager to open the database
                self.db_manager.open_database(file_path)
                
                # Update UI with tables from the database using new method
                for table_name, source in self.db_manager.loaded_tables.items():
                    if source == 'database':
                        self.tables_list.add_table_item(table_name, "database")
                
                # Update the completer with table and column names
                self.update_completer()
                
                # Update status bar
                self.statusBar().showMessage(f"Connected to database: {file_path}")
                self.db_info_label.setText(self.db_manager.get_connection_info())
                
            elif file_ext in ['.xlsx', '.xls', '.csv', '.parquet']:
                # Data file
                if not self.db_manager.is_connected():
                    # Create a default in-memory DuckDB connection if none exists
                    connection_info = self.db_manager.create_memory_connection()
                    self.db_info_label.setText(connection_info)
                
                # Use the database manager to load the file
                table_name, df = self.db_manager.load_file(file_path)
                
                # Update UI using new method
                self.tables_list.add_table_item(table_name, os.path.basename(file_path))
                self.statusBar().showMessage(f'Loaded {file_path} as table "{table_name}"')
                
                # Show preview of loaded data
                preview_df = df.head()
                current_tab = self.get_current_tab()
                if current_tab:
                    self.populate_table(preview_df)
                    current_tab.results_title.setText(f"PREVIEW: {table_name}")
                
                # Update completer with new table and column names
                self.update_completer()
            else:
                QMessageBox.warning(self, "Unsupported File Type", 
                    f"The file type {file_ext} is not supported.")
                return
            
            # Update tracking - increment usage count
            self.add_recent_file(file_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                f"Failed to open file:\n\n{str(e)}")
            self.statusBar().showMessage(f"Error opening file: {os.path.basename(file_path)}")

    def show_quick_access_menu(self):
        """Display the quick access menu when the button is clicked"""
        # First, make sure the menu is up to date
        self.update_quick_access_menu()
        
        # Show the menu below the quick access button
        if hasattr(self, 'quick_access_menu') and hasattr(self, 'quick_access_btn'):
            self.quick_access_menu.popup(self.quick_access_btn.mapToGlobal(
                QPoint(0, self.quick_access_btn.height())))

    def add_tab(self, title="Query 1"):
        """Add a new query tab"""
        # Ensure title is a string
        title = str(title)
        
        # Create a new tab with a unique name if needed
        if title == "Query 1" and self.tab_widget.count() > 0:
            # Generate a unique tab name (Query 2, Query 3, etc.)
            # Use a more efficient approach to find a unique name
            base_name = "Query"
            existing_names = set()
            
            # Collect existing tab names first (more efficient than checking each time)
            for i in range(self.tab_widget.count()):
                existing_names.add(self.tab_widget.tabText(i))
            
            # Find the next available number
            counter = 1
            while f"{base_name} {counter}" in existing_names:
                counter += 1
            title = f"{base_name} {counter}"
        
        # Create the tab content
        tab = QueryTab(self)
        
        # Add to our list of tabs
        self.tabs.append(tab)
        
        # Block signals temporarily to improve performance when adding many tabs
        was_blocked = self.tab_widget.blockSignals(True)
        
        # Add tab to widget
        index = self.tab_widget.addTab(tab, title)
        self.tab_widget.setCurrentIndex(index)
        
        # Restore signals
        self.tab_widget.blockSignals(was_blocked)
        
        # Focus the new tab's query editor
        tab.query_edit.setFocus()
        
        # Process events to keep UI responsive
        QApplication.processEvents()
        
        # Update completer for the new tab
        try:
            from sqlshell.suggester_integration import get_suggestion_manager
            
            # Get the suggestion manager singleton
            suggestion_mgr = get_suggestion_manager()
            
            # Register the new editor with a unique ID
            editor_id = f"tab_{index}_{id(tab.query_edit)}"
            suggestion_mgr.register_editor(tab.query_edit, editor_id)
            
            # Apply the current completer model if available
            if hasattr(self, '_current_completer_model'):
                tab.query_edit.update_completer_model(self._current_completer_model)
        except Exception as e:
            # Don't let autocomplete errors affect tab creation
            print(f"Error setting up autocomplete for new tab: {e}")
        
        return tab
    
    def duplicate_current_tab(self):
        """Duplicate the current tab"""
        if self.tab_widget.count() == 0:
            return self.add_tab()
            
        current_idx = self.tab_widget.currentIndex()
        if current_idx == -1:
            return
            
        # Get current tab data
        current_tab = self.get_current_tab()
        current_title = self.tab_widget.tabText(current_idx)
        
        # Create a new tab with "(Copy)" suffix
        new_title = f"{current_title} (Copy)"
        new_tab = self.add_tab(new_title)
        
        # Copy query text
        new_tab.set_query_text(current_tab.get_query_text())
        
        # Return focus to the new tab
        new_tab.query_edit.setFocus()
        
        return new_tab
    
    def rename_current_tab(self):
        """Rename the current tab"""
        current_idx = self.tab_widget.currentIndex()
        if current_idx == -1:
            return
            
        current_title = self.tab_widget.tabText(current_idx)
        
        new_title, ok = QInputDialog.getText(
            self,
            "Rename Tab",
            "Enter new tab name:",
            QLineEdit.EchoMode.Normal,
            current_title
        )
        
        if ok and new_title:
            self.tab_widget.setTabText(current_idx, new_title)
    
    def handle_tab_double_click(self, index):
        """Handle double-clicking on a tab by starting rename immediately"""
        if index == -1:
            return
            
        current_title = self.tab_widget.tabText(index)
        
        new_title, ok = QInputDialog.getText(
            self,
            "Rename Tab",
            "Enter new tab name:",
            QLineEdit.EchoMode.Normal,
            current_title
        )
        
        if ok and new_title:
            self.tab_widget.setTabText(index, new_title)
    
    def close_tab(self, index):
        """Close the tab at the given index"""
        if self.tab_widget.count() <= 1:
            # Don't close the last tab, just clear it
            tab = self.get_tab_at_index(index)
            if tab:
                tab.set_query_text("")
                tab.results_table.clearContents()
                tab.results_table.setRowCount(0)
                tab.results_table.setColumnCount(0)
            return
            
        # Get the widget before removing the tab
        widget = self.tab_widget.widget(index)
        
        # Unregister the editor from the suggestion manager before closing
        try:
            from sqlshell.suggester_integration import get_suggestion_manager
            suggestion_mgr = get_suggestion_manager()
            
            # Find and unregister this editor
            for editor_id in list(suggestion_mgr._editors.keys()):
                if editor_id.startswith(f"tab_{index}_") or (hasattr(widget, 'query_edit') and 
                    str(id(widget.query_edit)) in editor_id):
                    suggestion_mgr.unregister_editor(editor_id)
        except Exception as e:
            # Don't let errors affect tab closing
            print(f"Error unregistering editor from suggestion manager: {e}")
        
        # Block signals temporarily to improve performance when removing multiple tabs
        was_blocked = self.tab_widget.blockSignals(True)
        
        # Remove the tab
        self.tab_widget.removeTab(index)
        
        # Restore signals
        self.tab_widget.blockSignals(was_blocked)
        
        # Remove from our list of tabs
        if widget in self.tabs:
            self.tabs.remove(widget)
        
        # Schedule the widget for deletion instead of immediate deletion
        widget.deleteLater()
        
        # Process events to keep UI responsive
        QApplication.processEvents()
        
        # Update tab indices in the suggestion manager
        QTimer.singleShot(100, self.update_tab_indices_in_suggestion_manager)
    
    def update_tab_indices_in_suggestion_manager(self):
        """Update tab indices in the suggestion manager after tab removal"""
        try:
            from sqlshell.suggester_integration import get_suggestion_manager
            suggestion_mgr = get_suggestion_manager()
            
            # Get current editors
            old_editors = suggestion_mgr._editors.copy()
            old_completers = suggestion_mgr._completers.copy()
            
            # Clear current registrations
            suggestion_mgr._editors.clear()
            suggestion_mgr._completers.clear()
            
            # Re-register with updated indices
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if tab and hasattr(tab, 'query_edit'):
                    # Register with new index
                    editor_id = f"tab_{i}_{id(tab.query_edit)}"
                    suggestion_mgr._editors[editor_id] = tab.query_edit
                    if hasattr(tab.query_edit, 'completer') and tab.query_edit.completer:
                        suggestion_mgr._completers[editor_id] = tab.query_edit.completer
        except Exception as e:
            # Don't let errors affect application
            print(f"Error updating tab indices in suggestion manager: {e}")
    
    def close_current_tab(self):
        """Close the current tab"""
        current_idx = self.tab_widget.currentIndex()
        if current_idx != -1:
            self.close_tab(current_idx)
    
    def get_current_tab(self):
        """Get the currently active tab"""
        current_idx = self.tab_widget.currentIndex()
        if current_idx == -1:
            return None
        return self.tab_widget.widget(current_idx)
        
    def get_tab_at_index(self, index):
        """Get the tab at the specified index"""
        if index < 0 or index >= self.tab_widget.count():
            return None
        return self.tab_widget.widget(index)

    def toggle_maximize_window(self):
        """Toggle between maximized and normal window state"""
        if self.isMaximized():
            self.showNormal()
            self.was_maximized = False
        else:
            self.showMaximized()
            self.was_maximized = True
            
    def get_selected_table(self):
        """Get the name of the currently selected table in the tables list"""
        if not hasattr(self, 'tables_list'):
            return None
            
        selected_items = self.tables_list.selectedItems()
        # Filter out folders and use only single selections
        table_items = [item for item in selected_items if not self.tables_list.is_folder_item(item)]
        
        if len(table_items) == 1:  # Only use if exactly one table is selected
            return self.tables_list.get_table_name_from_item(table_items[0])
        
        return None
            
    def change_zoom(self, factor):
        """Change the zoom level of the application by adjusting font sizes"""
        try:
            # Update font sizes for SQL editors
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if hasattr(tab, 'query_edit'):
                    # Get current font
                    current_font = tab.query_edit.font()
                    current_size = current_font.pointSizeF()
                    
                    # Calculate new size with limits to prevent too small/large fonts
                    new_size = current_size * factor
                    if 6 <= new_size <= 72:  # Reasonable limits
                        current_font.setPointSizeF(new_size)
                        tab.query_edit.setFont(current_font)
                        
                    # Also update the line number area
                    tab.query_edit.update_line_number_area_width(0)
                
                # Update results table font if needed
                if hasattr(tab, 'results_table'):
                    table_font = tab.results_table.font()
                    table_size = table_font.pointSizeF()
                    new_table_size = table_size * factor
                    
                    if 6 <= new_table_size <= 72:
                        table_font.setPointSizeF(new_table_size)
                        tab.results_table.setFont(table_font)
                        # Resize rows and columns to fit new font size
                        tab.results_table.resizeColumnsToContents()
                        tab.results_table.resizeRowsToContents()
            
            # Update status bar
            self.statusBar().showMessage(f"Zoom level adjusted to {int(current_size * factor)}", 2000)
            
        except Exception as e:
            self.statusBar().showMessage(f"Error adjusting zoom: {str(e)}", 2000)
            
    def reset_zoom(self):
        """Reset zoom level to default"""
        try:
            # Default font sizes
            sql_editor_size = 12
            table_size = 10
            
            # Update all tabs
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                
                # Reset editor font
                if hasattr(tab, 'query_edit'):
                    editor_font = tab.query_edit.font()
                    editor_font.setPointSizeF(sql_editor_size)
                    tab.query_edit.setFont(editor_font)
                    tab.query_edit.update_line_number_area_width(0)
                
                # Reset table font
                if hasattr(tab, 'results_table'):
                    table_font = tab.results_table.font()
                    table_font.setPointSizeF(table_size)
                    tab.results_table.setFont(table_font)
                    tab.results_table.resizeColumnsToContents()
                    tab.results_table.resizeRowsToContents()
            
            self.statusBar().showMessage("Zoom level reset to default", 2000)
            
        except Exception as e:
            self.statusBar().showMessage(f"Error resetting zoom: {str(e)}", 2000)

    def load_most_recent_project(self):
        """Load the most recent project if available"""
        if self.recent_projects:
            most_recent_project = self.recent_projects[0]
            if os.path.exists(most_recent_project):
                self.open_project(most_recent_project)
                self.statusBar().showMessage(f"Auto-loaded most recent project: {os.path.basename(most_recent_project)}")
            else:
                # Remove the non-existent project from the list
                self.recent_projects.remove(most_recent_project)
                self.save_recent_projects()
                # Try the next project if available
                if self.recent_projects:
                    self.load_most_recent_project()

    def load_delta_table(self):
        """Load a Delta table from a directory"""
        if not self.db_manager.is_connected():
            # Create a default in-memory DuckDB connection if none exists
            connection_info = self.db_manager.create_memory_connection()
            self.db_info_label.setText(connection_info)
            
        # Get directory containing the Delta table
        delta_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Delta Table Directory",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if not delta_dir:
            return
            
        # Check if this is a valid Delta table directory
        delta_path = Path(delta_dir)
        delta_log_path = delta_path / '_delta_log'
        
        if not delta_log_path.exists():
            # Ask if they want to select a subdirectory
            subdirs = [d for d in delta_path.iterdir() if d.is_dir() and (d / '_delta_log').exists()]
            
            if subdirs:
                # There are subdirectories with Delta tables
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Select Subdirectory")
                msg.setText(f"The selected directory does not contain a Delta table, but it contains {len(subdirs)} subdirectories with Delta tables.")
                msg.setInformativeText("Would you like to select one of these subdirectories?")
                msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg.setDefaultButton(QMessageBox.StandardButton.Yes)
                
                if msg.exec() == QMessageBox.StandardButton.Yes:
                    # Create a dialog to select a subdirectory
                    subdir_names = [d.name for d in subdirs]
                    subdir, ok = QInputDialog.getItem(
                        self,
                        "Select Delta Subdirectory",
                        "Choose a subdirectory containing a Delta table:",
                        subdir_names,
                        0,
                        False
                    )
                    
                    if not ok or not subdir:
                        return
                        
                    delta_dir = str(delta_path / subdir)
                    delta_path = Path(delta_dir)
                else:
                    # Show error and return
                    QMessageBox.critical(self, "Invalid Delta Table", 
                        "The selected directory does not contain a Delta table (_delta_log directory not found).")
                    return
            else:
                # No Delta tables found
                QMessageBox.critical(self, "Invalid Delta Table", 
                    "The selected directory does not contain a Delta table (_delta_log directory not found).")
                return
        
        try:
            # Add to recent files
            self.add_recent_file(delta_dir)
            
            # Use the database manager to load the Delta table
            import os
            table_name, df = self.db_manager.load_file(delta_dir)
            
            # Update UI using new method
            self.tables_list.add_table_item(table_name, os.path.basename(delta_dir))
            self.statusBar().showMessage(f'Loaded Delta table from {delta_dir} as "{table_name}"')
            
            # Show preview of loaded data
            preview_df = df.head()
            self.populate_table(preview_df)
            
            # Update results title to show preview
            current_tab = self.get_current_tab()
            if current_tab:
                current_tab.results_title.setText(f"PREVIEW: {table_name}")
            
            # Update completer with new table and column names
            self.update_completer()
            
        except Exception as e:
            error_msg = f'Error loading Delta table from {os.path.basename(delta_dir)}: {str(e)}'
            self.statusBar().showMessage(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
            
            current_tab = self.get_current_tab()
            if current_tab:
                current_tab.results_table.setRowCount(0)
                current_tab.results_table.setColumnCount(0)
                current_tab.row_count_label.setText("")

    def show_load_dialog(self):
        """Show a modern dialog with options to load different types of data"""
        # Create the dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Data")
        dialog.setMinimumWidth(450)
        dialog.setMinimumHeight(520)
        
        # Create a layout for the dialog
        layout = QVBoxLayout(dialog)
        layout.setSpacing(24)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header section with title and logo
        header_layout = QHBoxLayout()
        
        # Title label with gradient effect
        title_label = QLabel("Load Data")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("""
            font-weight: bold;
            background: -webkit-linear-gradient(#2C3E50, #3498DB);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        """)
        header_layout.addWidget(title_label, 1)
        
        # Try to add a small logo image
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.png")
            if os.path.exists(icon_path):
                logo_label = QLabel()
                logo_pixmap = QPixmap(icon_path).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(logo_pixmap)
                header_layout.addWidget(logo_label)
        except Exception:
            pass  # Skip logo if any issues
            
        layout.addLayout(header_layout)
        
        # Description with clearer styling
        desc_label = QLabel("Choose a data source to load into SQLShell")
        desc_label.setStyleSheet("color: #7F8C8D; font-size: 14px; margin: 4px 0 12px 0;")
        layout.addWidget(desc_label)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #E0E0E0; min-height: 1px; max-height: 1px;")
        layout.addWidget(separator)
        
        # Create option cards with icons, titles and descriptions
        options_layout = QVBoxLayout()
        options_layout.setSpacing(16)
        options_layout.setContentsMargins(0, 10, 0, 10)
        
        # Store animation references to prevent garbage collection
        animations = []
        
        # Function to create hover animations for cards
        def create_hover_animations(card):
            # Store original stylesheet
            original_style = card.styleSheet()
            hover_style = """
                background-color: #F8F9FA;
                border: 1px solid #3498DB;
                border-radius: 8px;
            """
            
            # Function to handle enter event with animation
            def enterEvent(event):
                # Create and configure animation
                anim = QPropertyAnimation(card, b"geometry")
                anim.setDuration(150)
                current_geo = card.geometry()
                target_geo = QRect(
                    current_geo.x() - 3,  # Slight shift to left for effect
                    current_geo.y(),
                    current_geo.width() + 6,  # Slight growth in width
                    current_geo.height()
                )
                anim.setStartValue(current_geo)
                anim.setEndValue(target_geo)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                
                # Set hover style
                card.setStyleSheet(hover_style)
                # Start animation
                anim.start()
                # Keep reference to prevent garbage collection
                animations.append(anim)
                
                # Call original enter event if it exists
                original_enter = getattr(card, "_original_enterEvent", None)
                if original_enter:
                    original_enter(event)
            
            # Function to handle leave event with animation
            def leaveEvent(event):
                # Create and configure animation to return to original state
                anim = QPropertyAnimation(card, b"geometry")
                anim.setDuration(200)
                current_geo = card.geometry()
                original_geo = QRect(
                    current_geo.x() + 3,  # Shift back to original position
                    current_geo.y(),
                    current_geo.width() - 6,  # Shrink back to original width
                    current_geo.height()
                )
                anim.setStartValue(current_geo)
                anim.setEndValue(original_geo)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                
                # Restore original style
                card.setStyleSheet(original_style)
                # Start animation
                anim.start()
                # Keep reference to prevent garbage collection
                animations.append(anim)
                
                # Call original leave event if it exists
                original_leave = getattr(card, "_original_leaveEvent", None)
                if original_leave:
                    original_leave(event)
            
            # Store original event handlers and set new ones
            card._original_enterEvent = card.enterEvent
            card._original_leaveEvent = card.leaveEvent
            card.enterEvent = enterEvent
            card.leaveEvent = leaveEvent
            
            return card
        
        # Function to create styled option buttons with descriptions
        def create_option_button(title, description, icon_name, option_type, accent_color="#3498DB"):
            # Create container frame
            container = QFrame()
            container.setObjectName("optionCard")
            container.setCursor(Qt.CursorShape.PointingHandCursor)
            container.setProperty("optionType", option_type)
            
            # Set frame style
            container.setFrameShape(QFrame.Shape.StyledPanel)
            container.setLineWidth(1)
            container.setMinimumHeight(90)
            container.setStyleSheet(f"""
                background-color: #FFFFFF;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
            """)
            
            # Create layout for the container
            card_layout = QHBoxLayout(container)
            card_layout.setContentsMargins(20, 16, 20, 16)
            
            # Add icon with colored circle background
            icon_container = QFrame()
            icon_container.setFixedSize(QSize(50, 50))
            icon_container.setStyleSheet(f"""
                background-color: {accent_color}20;  /* 20% opacity */
                border-radius: 25px;
                border: none;
            """)
            
            icon_layout = QHBoxLayout(icon_container)
            icon_layout.setContentsMargins(0, 0, 0, 0)
            
            icon_label = QLabel()
            icon = QIcon.fromTheme(icon_name)
            icon_pixmap = icon.pixmap(QSize(24, 24))
            icon_label.setPixmap(icon_pixmap)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_layout.addWidget(icon_label)
            
            card_layout.addWidget(icon_container)
            
            # Add text section
            text_layout = QVBoxLayout()
            text_layout.setSpacing(4)
            text_layout.setContentsMargins(12, 0, 0, 0)
            
            # Add title
            title_label = QLabel(title)
            title_font = QFont()
            title_font.setBold(True)
            title_font.setPointSize(12)
            title_label.setFont(title_font)
            text_layout.addWidget(title_label)
            
            # Add description
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #7F8C8D; font-size: 11px;")
            text_layout.addWidget(desc_label)
            
            card_layout.addLayout(text_layout, 1)
            
            # Add arrow icon to suggest clickable
            arrow_label = QLabel("→")
            arrow_label.setStyleSheet(f"color: {accent_color}; font-size: 16px; font-weight: bold;")
            card_layout.addWidget(arrow_label)
            
            # Connect click event
            container.mousePressEvent = lambda e: self.handle_load_option(dialog, option_type)
            
            # Apply hover animations
            container = create_hover_animations(container)
            
            return container
        
        # Database option
        db_option = create_option_button(
            "Database",
            "Load SQL database files (SQLite, etc.) to query and analyze.",
            "database",
            "database",
            "#2980B9"  # Blue accent
        )
        options_layout.addWidget(db_option)
        
        # Files option
        files_option = create_option_button(
            "Data Files", 
            "Load Excel, CSV, Parquet and other data file formats.",
            "document-new",
            "files",
            "#27AE60"  # Green accent
        )
        options_layout.addWidget(files_option)
        
        # Delta Table option
        delta_option = create_option_button(
            "Delta Table",
            "Load data from Delta Lake format directories.",
            "folder-open",
            "delta",
            "#8E44AD"  # Purple accent
        )
        options_layout.addWidget(delta_option)
        
        # Test Data option
        test_option = create_option_button(
            "Test Data",
            "Generate and load sample data for testing and exploration.",
            "system-run",
            "test",
            "#E67E22"  # Orange accent
        )
        options_layout.addWidget(test_option)
        
        layout.addLayout(options_layout)
        
        # Add spacer
        layout.addStretch()
        
        # Add separator line before buttons
        bottom_separator = QFrame()
        bottom_separator.setFrameShape(QFrame.Shape.HLine)
        bottom_separator.setFrameShadow(QFrame.Shadow.Sunken)
        bottom_separator.setStyleSheet("background-color: #E0E0E0; min-height: 1px; max-height: 1px;")
        layout.addWidget(bottom_separator)
        
        # Add cancel button
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.setContentsMargins(0, 16, 0, 0)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedWidth(100)
        cancel_btn.setStyleSheet("""
            background-color: #F5F5F5;
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            padding: 8px 16px;
            color: #7F8C8D;
            font-weight: bold;
        """)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Apply modern drop shadow effect to the dialog
        try:
            dialog.setGraphicsEffect(None)  # Clear any existing effects
            shadow = QGraphicsDropShadowEffect(dialog)
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 50))  # Semi-transparent black
            shadow.setOffset(0, 0)
            dialog.setGraphicsEffect(shadow)
        except Exception:
            pass  # Skip shadow if there are any issues
        
        # Add custom styling to make the dialog look modern
        dialog.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                border-radius: 12px;
            }
            QLabel {
                color: #2C3E50;
            }
        """)
        
        # Store dialog animation references in the instance to prevent garbage collection
        dialog._animations = animations
        
        # Center the dialog on the parent window
        if self.geometry().isValid():
            dialog.move(
                self.geometry().center().x() - dialog.width() // 2,
                self.geometry().center().y() - dialog.height() // 2
            )
        
        # Show the dialog
        dialog.exec()
    
    def handle_load_option(self, dialog, option):
        """Handle the selected load option"""
        # Close the dialog
        dialog.accept()
        
        # Call the appropriate function based on the selected option
        if option == "database":
            self.open_database()
        elif option == "files":
            self.browse_files()
        elif option == "delta":
            self.load_delta_table()
        elif option == "test":
            self.load_test_data()

    def analyze_table_entropy(self, table_name):
        """Analyze a table with the entropy profiler to identify important columns"""
        try:
            # Show a loading indicator
            self.statusBar().showMessage(f'Analyzing table "{table_name}" columns...')
            
            # Get the table data
            if table_name in self.db_manager.loaded_tables:
                # Check if table needs reloading first
                if table_name in self.tables_list.tables_needing_reload:
                    # Reload the table immediately
                    self.reload_selected_table(table_name)
                
                # Get the data as a dataframe
                query = f'SELECT * FROM "{table_name}"'
                df = self.db_manager.execute_query(query)
                
                if df is not None and not df.empty:
                    # Import the entropy profiler
                    from sqlshell.utils.profile_entropy import visualize_profile
                    
                    # Create and show the visualization
                    self.statusBar().showMessage(f'Generating entropy profile for "{table_name}"...')
                    vis = visualize_profile(df)
                    
                    # Store a reference to prevent garbage collection
                    self._entropy_window = vis
                    
                    self.statusBar().showMessage(f'Entropy profile generated for "{table_name}"')
                else:
                    QMessageBox.warning(self, "Empty Table", f"Table '{table_name}' has no data to analyze.")
                    self.statusBar().showMessage(f'Table "{table_name}" is empty - cannot analyze')
            else:
                QMessageBox.warning(self, "Table Not Found", f"Table '{table_name}' not found.")
                self.statusBar().showMessage(f'Table "{table_name}" not found')
                
        except Exception as e:
            QMessageBox.critical(self, "Analysis Error", f"Error analyzing table:\n\n{str(e)}")
            self.statusBar().showMessage(f'Error analyzing table: {str(e)}')
            
    def profile_table_structure(self, table_name):
        """Analyze a table's structure to identify candidate keys and functional dependencies"""
        try:
            # Show a loading indicator
            self.statusBar().showMessage(f'Profiling table structure for "{table_name}"...')
            
            # Get the table data
            if table_name in self.db_manager.loaded_tables:
                # Check if table needs reloading first
                if table_name in self.tables_list.tables_needing_reload:
                    # Reload the table immediately
                    self.reload_selected_table(table_name)
                
                # Get the data as a dataframe
                query = f'SELECT * FROM "{table_name}"'
                df = self.db_manager.execute_query(query)
                
                if df is not None and not df.empty:
                    # Sample the data if it's larger than 10,000 rows
                    row_count = len(df)
                    if row_count > 10000:
                        self.statusBar().showMessage(f'Sampling {table_name} (using 10,000 rows from {row_count} total)...')
                        df = df.sample(n=10000, random_state=42)
                    
                    # Import the key profiler
                    from sqlshell.utils.profile_keys import visualize_profile
                    
                    # Create and show the visualization
                    self.statusBar().showMessage(f'Generating table profile for "{table_name}"...')
                    vis = visualize_profile(df)
                    
                    # Store a reference to prevent garbage collection
                    self._keys_profile_window = vis
                    
                    if row_count > 10000:
                        self.statusBar().showMessage(f'Table structure profile generated for "{table_name}" (sampled 10,000 rows from {row_count})')
                    else:
                        self.statusBar().showMessage(f'Table structure profile generated for "{table_name}"')
                else:
                    QMessageBox.warning(self, "Empty Table", f"Table '{table_name}' has no data to analyze.")
                    self.statusBar().showMessage(f'Table "{table_name}" is empty - cannot analyze')
            else:
                QMessageBox.warning(self, "Table Not Found", f"Table '{table_name}' not found.")
                self.statusBar().showMessage(f'Table "{table_name}" not found')
                
        except Exception as e:
            QMessageBox.critical(self, "Profile Error", f"Error profiling table structure:\n\n{str(e)}")
            self.statusBar().showMessage(f'Error profiling table: {str(e)}')
    
    def profile_distributions(self, table_name):
        """Analyze a table's column distributions to understand data patterns"""
        try:
            # Show a loading indicator
            self.statusBar().showMessage(f'Analyzing column distributions for "{table_name}"...')
            
            # Get the table data
            if table_name in self.db_manager.loaded_tables:
                # Check if table needs reloading first
                if table_name in self.tables_list.tables_needing_reload:
                    # Reload the table immediately
                    self.reload_selected_table(table_name)
                
                # Get the data as a dataframe
                query = f'SELECT * FROM "{table_name}"'
                df = self.db_manager.execute_query(query)
                
                if df is not None and not df.empty:
                    # Sample the data if it's larger than 10,000 rows
                    row_count = len(df)
                    if row_count > 10000:
                        self.statusBar().showMessage(f'Sampling {table_name} (using 10,000 rows from {row_count} total)...')
                        df = df.sample(n=10000, random_state=42)
                    
                    # Import the distribution profiler
                    from sqlshell.utils.profile_distributions import visualize_profile
                    
                    # Create and show the visualization
                    self.statusBar().showMessage(f'Generating distribution profile for "{table_name}"...')
                    vis = visualize_profile(df)
                    
                    # Store a reference to prevent garbage collection
                    self._distributions_window = vis
                    
                    if row_count > 10000:
                        self.statusBar().showMessage(f'Distribution profile generated for "{table_name}" (sampled 10,000 rows from {row_count})')
                    else:
                        self.statusBar().showMessage(f'Distribution profile generated for "{table_name}"')
                else:
                    QMessageBox.warning(self, "Empty Table", f"Table '{table_name}' has no data to analyze.")
                    self.statusBar().showMessage(f'Table "{table_name}" is empty - cannot analyze')
            else:
                QMessageBox.warning(self, "Table Not Found", f"Table '{table_name}' not found.")
                self.statusBar().showMessage(f'Table "{table_name}" not found')
                
        except Exception as e:
            QMessageBox.critical(self, "Profile Error", f"Error analyzing distributions:\n\n{str(e)}")
            self.statusBar().showMessage(f'Error analyzing distributions: {str(e)}')

    def explain_column(self, column_name):
        """Analyze a column to explain its relationship with other columns"""
        try:
            # Get the current tab
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None:
                return
                
            # Show a loading indicator
            self.statusBar().showMessage(f'Analyzing column "{column_name}"...')
            
            # Get the dataframe from the current tab
            df = current_tab.current_df
            
            if df is not None and not df.empty:
                # Sample the data if it's larger than 100 rows for ultra-fast performance
                row_count = len(df)
                if row_count > 100:
                    self.statusBar().showMessage(f'Sampling data (using 100 rows from {row_count} total)...')
                    df = df.sample(n=100, random_state=42)
                
                # Import the column profiler
                from sqlshell.utils.profile_column import visualize_profile
                
                # Create and show the visualization
                self.statusBar().showMessage(f'Generating column profile for "{column_name}"...')
                visualize_profile(df, column_name)
                
                # We don't need to store a reference since the UI keeps itself alive
                
                if row_count > 100:
                    self.statusBar().showMessage(f'Column profile generated for "{column_name}" (sampled 100 rows from {row_count})')
                else:
                    self.statusBar().showMessage(f'Column profile generated for "{column_name}"')
            else:
                QMessageBox.warning(self, "Empty Data", "No data available to analyze.")
                self.statusBar().showMessage(f'No data to analyze')
                
        except Exception as e:
            QMessageBox.critical(self, "Analysis Error", f"Error analyzing column:\n\n{str(e)}")
            self.statusBar().showMessage(f'Error analyzing column: {str(e)}')

    def encode_text(self, column_name):
        """Generate one-hot encoding for a text column and visualize the results"""
        try:
            # Get the current tab
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None:
                return
                
            # Show a loading indicator
            self.statusBar().showMessage(f'Preparing one-hot encoding for "{column_name}"...')
            
            # Get the dataframe from the current tab
            full_df = current_tab.current_df.copy()
            df = full_df
            
            # Save original row count for reference
            current_tab.original_df_rowcount = len(full_df)
            
            if df is not None and not df.empty:
                # Sample the data if it's larger than 1000 rows for better performance
                row_count = len(df)
                if row_count > 1000:
                    self.statusBar().showMessage(f'Sampling data (using 1000 rows from {row_count} total)...')
                    
                    # Store the full dataframe before sampling for later use
                    current_tab._original_df_before_encoding = full_df
                    
                    # Sample the data
                    df = df.sample(n=1000, random_state=42)
                
                # Import the one-hot encoding visualizer
                from sqlshell.utils.profile_ohe import visualize_ohe
                
                # Create and show the visualization
                self.statusBar().showMessage(f'Generating one-hot encoding for "{column_name}"...')
                vis = visualize_ohe(df, column_name)
                
                # Connect to the encodingApplied signal
                vis.encodingApplied.connect(self.apply_encoded_dataframe)
                
                # Store a reference to prevent garbage collection
                self._ohe_window = vis
                
                if row_count > 1000:
                    self.statusBar().showMessage(f'One-hot encoding generated for "{column_name}" (sampled 1000 rows from {row_count})')
                else:
                    self.statusBar().showMessage(f'One-hot encoding generated for "{column_name}"')
            else:
                QMessageBox.warning(self, "Empty Data", "No data available to encode.")
                self.statusBar().showMessage(f'No data to encode')
                
        except Exception as e:
            QMessageBox.critical(self, "Encoding Error", f"Error generating one-hot encoding:\n\n{str(e)}")
            self.statusBar().showMessage(f'Error generating one-hot encoding: {str(e)}')
            
    def apply_encoded_dataframe(self, encoded_df):
        """Apply the encoded dataframe to the current tab's results table"""
        try:
            # Get the current tab
            current_tab = self.get_current_tab()
            if not current_tab:
                return
            
            # Check if we're using a sampled version
            is_sampled = False
            full_df = None
            
            # Show a loading indicator
            self.statusBar().showMessage(f'Applying one-hot encoding...')
            
            # Progress dialog for large datasets
            progress = QProgressDialog("Applying encoding...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Processing")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setValue(10)
            
            # Check if this sample is smaller than the actual dataset
            if hasattr(current_tab, '_original_df_before_encoding'):
                # We have the original, full dataset stored
                full_df = current_tab._original_df_before_encoding
                is_sampled = len(full_df) > len(encoded_df)
            elif hasattr(current_tab, 'original_df_rowcount'):
                # We know the original row count but don't have the data
                is_sampled = current_tab.original_df_rowcount > len(encoded_df)
            
            progress.setValue(20)
            QApplication.processEvents()
            
            # If we're working with a sample, apply the encoding to the full dataset
            if is_sampled and full_df is not None:
                self.statusBar().showMessage(f'Re-applying encoding to full dataset ({len(full_df)} rows)...')
                
                try:
                    # Get the encoding columns (added by the OHE process)
                    original_cols = set(current_tab.current_df.columns)
                    ohe_cols = set(encoded_df.columns) - original_cols
                    
                    if ohe_cols:
                        # Import the encoding function to apply to full dataset
                        from sqlshell.utils.profile_ohe import get_ohe
                        
                        # Get the column that was encoded
                        encoded_column = None
                        for col in original_cols:
                            if any(c.startswith(f'is_{col}') for c in ohe_cols) or any(c.startswith(f'has_{col}') for c in ohe_cols):
                                encoded_column = col
                                break
                        
                        progress.setValue(40)
                        QApplication.processEvents()
                        
                        if encoded_column:
                            # Apply encoding to full dataset
                            self.statusBar().showMessage(f'Encoding column "{encoded_column}" on full dataset...')
                            full_encoded_df = get_ohe(full_df, encoded_column)
                            
                            progress.setValue(80)
                            QApplication.processEvents()
                            
                            # Update the current dataframe with the fully encoded one
                            current_tab.current_df = full_encoded_df
                            self.current_df = full_encoded_df  # Keep this for compatibility
                            
                            # Use the full encoded dataframe instead
                            encoded_df = full_encoded_df
                        else:
                            # If we can't determine the encoded column, use the sampled version
                            current_tab.current_df = encoded_df
                            self.current_df = encoded_df  # Keep this for compatibility
                    else:
                        # No encoding columns found, use the sampled version
                        current_tab.current_df = encoded_df
                        self.current_df = encoded_df  # Keep this for compatibility
                except Exception as e:
                    # If there's an error, fall back to the provided encoded_df
                    print(f"Error applying encoding to full dataset: {e}")
                    current_tab.current_df = encoded_df
                    self.current_df = encoded_df  # Keep this for compatibility
            else:
                # No sampling occurred, just use the provided encoded dataframe
                current_tab.current_df = encoded_df
                self.current_df = encoded_df  # Keep this for compatibility
            
            progress.setValue(90)
            QApplication.processEvents()
            
            # Populate the results table with the new dataframe
            self.populate_table(encoded_df)
            
            # Update results title to show this is encoded data
            current_tab.results_title.setText(f"ENCODED DATA")
            
            progress.setValue(100)
            progress.close()
            
            # Update status
            self.statusBar().showMessage(f'Applied one-hot encoding with {len(encoded_df.columns)} columns')
            
            # Check if we should register this as a temporary table
            if len(encoded_df) >= 100:  # Only worth registering as table if it's substantial
                try:
                    # Generate a unique table name
                    import time
                    timestamp = int(time.time())
                    table_name = f"encoded_data_{timestamp}"
                    
                    # Register as a temporary table in the database manager
                    self.db_manager.register_dataframe(encoded_df, table_name, "query_result")
                    
                    # Add to tables list
                    self.tables_list.add_table_item(table_name, "encoded data")
                    
                    # Update completer
                    self.update_completer()
                    
                    # Notify user
                    self.statusBar().showMessage(f'Applied one-hot encoding and registered as table "{table_name}"')
                except Exception as e:
                    # Just log the error but continue - this is an optional enhancement
                    print(f"Error registering encoded dataframe as table: {e}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply encoded dataframe:\n\n{str(e)}")
            self.statusBar().showMessage(f'Error applying encoding: {str(e)}')

    def get_current_query_tab(self):
        """Get the currently active tab if it's a query tab (has query_edit attribute)"""
        current_tab = self.get_current_tab()
        if current_tab and hasattr(current_tab, 'query_edit'):
            return current_tab
        return None

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SQL Shell - SQL Query Tool')
    parser.add_argument('--no-auto-load', action='store_true', 
                        help='Disable auto-loading the most recent project at startup')
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        # Fallback to the main logo if the icon isn't found
        main_logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sqlshell_logo.png")
        if os.path.exists(main_logo_path):
            app.setWindowIcon(QIcon(main_logo_path))
    
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
    
    try:
        # Show splash screen
        splash = AnimatedSplashScreen()
        splash.show()
        
        # Process events immediately to ensure the splash screen appears
        app.processEvents()
        
        # Create main window but don't show it yet
        print("Initializing main application...")
        window = SQLShell()
        
        # Override auto-load setting if command-line argument is provided
        if args.no_auto_load:
            window.auto_load_recent_project = False
            
        # Define the function to show main window and hide splash
        def show_main_window():
            # Properly finish the splash screen
            if splash:
                splash.finish(window)
            
            # Show the main window
            window.show()
            timer.stop()
            
            # Also stop the failsafe timer if it's still running
            if failsafe_timer.isActive():
                failsafe_timer.stop()
                
            print("Main application started")
        
        # Create a failsafe timer in case the splash screen fails to show
        def failsafe_show_window():
            if not window.isVisible():
                print("Failsafe timer activated - showing main window")
                if splash:
                    try:
                        # First try to use the proper finish method
                        splash.finish(window)
                    except Exception as e:
                        print(f"Error in failsafe finish: {e}")
                        try:
                            # Fall back to direct close if finish fails
                            splash.close()
                        except Exception:
                            pass
                window.show()
        
        # Create and show main window after delay
        timer = QTimer()
        timer.setSingleShot(True)  # Ensure it only fires once
        timer.timeout.connect(show_main_window)
        timer.start(2000)  # 2 second delay
        
        # Failsafe timer - show the main window after 5 seconds even if splash screen fails
        failsafe_timer = QTimer()
        failsafe_timer.setSingleShot(True)
        failsafe_timer.timeout.connect(failsafe_show_window)
        failsafe_timer.start(5000)  # 5 second delay
        
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"Error during startup: {e}")
        # If there's any error with the splash screen, just show the main window directly
        window = SQLShell()
        window.show()
        sys.exit(app.exec())

if __name__ == '__main__':
    main() 