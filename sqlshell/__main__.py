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
                           QListWidgetItem, QDialog, QGraphicsDropShadowEffect, QTreeWidgetItem)
from PyQt6.QtCore import Qt, QAbstractTableModel, QRegularExpression, QRect, QSize, QStringListModel, QPropertyAnimation, QEasingCurve, QTimer, QPoint, QMimeData
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat, QPainter, QTextFormat, QTextCursor, QIcon, QPalette, QLinearGradient, QBrush, QPixmap, QPolygon, QPainterPath, QDrag
import numpy as np
from datetime import datetime

from sqlshell import create_test_data
from sqlshell.splash_screen import AnimatedSplashScreen
from sqlshell.syntax_highlighter import SQLSyntaxHighlighter
from sqlshell.editor import LineNumberArea, SQLEditor
from sqlshell.ui import FilterHeader, BarChartDelegate
from sqlshell.db import DatabaseManager
from sqlshell.query_tab import QueryTab
from sqlshell.styles import (get_application_stylesheet, get_tab_corner_stylesheet, 
                           get_context_menu_stylesheet,
                           get_header_label_stylesheet, get_db_info_label_stylesheet, 
                           get_tables_header_stylesheet, get_row_count_label_stylesheet)
from sqlshell.menus import setup_menubar
from sqlshell.table_list import DraggableTablesList
from sqlshell.notification_manager import init_notification_manager, show_error_notification, show_warning_notification, show_info_notification, show_success_notification
from sqlshell.christmas_theme import ChristmasThemeManager
from sqlshell.project_manager import ProjectManager

class SQLShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.current_df = None  # Store the current DataFrame for filtering
        self.filter_widgets = []  # Store filter line edits
        self.current_project_file = None  # Store the current project file path
        self.recent_projects = []  # Store list of recent projects
        self.max_recent_projects = 10  # Maximum number of recent projects to track
        self.tabs = []  # Store list of all tabs
        
        # User preferences
        self.auto_load_recent_project = True  # Default to auto-loading most recent project
        self.christmas_theme_enabled = False  # Christmas theme disabled by default
        
        # File tracking for quick access
        self.recent_files = []  # Store list of recently opened files
        self.frequent_files = {}  # Store file paths with usage counts
        self.max_recent_files = 15  # Maximum number of recent files to track
        # Track in-memory transforms for previewed tables (e.g., deleted columns)
        # Keyed by table name so we can restore the same transformed view when
        # the user navigates away and back without persisting to the database.
        self._preview_transforms = {}
        # Track column renames per table: {table_name: {old_column_name: new_column_name}}
        # This allows us to persist renames across project save/load
        self._column_renames = {}
        
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
        
        # Initialize notification manager
        init_notification_manager(self)
        
        # Initialize Christmas theme manager
        self.christmas_theme_manager = ChristmasThemeManager(self)
        
        # Initialize project manager
        self.project_manager = ProjectManager(self)
        
        # Create initial tab
        self.add_tab()
        
        # Load most recent project if enabled and available
        if self.auto_load_recent_project:
            self.load_most_recent_project()
        
        # Ensure AI autocomplete is properly set up for all editors
        # This must happen after any project loading to register the correct editors
        QTimer.singleShot(100, self.update_completer)
        
        # Enable Christmas theme if it was previously enabled (delay to ensure window is ready)
        if self.christmas_theme_enabled:
            QTimer.singleShot(200, lambda: self.toggle_christmas_theme(True))

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
        
        # Enable drag and drop for files
        self.setAcceptDrops(True)
        
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

        # Left panel for table list (stored as instance var for toggle)
        self.left_panel = QFrame()
        self.left_panel.setObjectName("sidebar")
        self.left_panel.setMinimumWidth(220)
        self.left_panel.setMaximumWidth(350)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        
        # Database info section
        db_header = QLabel("DATABASE")
        db_header.setObjectName("header_label")
        db_header.setStyleSheet(get_header_label_stylesheet())
        left_layout.addWidget(db_header)
        
        self.db_info_label = QLabel("No database connected")
        self.db_info_label.setStyleSheet(get_db_info_label_stylesheet())
        left_layout.addWidget(self.db_info_label)
        
        # Drag and drop info label
        drag_drop_info = QLabel("💡 Drag and drop files here to load them instantly!\nSupported: Excel, CSV, Parquet, SQLite, and more")
        drag_drop_info.setWordWrap(True)
        drag_drop_info.setStyleSheet("color: #52C41A; font-size: 11px; margin-top: 8px; margin-bottom: 8px; background-color: rgba(82, 196, 26, 0.1); padding: 8px; border-radius: 4px; border-left: 3px solid #52C41A;")
        left_layout.addWidget(drag_drop_info)
        
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
        
        # Browse button for quick file selection
        self.browse_button = QPushButton("Browse...  Ctrl+B")
        self.browse_button.setIcon(QIcon.fromTheme("folder-open"))
        self.browse_button.setToolTip("Open data files (Excel, CSV, Parquet) or databases (SQLite, DuckDB)")
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.clicked.connect(self.browse_files)
        self.browse_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.15);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        left_layout.addWidget(self.browse_button)
        
        # Add spacer at the bottom
        left_layout.addStretch()
        
        # Right panel for query tabs and results
        right_panel = QFrame()
        right_panel.setObjectName("content_panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(4)
        
        # Query section header (stored for toggle, hidden by default in favor of tabs)
        self.query_header = QLabel("SQL QUERY")
        self.query_header.setObjectName("header_label")
        self.query_header.setVisible(False)  # Tabs provide context, header is redundant
        right_layout.addWidget(self.query_header)
        
        # Create a compact drop area for tables above the tab widget
        self.tab_drop_area = QFrame()
        self.tab_drop_area.setFixedHeight(22)
        self.tab_drop_area.setObjectName("tab_drop_area")
        
        # Add a label with hint text
        drop_area_layout = QHBoxLayout(self.tab_drop_area)
        drop_area_layout.setContentsMargins(8, 0, 8, 0)
        self.drop_hint_label = QLabel("📂 Drop tables here to create new query tabs")
        self.drop_hint_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        self.drop_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_area_layout.addWidget(self.drop_hint_label)
        
        self.tab_drop_area.setStyleSheet("""
            #tab_drop_area {
                background-color: #fafbfc;
                border: 1px dashed #d0d7de;
                border-radius: 3px;
            }
            
            #tab_drop_area:hover {
                background-color: #ddf4ff;
                border: 1px dashed #0969da;
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

        # Add panels to main layout (sidebar:content ratio 1:5 gives more space to queries)
        main_layout.addWidget(self.left_panel, 1)
        main_layout.addWidget(right_panel, 5)

        # Status bar
        self.statusBar().showMessage('Ready | Ctrl+Enter: Execute Query | Ctrl+K: Toggle Comment | Ctrl+T: New Tab')
        
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
            
            # Calculate chunk size (adjust based on available memory)
            CHUNK_SIZE = 1000
            
            # Process data in chunks to avoid memory issues with large datasets
            for chunk_start in range(0, row_count, CHUNK_SIZE):
                chunk_end = min(chunk_start + CHUNK_SIZE, row_count)
                chunk = df.iloc[chunk_start:chunk_end]
                
                # Add rows for this chunk
                current_tab.results_table.setRowCount(chunk_end)
                
                for row_idx, (_, row_data) in enumerate(chunk.iterrows(), start=chunk_start):
                    for col_idx, value in enumerate(row_data):
                        formatted_value = self.format_value(value)
                        item = QTableWidgetItem(formatted_value)
                        current_tab.results_table.setItem(row_idx, col_idx, item)
                        
                # Process events to keep UI responsive
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
        
        # Database file extensions
        db_extensions = {'.db', '.sqlite', '.sqlite3', '.duckdb'}
            
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Files",
            "",
            "All Supported Files (*.xlsx *.xls *.csv *.txt *.parquet *.db *.sqlite *.sqlite3 *.duckdb);;"
            "Data Files (*.xlsx *.xls *.csv *.txt *.parquet);;"
            "Database Files (*.db *.sqlite *.sqlite3 *.duckdb);;"
            "Excel Files (*.xlsx *.xls);;"
            "CSV Files (*.csv);;"
            "Parquet Files (*.parquet);;"
            "All Files (*)"
        )
        
        for file_name in file_names:
            try:
                # Add to recent files
                self.add_recent_file(file_name)
                
                # Check if this is a database file
                file_ext = os.path.splitext(file_name)[1].lower()
                if file_ext in db_extensions:
                    # Handle database file
                    self._load_database_file(file_name)
                else:
                    # Handle data file (Excel, CSV, Parquet, etc.)
                    self._load_data_file(file_name)
                
            except Exception as e:
                error_msg = f'Error loading file {os.path.basename(file_name)}: {str(e)}'
                self.statusBar().showMessage(error_msg)
                QMessageBox.critical(self, "Error", error_msg)
    
    def _load_data_file(self, file_name):
        """Load a data file (Excel, CSV, Parquet, etc.)"""
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
    
    def _load_database_file(self, file_name):
        """Load a database file (SQLite, DuckDB, etc.)"""
        # Clear existing database tables from the list widget (tables that came from a database)
        for i in range(self.tables_list.topLevelItemCount() - 1, -1, -1):
            item = self.tables_list.topLevelItem(i)
            if item and item.text(0).endswith('(database)'):
                self.tables_list.takeTopLevelItem(i)
        
        # Use the database manager to open the database
        # This attaches the database while preserving loaded files
        self.db_manager.open_database(file_name, load_all_tables=True)
        
        # Update UI with tables from the database
        for table_name, source in self.db_manager.loaded_tables.items():
            # Check if this is a database table (source starts with 'database:')
            if source.startswith('database:'):
                self.tables_list.add_table_item(table_name, "database")
        
        # Update the completer with table and column names
        self.update_completer()
        
        # Update status bar
        self.statusBar().showMessage(f"Connected to database: {file_name}")
        self.db_info_label.setText(self.db_manager.get_connection_info())

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

    def remove_multiple_selected_tables(self, table_items):
        """Remove multiple selected tables from the database and UI"""
        # Extract table names from items
        table_names = []
        for item in table_items:
            table_name = self.tables_list.get_table_name_from_item(item)
            if table_name:
                table_names.append(table_name)
        
        if not table_names:
            return
        
        # Remove tables from database
        successful_removals, failed_removals = self.db_manager.remove_multiple_tables(table_names)
        
        # Remove successfully deleted items from UI
        for item in table_items:
            table_name = self.tables_list.get_table_name_from_item(item)
            if table_name in successful_removals:
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    index = self.tables_list.indexOfTopLevelItem(item)
                    if index >= 0:
                        self.tables_list.takeTopLevelItem(index)
        
        # Update status message
        if successful_removals and failed_removals:
            self.statusBar().showMessage(
                f'Removed {len(successful_removals)} tables successfully. '
                f'Failed to remove {len(failed_removals)} tables: {", ".join(failed_removals)}'
            )
        elif successful_removals:
            self.statusBar().showMessage(f'Successfully removed {len(successful_removals)} tables')
        elif failed_removals:
            self.statusBar().showMessage(f'Failed to remove tables: {", ".join(failed_removals)}')
        
        # Clear results table if needed
        current_tab = self.get_current_tab()
        if current_tab and successful_removals:
            current_tab.results_table.setRowCount(0)
            current_tab.results_table.setColumnCount(0)
            current_tab.row_count_label.setText("")
        
        # Update completer
        if successful_removals:
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
                    
                    # Clear existing database tables from the list widget (tables that came from a database)
                    for i in range(self.tables_list.topLevelItemCount() - 1, -1, -1):
                        item = self.tables_list.topLevelItem(i)
                        if item and item.text(0).endswith('(database)'):
                            self.tables_list.takeTopLevelItem(i)
                    
                    # Use the database manager to open the database
                    # This attaches the database while preserving loaded files
                    self.db_manager.open_database(filename, load_all_tables=True)
                    
                    # Update UI with tables from the database
                    for table_name, source in self.db_manager.loaded_tables.items():
                        # Check if this is a database table (source starts with 'database:')
                        if source.startswith('database:'):
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
                show_warning_notification("Please enter a SQL query to execute.")
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
                
                # Try to determine the source table from the query and tag the dataframe
                try:
                    source_tables = self.extract_table_names_from_query(query)
                    if source_tables:
                        # Use the first table as the primary source
                        primary_table = list(source_tables)[0]
                        if primary_table in self.db_manager.loaded_tables:
                            setattr(result, '_query_source', primary_table)
                except Exception as e:
                    # Don't let table detection errors affect query execution
                    print(f"Warning: Could not determine source table: {e}")
                
                self.populate_table(result)
                
                # User ran their own query, so disable preview mode
                # This means tools should use current_df, not the full table
                current_tab.is_preview_mode = False
                current_tab.preview_table_name = None
                
                self.statusBar().showMessage(f"Query executed successfully. Time: {execution_time:.2f}s. Rows: {len(result)}")
                
                # Show success notification for query execution
                if len(result) > 0:
                    show_success_notification(f"Query executed successfully! Retrieved {len(result):,} rows in {execution_time:.2f}s")
                else:
                    show_info_notification(f"Query completed successfully in {execution_time:.2f}s (no rows returned)")
                
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
                show_error_notification(f"SQL Syntax Error: {str(e)}")
                self.statusBar().showMessage("Query execution failed: syntax error")
            except ValueError as e:
                show_error_notification(f"Query Error: {str(e)}")
                self.statusBar().showMessage("Query execution failed")
            except Exception as e:
                show_error_notification(f"Database Error: {str(e)}")
                self.statusBar().showMessage("Query execution failed")
                
        except Exception as e:
            show_error_notification(f"Unexpected Error: An unexpected error occurred - {str(e)}")
            self.statusBar().showMessage("Query execution failed")

    def execute_specific_query(self, query_text):
        """
        Execute a specific query string (used by F5/F9 functionality).
        
        Args:
            query_text: The specific SQL query string to execute
        """
        try:
            if not query_text.strip():
                show_warning_notification("Cannot execute empty statement.")
                return

            # Check if the query references any tables that need to be loaded
            referenced_tables = self.extract_table_names_from_query(query_text)
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
            
            # Get current tab for resetting preview mode
            current_tab = self.get_current_tab()
            
            try:
                # Use the database manager to execute the query
                result = self.db_manager.execute_query(query_text)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                self.populate_table(result)
                
                # User ran their own query, so disable preview mode
                # This means tools should use current_df, not the full table
                if current_tab:
                    current_tab.is_preview_mode = False
                    current_tab.preview_table_name = None
                
                # Show which statement was executed in status
                query_preview = query_text[:50] + "..." if len(query_text) > 50 else query_text
                self.statusBar().showMessage(f"Statement executed: {query_preview} | Time: {execution_time:.2f}s | Rows: {len(result)}")
                
                # Show success notification for statement execution
                if len(result) > 0:
                    show_success_notification(f"Statement executed successfully! Retrieved {len(result):,} rows in {execution_time:.2f}s")
                else:
                    show_info_notification(f"Statement completed successfully in {execution_time:.2f}s (no rows returned)")
                
                # Record query for context-aware suggestions
                try:
                    from sqlshell.suggester_integration import get_suggestion_manager
                    suggestion_mgr = get_suggestion_manager()
                    suggestion_mgr.record_query(query_text)
                except Exception as e:
                    # Don't let suggestion errors affect query execution
                    print(f"Error recording query for suggestions: {e}")
                
                # Record query in history and update completion usage (legacy)
                self._update_query_history(query_text)
                
            except SyntaxError as e:
                show_error_notification(f"SQL Syntax Error: {str(e)}")
                self.statusBar().showMessage("Statement execution failed: syntax error")
            except ValueError as e:
                show_error_notification(f"Query Error: {str(e)}")
                self.statusBar().showMessage("Statement execution failed")
            except Exception as e:
                show_error_notification(f"Database Error: {str(e)}")
                self.statusBar().showMessage("Statement execution failed")
                
        except Exception as e:
            show_error_notification(f"Unexpected Error: An unexpected error occurred - {str(e)}")
            self.statusBar().showMessage("Statement execution failed")

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
            # Apply any saved column renames to this table if it's loaded
            if table_name not in self.tables_list.tables_needing_reload:
                self._apply_column_renames_to_table(table_name)
            
            # If we have an in-memory transformed version of this table, preview that
            transformed_full = self._preview_transforms.get(table_name)
            if transformed_full is not None:
                preview_df = transformed_full.head()
                self.populate_table(preview_df)
                self.statusBar().showMessage(
                    f'Showing preview of transformed table "{table_name}" (not yet saved to database)'
                )
            else:
                # Use the database manager to get a preview of the table
                preview_df = self.db_manager.get_table_preview(table_name)
                self.populate_table(preview_df)
                self.statusBar().showMessage(f'Showing preview of table "{table_name}"')
            
            # Update the results title to show which table is being previewed
            current_tab.results_title.setText(f"PREVIEW: {table_name}")
            
            # Set preview mode - tools should use full table data, not just the preview
            current_tab.is_preview_mode = True
            current_tab.preview_table_name = table_name
            
        except Exception as e:
            current_tab.results_table.setRowCount(0)
            current_tab.results_table.setColumnCount(0)
            current_tab.row_count_label.setText("")
            self.statusBar().showMessage('Error showing table preview')
            
            # Show error notification
            show_error_notification(f"Error showing preview: {str(e)}")

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
            show_error_notification(f"Failed to load test data: {str(e)}")

    def export_to_excel(self):
        # Get the current tab
        current_tab = self.get_current_tab()
        if not current_tab:
            return
            
        if current_tab.results_table.rowCount() == 0:
            show_warning_notification("There is no data to export.")
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
            table_name = self.db_manager.sanitize_table_name(base_name)
            
            # Ensure unique table name
            original_name = table_name
            counter = 1
            while table_name in self.db_manager.loaded_tables:
                table_name = f"{original_name}_{counter}"
                counter += 1
            
            # Register the table in the database manager
            self.db_manager.register_dataframe(df, table_name, file_name)
            
            # Update tracking
            self.db_manager.loaded_tables[table_name] = file_name
            self.db_manager.table_columns[table_name] = [str(col) for col in df.columns.tolist()]
            
            # Update UI using new method
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
            show_error_notification(f"Failed to export data: {str(e)}")
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
            df = self.get_table_data_as_dataframe()
            df.to_parquet(file_name, index=False)
            
            # Generate table name from file name
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            table_name = self.db_manager.sanitize_table_name(base_name)
            
            # Ensure unique table name
            original_name = table_name
            counter = 1
            while table_name in self.db_manager.loaded_tables:
                table_name = f"{original_name}_{counter}"
                counter += 1
            
            # Register the table in the database manager
            self.db_manager.register_dataframe(df, table_name, file_name)
            
            # Update tracking
            self.db_manager.loaded_tables[table_name] = file_name
            self.db_manager.table_columns[table_name] = [str(col) for col in df.columns.tolist()]
            
            # Update UI using new method
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
            show_error_notification(f"Failed to export data: {str(e)}")
            self.statusBar().showMessage('Error exporting data')

    def save_results_as_table(self, df=None):
        """Save the current query results as a new table (Parquet file) in the database.
        
        The results are saved as a Parquet file so they persist across sessions.
        
        Args:
            df: Optional DataFrame to save. If None, uses current tab's results.
        """
        # If no DataFrame provided, get from current tab
        if df is None:
            current_tab = self.get_current_tab()
            if not current_tab:
                show_warning_notification("No active query tab.")
                return
            
            if not hasattr(current_tab, 'current_df') or current_tab.current_df is None:
                show_warning_notification("No query results to save.")
                return
            
            df = current_tab.current_df
        
        if df.empty:
            show_warning_notification("Results are empty. Nothing to save.")
            return
        
        # Prompt user for file location
        file_name, _ = QFileDialog.getSaveFileName(
            self, 
            f"Save Results as Table ({len(df):,} rows, {len(df.columns)} columns)", 
            "query_result.parquet",
            "Parquet Files (*.parquet);;All Files (*)"
        )
        
        if not file_name:
            return
        
        # Ensure .parquet extension
        if not file_name.lower().endswith('.parquet'):
            file_name += '.parquet'
        
        try:
            # Show loading indicator
            self.statusBar().showMessage('Saving results as table...')
            
            # Save DataFrame as Parquet file (using fastparquet engine for consistency)
            df.to_parquet(file_name, index=False, engine='fastparquet')
            
            # Generate table name from file name
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            table_name = self.db_manager.sanitize_table_name(base_name)
            
            # Ensure unique table name
            original_name = table_name
            counter = 1
            while table_name in self.db_manager.loaded_tables:
                table_name = f"{original_name}_{counter}"
                counter += 1
            
            # Register the table in the database manager with the file path
            self.db_manager.register_dataframe(df, table_name, file_name)
            
            # Update tracking with file path (so it can be reloaded)
            self.db_manager.loaded_tables[table_name] = file_name
            self.db_manager.table_columns[table_name] = [str(col) for col in df.columns.tolist()]
            
            # Add to the tables list in UI
            self.tables_list.add_table_item(table_name, os.path.basename(file_name))
            
            # Update completer with new table and column names
            self.update_completer()
            
            # Show success message
            self.statusBar().showMessage(
                f'Results saved as table "{table_name}" ({len(df):,} rows)'
            )
            
            QMessageBox.information(
                self,
                "Table Created",
                f"Query results have been saved as:\n\n"
                f"File: {file_name}\n"
                f"Table: {table_name}\n\n"
                f"Rows: {len(df):,}\nColumns: {len(df.columns)}\n\n"
                "You can now query this table like any other table.\n"
                "The file will be available when you reopen SQLShell.",
                QMessageBox.StandardButton.Ok
            )
            
        except Exception as e:
            show_error_notification(f"Failed to save as table: {str(e)}")
            self.statusBar().showMessage('Error saving results as table')

    def paste_data_from_clipboard(self):
        """Paste tabular data from clipboard and create a new table.
        
        This method:
        - Verifies that clipboard contains tabular data
        - Auto-detects format (tab, comma, semicolon, pipe separated)
        - Auto-detects if first row is a header
        - Prompts user for table name
        - Creates the table and adds it to the database
        """
        from PyQt6.QtWidgets import QApplication
        from sqlshell.utils.clipboard_data_parser import ClipboardDataParser
        
        # Get clipboard text
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        if not text or not text.strip():
            show_warning_notification("Clipboard is empty")
            return
        
        # Quick verification that it looks like data
        if not ClipboardDataParser.is_likely_data(text):
            show_warning_notification(
                "Clipboard content doesn't appear to be tabular data.\n"
                "Please copy data from a spreadsheet, CSV file, or similar tabular source."
            )
            return
        
        # Parse the data
        df, message = ClipboardDataParser.parse_clipboard_data(text)
        
        if df is None:
            show_error_notification(f"Could not parse clipboard data: {message}")
            return
        
        # Show preview and ask for confirmation
        preview = ClipboardDataParser.get_data_preview(df, max_rows=5)
        
        # Prompt for table name
        table_name, ok = QInputDialog.getText(
            self,
            "Paste Data as Table",
            f"Data detected: {message}\n\n"
            f"Preview (first 5 rows):\n{preview}\n\n"
            f"Enter a name for the new table:",
            text="clipboard_data"
        )
        
        if not ok or not table_name:
            return
        
        # Sanitize and ensure unique table name
        table_name = self.db_manager.sanitize_table_name(table_name)
        original_name = table_name
        counter = 1
        while table_name in self.db_manager.loaded_tables:
            table_name = f"{original_name}_{counter}"
            counter += 1
        
        try:
            # Register the DataFrame in the database
            self.db_manager.register_dataframe(df, table_name, 'clipboard')
            
            # Update tracking
            self.db_manager.loaded_tables[table_name] = 'clipboard'
            self.db_manager.table_columns[table_name] = [str(col) for col in df.columns.tolist()]
            
            # Add to the tables list in UI
            self.tables_list.add_table_item(table_name, f"📋 {table_name}")
            
            # Update completer with new table and column names
            self.update_completer()
            
            # Show success message
            show_success_notification(
                f'Created table "{table_name}" with {len(df):,} rows × {len(df.columns)} columns'
            )
            self.statusBar().showMessage(
                f'Pasted data as table "{table_name}" ({len(df):,} rows, {len(df.columns)} columns)'
            )
            
        except Exception as e:
            show_error_notification(f"Failed to create table from clipboard: {str(e)}")
            self.statusBar().showMessage('Error pasting clipboard data')

    def get_table_data_as_dataframe(self):
        """Helper function to convert table widget data to a DataFrame with proper data types"""
        # Get the current tab
        current_tab = self.get_current_tab()
        if not current_tab:
            return pd.DataFrame()
            
        headers = [current_tab.results_table.horizontalHeaderItem(i).text() for i in range(current_tab.results_table.columnCount())]
        data = []
        for row in range(current_tab.results_table.rowCount()):
            row_data = []
            for column in range(current_tab.results_table.columnCount()):
                item = current_tab.results_table.item(row, column)
                row_data.append(item.text() if item else '')
            data.append(row_data)
        
        # Create DataFrame from raw string data
        df_raw = pd.DataFrame(data, columns=headers)
        
        # Try to use the original dataframe's dtypes if available
        if hasattr(current_tab, 'current_df') and current_tab.current_df is not None:
            original_df = current_tab.current_df
            # Since we might have filtered rows, we can't just return the original DataFrame
            # But we can use its column types to convert our string data appropriately
            
            # Create a new DataFrame with appropriate types
            df_typed = pd.DataFrame()
            
            for col in df_raw.columns:
                if col in original_df.columns:
                    # Get the original column type
                    orig_type = original_df[col].dtype
                    
                    # Special handling for different data types
                    if pd.api.types.is_numeric_dtype(orig_type):
                        # Handle numeric columns (int or float)
                        try:
                            # First try to convert to numeric type
                            # Remove commas used for thousands separators
                            numeric_col = pd.to_numeric(df_raw[col].str.replace(',', '').replace('NULL', np.nan))
                            df_typed[col] = numeric_col
                        except:
                            # If that fails, keep the original string
                            df_typed[col] = df_raw[col]
                    elif pd.api.types.is_datetime64_dtype(orig_type):
                        # Handle datetime columns
                        try:
                            df_typed[col] = pd.to_datetime(df_raw[col].replace('NULL', np.nan))
                        except:
                            df_typed[col] = df_raw[col]
                    elif pd.api.types.is_bool_dtype(orig_type):
                        # Handle boolean columns
                        try:
                            df_typed[col] = df_raw[col].map({'True': True, 'False': False}).replace('NULL', np.nan)
                        except:
                            df_typed[col] = df_raw[col]
                    else:
                        # For other types, keep as is
                        df_typed[col] = df_raw[col]
                else:
                    # For columns not in the original dataframe, infer type
                    df_typed[col] = df_raw[col]
                    
            return df_typed
            
        else:
            # If we don't have the original dataframe, try to infer types
            # First replace 'NULL' with actual NaN
            df_raw.replace('NULL', np.nan, inplace=True)
            
            # Try to convert each column to numeric if possible
            for col in df_raw.columns:
                try:
                    # First try to convert to numeric by removing commas
                    df_raw[col] = pd.to_numeric(df_raw[col].str.replace(',', ''))
                except:
                    # If that fails, try to convert to datetime
                    try:
                        df_raw[col] = pd.to_datetime(df_raw[col])
                    except:
                        # If both numeric and datetime conversions fail,
                        # try boolean conversion for True/False strings
                        try:
                            if df_raw[col].dropna().isin(['True', 'False']).all():
                                df_raw[col] = df_raw[col].map({'True': True, 'False': False})
                        except:
                            # Otherwise, keep as is
                            pass
            
            return df_raw

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
        
        # Search in results with Ctrl+F
        if event.key() == Qt.Key.Key_F and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.show_search_dialog()
            return
        
        # Clear search with ESC key (only if search is active)
        if event.key() == Qt.Key.Key_Escape:
            current_tab = self.get_current_tab()
            if current_tab and "SEARCH RESULTS:" in current_tab.results_title.text():
                self.clear_search()
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

    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        # Update Christmas theme decorations when window is resized
        if hasattr(self, 'christmas_theme_manager') and self.christmas_theme_manager.enabled:
            self.christmas_theme_manager.update_positions()

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
                
                context_menu.addSeparator()
                
                # Add Set Operations submenu (UNION, UNION ALL, EXCEPT, INTERSECT)
                set_ops_menu = context_menu.addMenu(f"Combine {len(table_items)} Tables (Set Operations)")
                set_ops_menu.setIcon(QIcon.fromTheme("view-split-left-right"))
                
                union_all_action = set_ops_menu.addAction("UNION ALL - Combine all rows (keeps duplicates)")
                union_action = set_ops_menu.addAction("UNION - Combine rows (removes duplicates)")
                except_action = set_ops_menu.addAction("EXCEPT - Rows in first but not others")
                intersect_action = set_ops_menu.addAction("INTERSECT - Only rows in all tables")
                
                # Add Join All Tables option
                join_menu = context_menu.addMenu(f"Join {len(table_items)} Tables")
                join_menu.setIcon(QIcon.fromTheme("insert-link"))
                
                inner_join_action = join_menu.addAction("INNER JOIN - Only matching rows")
                left_join_action = join_menu.addAction("LEFT JOIN - All from first, matching from others")
                right_join_action = join_menu.addAction("RIGHT JOIN - All from last, matching from others")
                full_join_action = join_menu.addAction("FULL JOIN - All rows from all tables")
                
                # Add Compare Datasets option
                context_menu.addSeparator()
                compare_datasets_action = context_menu.addAction(f"Compare {len(table_items)} Datasets")
                compare_datasets_action.setIcon(QIcon.fromTheme("edit-find-replace"))
                
                # Add separator and delete option
                context_menu.addSeparator()
                delete_multiple_action = context_menu.addAction(f"Delete {len(table_items)} Tables")
                delete_multiple_action.setIcon(QIcon.fromTheme("edit-delete"))
                
                # Show menu and get selected action
                action = context_menu.exec(self.tables_list.mapToGlobal(position))
                
                if action == analyze_fk_action:
                    self.analyze_foreign_keys_between_tables(table_items)
                elif action == union_all_action:
                    self.generate_set_operation_for_tables(table_items, 'UNION ALL')
                elif action == union_action:
                    self.generate_set_operation_for_tables(table_items, 'UNION')
                elif action == except_action:
                    self.generate_set_operation_for_tables(table_items, 'EXCEPT')
                elif action == intersect_action:
                    self.generate_set_operation_for_tables(table_items, 'INTERSECT')
                elif action == inner_join_action:
                    self.generate_join_for_tables(table_items, 'INNER')
                elif action == left_join_action:
                    self.generate_join_for_tables(table_items, 'LEFT')
                elif action == right_join_action:
                    self.generate_join_for_tables(table_items, 'RIGHT')
                elif action == full_join_action:
                    self.generate_join_for_tables(table_items, 'FULL')
                elif action == compare_datasets_action:
                    self.compare_datasets_for_tables(table_items)
                elif action == delete_multiple_action:
                    # Show confirmation dialog
                    table_names = [self.tables_list.get_table_name_from_item(item) for item in table_items]
                    table_names = [name for name in table_names if name]  # Remove None values
                    
                    if table_names:
                        reply = QMessageBox.question(
                            self,
                            "Delete Multiple Tables",
                            f"Are you sure you want to delete these {len(table_names)} tables?\n\n" +
                            "\n".join(f"• {name}" for name in table_names[:10]) +
                            (f"\n... and {len(table_names) - 10} more" if len(table_names) > 10 else ""),
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.No
                        )
                        
                        if reply == QMessageBox.StandardButton.Yes:
                            self.remove_multiple_selected_tables(table_items)
                
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
        profile_table_action = context_menu.addAction("Find Keys")
        profile_table_action.setIcon(QIcon.fromTheme("edit-find"))
        
        # Add distributions profiler action
        profile_distributions_action = context_menu.addAction("Analyze Column Distributions")
        profile_distributions_action.setIcon(QIcon.fromTheme("accessories-calculator"))
        
        # Add similarity profiler action
        profile_similarity_action = context_menu.addAction("Analyze Row Similarity")
        profile_similarity_action.setIcon(QIcon.fromTheme("applications-utilities"))

        # Transform submenu for table-level operations
        transform_menu = context_menu.addMenu("Transform")
        convert_query_names_action = transform_menu.addAction(
            "Convert Column Names to Query-Friendly (lowercase_with_underscores, trimmed)"
        )
        
        # Check if table needs reloading and add appropriate action
        if table_name in self.tables_list.tables_needing_reload:
            reload_action = context_menu.addAction("Reload Table")
            reload_action.setIcon(QIcon.fromTheme("view-refresh"))
        else:
            reload_action = context_menu.addAction("Refresh")
            reload_action.setIcon(QIcon.fromTheme("view-refresh"))
        
        # Add change source action for file-based tables
        change_source_action = None
        if table_name in self.db_manager.loaded_tables:
            source_path = self.db_manager.loaded_tables[table_name]
            if source_path not in ['database', 'query_result']:
                change_source_action = context_menu.addAction("Change Table Source...")
                change_source_action.setIcon(QIcon.fromTheme("document-open"))
        
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
            # Create a new tab with "SELECT * FROM table_name" and execute it with LIMIT 20
            new_tab = self.add_tab(f"Query {table_name}")
            query_with_limit = f"SELECT * FROM {table_name} LIMIT 20"
            new_tab.set_query_text(query_with_limit)
            new_tab.query_edit.setFocus()
            
            # Automatically execute the query
            self.execute_query()
        elif action == reload_action:
            self.reload_selected_table(table_name)
        elif change_source_action and action == change_source_action:
            self.change_table_source(table_name, item)
        elif action == copy_path_action:
            # Get the full path from the table source
            if table_name in self.db_manager.loaded_tables:
                path = self.db_manager.loaded_tables[table_name]
                if path != 'database':  # Only copy if it's a file path
                    QApplication.clipboard().setText(path)
                    self.statusBar().showMessage(f"Copied full path to clipboard")
                else:
                    self.statusBar().showMessage("Table is from database - no file path to copy")
            else:
                self.statusBar().showMessage("No path information available for this table")
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
                else:
                    self.statusBar().showMessage("Table is from database - no file path to copy")
            else:
                self.statusBar().showMessage("No path information available for this table")
        elif action == analyze_entropy_action:
            # Call the entropy analysis method
            self.analyze_table_entropy(table_name)
        elif action == profile_table_action:
            # Call the table profile method
            self.profile_table_structure(table_name)
        elif action == profile_distributions_action:
            # Call the distributions profile method
            self.profile_distributions(table_name)
        elif action == profile_similarity_action:
            # Call the similarity profile method
            self.profile_similarity(table_name)
        elif action == convert_query_names_action:
            # Apply query-friendly column name transform to this table
            self.convert_to_query_friendly_names(table_name)
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
                    # For database tables, use qualified name (e.g., db.table_name)
                    source = self.db_manager.loaded_tables[table_name]
                    if source.startswith('database:'):
                        alias = source.split(':')[1]
                        query = f'SELECT * FROM {alias}."{table_name}"'
                    else:
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
            
            # Define callback to handle generated JOIN queries
            def on_generate_join(query):
                current_tab = self.get_current_query_tab()
                if current_tab:
                    # Add the generated query to the editor
                    current_text = current_tab.query_edit.toPlainText()
                    # Add a new line if there's already content
                    if current_text and not current_text.endswith("\n"):
                        current_tab.query_edit.setPlainText(current_text + "\n" + query)
                    else:
                        current_tab.query_edit.setPlainText(current_text + query)
                    # Set focus to the query editor
                    current_tab.query_edit.setFocus()
            
            # Create and show the visualization
            self.statusBar().showMessage(f'Analyzing foreign key relationships between {len(dfs)} tables...')
            vis = visualize_foreign_keys(
                dfs, 
                table_names, 
                on_generate_join=on_generate_join,
                parent=self
            )
            
            # Store a reference to prevent garbage collection
            self._fk_analysis_window = vis
            
            self.statusBar().showMessage(f'Foreign key analysis complete for {len(dfs)} tables')
            
        except Exception as e:
            show_error_notification(f"Analysis Error: Error analyzing foreign keys - {str(e)}")
            self.statusBar().showMessage(f'Error analyzing foreign keys: {str(e)}')

    def generate_set_operation_for_tables(self, table_items, operation):
        """Generate a SQL set operation (UNION, UNION ALL, EXCEPT, INTERSECT) for selected tables"""
        try:
            from sqlshell.utils.table_set_operations import generate_set_operation_sql, find_common_columns
            
            # Extract table names from selected items
            table_names = []
            for item in table_items:
                table_name = self.tables_list.get_table_name_from_item(item)
                if table_name:
                    table_names.append(table_name)
            
            if len(table_names) < 2:
                QMessageBox.warning(self, "Not Enough Tables", 
                                    "At least two tables are required for set operations.")
                return
            
            # Check for common columns first
            common_cols = find_common_columns(self.db_manager, table_names)
            if not common_cols:
                QMessageBox.warning(self, "No Common Columns", 
                                    f"The selected tables have no common columns.\n\n"
                                    f"Set operations ({operation}) require tables to have "
                                    "at least one column with the same name.")
                return
            
            # Generate the SQL
            sql = generate_set_operation_sql(self.db_manager, table_names, operation)
            
            # Add the SQL to the current query editor
            current_tab = self.get_current_query_tab()
            if current_tab:
                current_text = current_tab.query_edit.toPlainText()
                # Add a new line if there's already content
                if current_text and not current_text.endswith("\n"):
                    current_tab.query_edit.setPlainText(current_text + "\n\n" + sql)
                else:
                    current_tab.query_edit.setPlainText(current_text + sql)
                # Set focus to the query editor
                current_tab.query_edit.setFocus()
                
                self.statusBar().showMessage(
                    f'{operation} query generated for {len(table_names)} tables '
                    f'using {len(common_cols)} common columns: {", ".join(common_cols[:5])}'
                    + ('...' if len(common_cols) > 5 else '')
                )
            
        except ValueError as e:
            QMessageBox.warning(self, "Set Operation Error", str(e))
        except Exception as e:
            show_error_notification(f"Error: {str(e)}")
            self.statusBar().showMessage(f'Error generating {operation} query: {str(e)}')

    def generate_join_for_tables(self, table_items, join_type):
        """Generate a JOIN query for selected tables with inferred relationships"""
        try:
            from sqlshell.utils.table_join_operations import generate_join_sql, infer_table_relationships
            
            # Extract table names from selected items
            table_names = []
            for item in table_items:
                table_name = self.tables_list.get_table_name_from_item(item)
                if table_name:
                    table_names.append(table_name)
            
            if len(table_names) < 2:
                QMessageBox.warning(self, "Not Enough Tables", 
                                    "At least two tables are required for JOIN operations.")
                return
            
            # Check for relationships first
            relationships = infer_table_relationships(self.db_manager, table_names)
            if not relationships:
                QMessageBox.warning(self, "No Relationships Found", 
                                    f"Could not infer any relationships between the selected tables.\n\n"
                                    "For automatic JOIN generation, tables should have:\n"
                                    "• Columns with matching names (e.g., 'user_id' in both tables)\n"
                                    "• Foreign key naming patterns (e.g., 'customer_id' referencing 'customers.id')")
                return
            
            # Generate the SQL
            sql = generate_join_sql(self.db_manager, table_names, join_type, relationships)
            
            # Add the SQL to the current query editor
            current_tab = self.get_current_query_tab()
            if current_tab:
                current_text = current_tab.query_edit.toPlainText()
                # Add a new line if there's already content
                if current_text and not current_text.endswith("\n"):
                    current_tab.query_edit.setPlainText(current_text + "\n\n" + sql)
                else:
                    current_tab.query_edit.setPlainText(current_text + sql)
                # Set focus to the query editor
                current_tab.query_edit.setFocus()
                
                # Build a description of the relationships found
                rel_desc = []
                for rel in relationships[:3]:
                    rel_desc.append(f"{rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']}")
                
                self.statusBar().showMessage(
                    f'{join_type} JOIN query generated for {len(table_names)} tables. '
                    f'Relationships: {"; ".join(rel_desc)}'
                    + ('...' if len(relationships) > 3 else '')
                )
            
        except ValueError as e:
            QMessageBox.warning(self, "Join Error", str(e))
        except Exception as e:
            show_error_notification(f"Error: {str(e)}")
            self.statusBar().showMessage(f'Error generating {join_type} JOIN query: {str(e)}')

    def compare_datasets_for_tables(self, table_items):
        """Compare datasets using pandas with visual difference display"""
        try:
            from sqlshell.utils.profile_compare import compare_datasets, DatasetComparator
            
            # Extract table names from selected items
            table_names = []
            for item in table_items:
                table_name = self.tables_list.get_table_name_from_item(item)
                if table_name:
                    table_names.append(table_name)
            
            if len(table_names) < 2:
                QMessageBox.warning(self, "Not Enough Tables", 
                                    "At least two tables are required for dataset comparison.")
                return
            
            # Load dataframes for each table
            dataframes = []
            for table_name in table_names:
                try:
                    # Get dataframe from database manager
                    source = self.db_manager.loaded_tables.get(table_name, '')
                    if source.startswith('database:'):
                        alias = source.split(':')[1]
                        query = f'SELECT * FROM {alias}."{table_name}"'
                    else:
                        query = f'SELECT * FROM "{table_name}"'
                    
                    df = self.db_manager.execute_query(query)
                    dataframes.append(df)
                except Exception as e:
                    QMessageBox.warning(self, "Load Error", 
                                        f"Could not load table '{table_name}': {str(e)}")
                    return
            
            # Find common columns
            common_cols = set(dataframes[0].columns)
            for df in dataframes[1:]:
                common_cols = common_cols.intersection(set(df.columns))
            
            if not common_cols:
                QMessageBox.warning(self, "No Common Columns", 
                                    f"The selected tables have no common columns.\n\n"
                                    "Dataset comparison requires tables to have at least one "
                                    "column with the same name to use as join keys.")
                return
            
            self.statusBar().showMessage(f'Comparing {len(table_names)} datasets...')
            
            # Perform comparison and show results
            results, widget = compare_datasets(
                dataframes, 
                names=table_names, 
                key_columns=list(common_cols),
                parent=self,
                show_window=True
            )
            
            if "error" in results:
                QMessageBox.warning(self, "Comparison Error", results["error"])
                return
            
            # Store reference to keep widget alive
            if not hasattr(self, '_comparison_widgets'):
                self._comparison_widgets = []
            self._comparison_widgets.append(widget)
            
            stats = results.get('summary_stats', {})
            self.statusBar().showMessage(
                f'Comparison complete: {stats.get("total_rows", 0)} total rows, '
                f'{stats.get("indicator_counts", {}).get("all", 0)} matching in all datasets'
            )
            
        except ImportError as e:
            QMessageBox.warning(self, "Import Error", 
                                f"Could not import comparison module: {str(e)}")
        except Exception as e:
            show_error_notification(f"Error: {str(e)}")
            self.statusBar().showMessage(f'Error comparing datasets: {str(e)}')

    def _apply_column_renames_to_table(self, table_name):
        """Apply saved column renames to a table if they exist"""
        if not hasattr(self, '_column_renames') or table_name not in self._column_renames:
            return False
        
        rename_map = self._column_renames[table_name]
        if not rename_map:
            return False
        
        try:
            # Get the current table data
            table_df = self.db_manager.get_full_table(table_name)
            
            # Build rename dictionary - only include renames that are still valid
            rename_dict = {}
            for old_name, new_name in rename_map.items():
                if old_name in table_df.columns and new_name not in table_df.columns:
                    rename_dict[old_name] = new_name
            
            if rename_dict:
                # Apply the renames
                renamed_df = table_df.rename(columns=rename_dict)
                
                # Update the table in DuckDB
                # Use 'transformed' source instead of preserving 'database:' source
                # This ensures _qualify_table_names won't rewrite queries to db.<table>
                self.db_manager.overwrite_table_with_dataframe(table_name, renamed_df, source='transformed')
                
                # Update table_columns tracking
                if table_name in self.db_manager.table_columns:
                    columns = self.db_manager.table_columns[table_name]
                    updated_columns = []
                    for col in columns:
                        if col in rename_dict:
                            updated_columns.append(rename_dict[col])
                        else:
                            updated_columns.append(col)
                    self.db_manager.table_columns[table_name] = updated_columns
                
                # Update preview transforms if it exists
                if table_name in self._preview_transforms:
                    self._preview_transforms[table_name] = renamed_df
                
                return True
        except Exception as e:
            print(f"Warning: Could not apply column renames to table '{table_name}': {e}")
        
        return False

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
                # Apply any saved column renames to this table
                self._apply_column_renames_to_table(table_name)
                
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
                show_warning_notification(f"Reload Failed: {message}")
                self.statusBar().showMessage(f'Failed to reload table: {message}')
                
        except Exception as e:
            show_error_notification(f"Error reloading table: {str(e)}")
            self.statusBar().showMessage('Error reloading table')

    def change_table_source(self, table_name, item):
        """Change the source file for a table (useful when files have been moved)"""
        try:
            # Get the current file path
            if table_name not in self.db_manager.loaded_tables:
                show_warning_notification("Table source not found")
                return
            
            current_path = self.db_manager.loaded_tables[table_name]
            
            # Determine the starting directory for the file dialog
            if os.path.exists(current_path):
                start_dir = os.path.dirname(current_path)
            else:
                start_dir = ""
            
            # Get the file extension to filter by same type
            current_ext = os.path.splitext(current_path)[1].lower()
            
            # Build file filter based on current file type
            if current_ext in ['.xlsx', '.xls']:
                file_filter = "Excel Files (*.xlsx *.xls);;All Files (*)"
            elif current_ext in ['.csv', '.txt']:
                file_filter = "CSV/Text Files (*.csv *.txt);;All Files (*)"
            elif current_ext == '.parquet':
                file_filter = "Parquet Files (*.parquet);;All Files (*)"
            else:
                file_filter = "Data Files (*.xlsx *.xls *.csv *.txt *.parquet);;All Files (*)"
            
            # Open file dialog
            new_path, _ = QFileDialog.getOpenFileName(
                self,
                f"Select new source file for '{table_name}'",
                start_dir,
                file_filter
            )
            
            if not new_path:
                return  # User cancelled
            
            # Verify the file exists
            if not os.path.exists(new_path):
                show_warning_notification("Selected file does not exist")
                return
            
            # Update the source path in the database manager
            self.db_manager.loaded_tables[table_name] = new_path
            
            # Update the item text in the tree widget
            new_source = os.path.basename(new_path)
            item.setText(0, f"{table_name} ({new_source})")
            
            # Mark as needing reload so user knows data needs to be refreshed
            self.tables_list.mark_table_needs_reload(table_name)
            
            # Show success message
            self.statusBar().showMessage(f'Changed source for "{table_name}" to {new_source}. Reload to update data.')
            
            # Ask if they want to reload now
            reply = QMessageBox.question(
                self,
                "Reload Table?",
                f"Source file for '{table_name}' has been changed.\n\nWould you like to reload the table now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.reload_selected_table(table_name)
                
        except Exception as e:
            show_error_notification(f"Error changing table source: {str(e)}")
            self.statusBar().showMessage('Error changing table source')

    def new_project(self, skip_confirmation=False):
        """Create a new project by clearing current state"""
        self.project_manager.new_project(skip_confirmation=skip_confirmation)

    def save_project(self):
        """Save the current project"""
        self.project_manager.save_project()

    def save_project_as(self):
        """Save the current project to a new file"""
        self.project_manager.save_project_as()

    def save_project_to_file(self, file_name):
        """Save project data to a file"""
        self.project_manager.save_project_to_file(file_name)

    def open_project(self, file_name=None):
        """Open a project file"""
        self.project_manager.open_project(file_name)

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
            show_error_notification(f"Error: Failed to rename table - {str(e)}")
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
                    self.christmas_theme_enabled = preferences.get('christmas_theme_enabled', False)
                    
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
            settings['preferences']['christmas_theme_enabled'] = self.christmas_theme_enabled
            
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
                    if source.startswith('database:'):
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

        
    def show_search_dialog(self):
        """Show search dialog and search in current results"""
        # Get current tab and check if it has results
        current_tab = self.get_current_tab()
        if not current_tab or current_tab.current_df is None or current_tab.current_df.empty:
            QMessageBox.information(self, "Search", "No data to search. Please execute a query first.")
            return
        
        # Create a custom dialog with search options
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Search in Results")
        dialog.setLabelText("Enter text to search for:")
        dialog.setTextValue("")
        dialog.resize(400, 150)
        
        # Add a checkbox for case sensitivity (though we default to case-insensitive)
        # For now, keep it simple with just the text input
        
        if dialog.exec() == QInputDialog.DialogCode.Accepted:
            search_text = dialog.textValue().strip()
            if search_text:
                self.search_in_results(search_text)
            else:
                # If empty search, offer to clear current search
                if "SEARCH RESULTS:" in current_tab.results_title.text():
                    reply = QMessageBox.question(self, "Clear Search", 
                        "Clear current search and show all results?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        self.clear_search()
    
    def search_in_results(self, search_text):
        """Search in current results using the optimized search function"""
        try:
            # Get current tab
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None:
                return
            
            # Import the search function
            from sqlshell.utils.search_in_df import search_optimized
            
            # Perform the search
            filtered_df = search_optimized(current_tab.current_df, search_text, case_sensitive=False)
            
            if filtered_df.empty:
                QMessageBox.information(self, "Search Results", f"No results found for '{search_text}'")
                return
            
            # Update the table with search results
            self.populate_table(filtered_df)
            
            # Update results title to show search
            current_tab.results_title.setText(f"SEARCH RESULTS: '{search_text}'")
            
            # Update status
            total_rows = len(current_tab.current_df)
            found_rows = len(filtered_df)
            self.statusBar().showMessage(f"Search found {found_rows:,} of {total_rows:,} rows matching '{search_text}' (Ctrl+F to search again)")
            
        except Exception as e:
            show_error_notification(f"Search Error: An error occurred while searching - {str(e)}")
            self.statusBar().showMessage(f"Search failed: {str(e)}")
    
    def clear_search(self):
        """Clear search results and show all original data"""
        try:
            # Get current tab
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None:
                return
            
            # Restore original data
            self.populate_table(current_tab.current_df)
            
            # Reset results title
            current_tab.results_title.setText("RESULTS")
            
            # Update status
            total_rows = len(current_tab.current_df)
            self.statusBar().showMessage(f"Showing all {total_rows:,} rows")
            
        except Exception as e:
            show_error_notification(f"Clear Search Error: An error occurred while clearing search - {str(e)}")
            self.statusBar().showMessage(f"Clear search failed: {str(e)}")

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

    def delete_column(self, column_name):
        """Delete a column from the current results table and refresh the view."""
        try:
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None:
                show_warning_notification("No data available. Please run a query or open a table before deleting columns.")
                return

            # Handle preview-mode tables separately from query results
            if current_tab.is_preview_mode and current_tab.preview_table_name:
                table_name = current_tab.preview_table_name

                # Work on the full underlying table, not just the 5-row preview.
                # Prefer any existing in-memory transformed version for this table.
                base_df = self._preview_transforms.get(table_name)
                if base_df is None:
                    try:
                        base_df = self.db_manager.get_full_table(table_name)
                    except Exception as e:
                        show_error_notification(
                            f"Delete Column Error: Could not load full table '{table_name}' - {str(e)}"
                        )
                        return

                if column_name not in base_df.columns:
                    show_warning_notification(f"Column '{column_name}' not found in the current table.")
                    return

                # Apply the delete to the full dataset and remember it for future tools
                updated_full_df = base_df.drop(columns=[column_name])
                self._preview_transforms[table_name] = updated_full_df

                # Update the table in DuckDB so SQL queries work immediately
                # Use 'transformed' source instead of preserving 'database:' source
                # This ensures _qualify_table_names won't rewrite queries to db.<table>
                try:
                    self.db_manager.overwrite_table_with_dataframe(table_name, updated_full_df, source='transformed')
                    # Update table_columns tracking
                    if table_name in self.db_manager.table_columns:
                        self.db_manager.table_columns[table_name] = [col for col in self.db_manager.table_columns[table_name] if col != column_name]
                except Exception as e:
                    # Log but don't fail - the delete still worked in the UI
                    print(f"Warning: Could not update table in database: {e}")

                # Keep showing a small preview in the UI, but based on the updated full data
                preview_df = updated_full_df.head()
                self.populate_table(preview_df)
            else:
                # Non-preview mode: operate directly on the current query results
                df = current_tab.current_df
                if column_name not in df.columns:
                    show_warning_notification(f"Column '{column_name}' not found in the current results.")
                    return

                updated_df = df.drop(columns=[column_name])
                current_tab.current_df = updated_df

                # Refresh the table display with the full (query) results
                self.populate_table(updated_df)

            # Determine current column count for messaging
            if current_tab.is_preview_mode and current_tab.preview_table_name:
                table_name = current_tab.preview_table_name
                transformed = self._preview_transforms.get(table_name)
                col_count = len(transformed.columns) if transformed is not None else 0
            else:
                col_count = len(current_tab.current_df.columns) if current_tab.current_df is not None else 0

            # Inform user about the deletion and remind them to persist changes
            message = (
                f"Deleted column '{column_name}'. Table now has {col_count} columns. "
                "Remember to use 'Save as Table' if you want to persist this change."
            )
            self.statusBar().showMessage(message)
            try:
                # Also show a non-intrusive notification if available
                show_info_notification(
                    "Column Deleted",
                    "The column was removed from the current results. "
                    "To avoid losing this change, use the 'Save as Table' option to save it back to the database."
                )
            except Exception:
                # Notifications are optional; ignore failures here
                pass
        except Exception as e:
            show_error_notification(f"Delete Column Error: Could not delete column '{column_name}' - {str(e)}")
            self.statusBar().showMessage(f"Error deleting column '{column_name}': {str(e)}")

    def rename_column(self, old_column_name, new_column_name):
        """Rename a column in the current results table and refresh the view."""
        try:
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None:
                show_warning_notification("No data available. Please run a query or open a table before renaming columns.")
                return

            # Validate the new name
            if not new_column_name or new_column_name.strip() == "":
                show_warning_notification("Column name cannot be empty.")
                return

            # Determine the source table name for updating the database schema
            source_table_name = None
            if current_tab.is_preview_mode and current_tab.preview_table_name:
                source_table_name = current_tab.preview_table_name
            elif hasattr(current_tab.current_df, '_query_source'):
                source_table_name = getattr(current_tab.current_df, '_query_source')
            else:
                # Try to extract table name from current query
                query_text = current_tab.get_query_text() if hasattr(current_tab, 'get_query_text') else ""
                if query_text:
                    source_tables = self.extract_table_names_from_query(query_text)
                    if source_tables:
                        # Use the first table found
                        potential_table = list(source_tables)[0]
                        if potential_table in self.db_manager.loaded_tables:
                            source_table_name = potential_table

            # Handle preview-mode tables separately from query results
            if current_tab.is_preview_mode and current_tab.preview_table_name:
                table_name = current_tab.preview_table_name

                # Work on the full underlying table, not just the 5-row preview.
                # Prefer any existing in-memory transformed version for this table.
                base_df = self._preview_transforms.get(table_name)
                if base_df is None:
                    try:
                        base_df = self.db_manager.get_full_table(table_name)
                    except Exception as e:
                        show_error_notification(
                            f"Rename Column Error: Could not load full table '{table_name}' - {str(e)}"
                        )
                        return

                if old_column_name not in base_df.columns:
                    show_warning_notification(f"Column '{old_column_name}' not found in the current table.")
                    return

                if new_column_name in base_df.columns:
                    show_warning_notification(f"Column '{new_column_name}' already exists in the table.")
                    return

                # Apply the rename to the full dataset and remember it for future tools
                updated_full_df = base_df.rename(columns={old_column_name: new_column_name})
                self._preview_transforms[table_name] = updated_full_df

                # Track the column rename for project persistence
                if table_name not in self._column_renames:
                    self._column_renames[table_name] = {}
                self._column_renames[table_name][old_column_name] = new_column_name

                # Update the table in DuckDB so SQL queries work immediately
                # Use 'transformed' source instead of preserving 'database:' source
                # This ensures _qualify_table_names won't rewrite queries to db.<table>
                try:
                    self.db_manager.overwrite_table_with_dataframe(table_name, updated_full_df, source='transformed')
                    # Update table_columns tracking
                    if table_name in self.db_manager.table_columns:
                        columns = self.db_manager.table_columns[table_name]
                        updated_columns = [new_column_name if col == old_column_name else col for col in columns]
                        self.db_manager.table_columns[table_name] = updated_columns
                except Exception as e:
                    # Log but don't fail - the rename still worked in the UI
                    print(f"Warning: Could not update table in database: {e}")

                # Keep showing a small preview in the UI, but based on the updated full data
                preview_df = updated_full_df.head()
                self.populate_table(preview_df)
            else:
                # Non-preview mode: operate directly on the current query results
                df = current_tab.current_df
                if old_column_name not in df.columns:
                    show_warning_notification(f"Column '{old_column_name}' not found in the current results.")
                    return

                if new_column_name in df.columns:
                    show_warning_notification(f"Column '{new_column_name}' already exists in the current results.")
                    return

                updated_df = df.rename(columns={old_column_name: new_column_name})
                current_tab.current_df = updated_df

                # Track the column rename for project persistence if we have a source table
                if source_table_name:
                    if source_table_name not in self._column_renames:
                        self._column_renames[source_table_name] = {}
                    self._column_renames[source_table_name][old_column_name] = new_column_name

                # Update the source table in DuckDB if we found one, so SQL queries work immediately
                if source_table_name and source_table_name in self.db_manager.loaded_tables:
                    try:
                        # Get the full table data to update
                        full_table_df = self.db_manager.get_full_table(source_table_name)
                        # Apply the same rename to the full table
                        if old_column_name in full_table_df.columns:
                            updated_full_table_df = full_table_df.rename(columns={old_column_name: new_column_name})
                            # Use 'transformed' source instead of preserving 'database:' source
                            # This ensures _qualify_table_names won't rewrite queries to db.<table>
                            self.db_manager.overwrite_table_with_dataframe(source_table_name, updated_full_table_df, source='transformed')
                            # Update table_columns tracking
                            if source_table_name in self.db_manager.table_columns:
                                columns = self.db_manager.table_columns[source_table_name]
                                updated_columns = [new_column_name if col == old_column_name else col for col in columns]
                                self.db_manager.table_columns[source_table_name] = updated_columns
                    except Exception as e:
                        # Log but don't fail - the rename still worked in the UI
                        print(f"Warning: Could not update source table '{source_table_name}' in database: {e}")

                # Refresh the table display with the full (query) results
                self.populate_table(updated_df)

            # Update autocomplete to include the new column name
            try:
                # Update the completer with new schema information
                self.update_completer()
            except Exception as e:
                # Log but don't fail - autocomplete update is not critical
                print(f"Warning: Could not update autocomplete: {e}")

            # Inform user about the rename
            message = f"Renamed column '{old_column_name}' to '{new_column_name}'. "
            if source_table_name:
                message += f"The table '{source_table_name}' has been updated - you can use '{new_column_name}' in SQL queries immediately."
            else:
                message += "Remember to use 'Save as Table' if you want to persist this change."
            self.statusBar().showMessage(message)
            try:
                # Also show a non-intrusive notification if available
                show_info_notification(
                    "Column Renamed",
                    f"The column '{old_column_name}' was renamed to '{new_column_name}'. "
                    "To avoid losing this change, use the 'Save as Table' option to save it back to the database."
                )
            except Exception:
                # Notifications are optional; ignore failures here
                pass
        except Exception as e:
            show_error_notification(f"Rename Column Error: Could not rename column '{old_column_name}' - {str(e)}")
            self.statusBar().showMessage(f"Error renaming column '{old_column_name}': {str(e)}")

    def _make_query_friendly_name(self, name: str) -> str:
        """Convert a single column name to a query-friendly form."""
        if name is None:
            return name
        import re
        # Convert to lowercase and replace all non-alphanumeric characters (except underscores) with underscores
        cleaned = re.sub(r'[^a-z0-9_]', '_', str(name).strip().lower())
        # Collapse multiple consecutive underscores into a single underscore
        cleaned = re.sub(r'_+', '_', cleaned)
        # Remove leading and trailing underscores
        cleaned = cleaned.strip('_')
        # If the result is empty (e.g., all special characters), use a default name
        if not cleaned:
            cleaned = 'column'
        return cleaned

    def _create_transformed_table(self, df, base_table_name=None, source_description="current results"):
        """
        Shared helper to create a new table with query-friendly column names.
        
        Args:
            df: DataFrame to transform
            base_table_name: Original table name to use as prefix (if available)
            source_description: Description for status message (e.g., "full table", "current results")
            
        Returns:
            Tuple of (registered_table_name, transformed_df)
        """
        import hashlib
        
        # Apply name transform
        new_columns = [self._make_query_friendly_name(col) for col in df.columns]
        df_renamed = df.copy()
        df_renamed.columns = new_columns

        # Generate a unique table name
        # If we have a base table name, use it as prefix; otherwise use "query_result"
        if base_table_name:
            # Use base table name + hash to ensure uniqueness
            original_cols_str = '_'.join(sorted(str(col) for col in df.columns))
            data_hash = hashlib.md5(
                f"{len(df)}_{len(df.columns)}_{original_cols_str}".encode()
            ).hexdigest()[:8]
            new_table_name = f"{base_table_name}_transformed_{data_hash}"
        else:
            # Fallback for query results without a clear source table
            original_cols_str = '_'.join(sorted(str(col) for col in df.columns))
            data_hash = hashlib.md5(
                f"{len(df)}_{len(df.columns)}_{original_cols_str}".encode()
            ).hexdigest()[:8]
            new_table_name = f"query_result_{data_hash}"

        # Register as a new query result table
        registered_name = self.db_manager.register_dataframe(df_renamed, new_table_name, source="query_result")
        
        # Add to tables list
        self.tables_list.add_table_item(registered_name, "query result")
        
        return registered_name, df_renamed

    def convert_to_query_friendly_names(self, table_name: str):
        """
        Convert column names for a table to query-friendly format:
        - trimmed
        - lowercase
        - spaces replaced with underscores
        Creates a new query result table with the transformed data, leaving the original untouched.
        """
        try:
            # Get full table data
            df = self.db_manager.get_full_table(table_name)

            # Use shared helper to create transformed table
            registered_name, df_renamed = self._create_transformed_table(df, base_table_name=table_name, source_description="full table")
            
            # Update autocomplete to include the new table
            self.update_completer()
            
            # Show the transformed data in the current tab
            current_tab = self.get_current_tab()
            if current_tab:
                # Reset preview mode - we're now showing a transformed query result
                current_tab.is_preview_mode = False
                current_tab.preview_table_name = None
                current_tab.current_df = df_renamed
                # Show the full transformed data (not just a preview)
                self.populate_table(df_renamed)

            self.statusBar().showMessage(
                f"Created new table '{registered_name}' with query-friendly column names "
                f"({len(df_renamed.columns)} columns, {len(df_renamed)} rows). Original table '{table_name}' unchanged."
            )
        except Exception as e:
            show_error_notification(
                f"Transform Error: Could not convert column names for '{table_name}' - {str(e)}"
            )
            self.statusBar().showMessage(f"Error converting column names for '{table_name}': {str(e)}")

    def convert_current_results_to_query_friendly_names(self):
        """
        Convert column names for the current result set to query-friendly format.
        Creates a new query result table.
        
        - If in preview mode: uses the FULL underlying table data (not just the preview)
        - If query results: uses only the current results (filtered/selected data)
        Uses the original table name as prefix when available.
        """
        try:
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None:
                show_warning_notification("No data available. Please run a query or open a table first.")
                return

            # If we're in preview mode, get the FULL table data, not just the preview
            was_preview_mode = current_tab.is_preview_mode and current_tab.preview_table_name
            preview_table_name = current_tab.preview_table_name if was_preview_mode else None
            
            # Determine base table name for prefixing
            base_table_name = None
            if was_preview_mode:
                # Use the preview table name as prefix
                base_table_name = preview_table_name
                df = self.db_manager.get_full_table(preview_table_name)
                row_msg = f"{len(df)} rows (full table)"
            else:
                # Try to get table name from query source or current_df metadata
                if hasattr(current_tab.current_df, '_query_source'):
                    base_table_name = getattr(current_tab.current_df, '_query_source')
                # For query results, use the current_df (which may be filtered)
                df = current_tab.current_df
                row_msg = f"{len(df)} rows from current results"
            
            # Use shared helper to create transformed table
            registered_name, df_renamed = self._create_transformed_table(df, base_table_name=base_table_name, source_description=row_msg)
            
            # Update autocomplete to include the new table
            self.update_completer()
            
            # Show the transformed data in the current tab
            current_tab.is_preview_mode = False
            current_tab.preview_table_name = None
            current_tab.current_df = df_renamed
            self.populate_table(df_renamed)
            
            self.statusBar().showMessage(
                f"Created new table '{registered_name}' with query-friendly column names "
                f"({len(df_renamed.columns)} columns, {row_msg})."
            )
        except Exception as e:
            show_error_notification(
                f"Transform Error: Could not convert column names in current results - {str(e)}"
            )
            self.statusBar().showMessage(f"Error converting column names in current results: {str(e)}")
    
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
    
    def toggle_sidebar(self, checked=None):
        """Toggle sidebar visibility (Ctrl+\\)"""
        if hasattr(self, 'left_panel'):
            if checked is None:
                # Toggle based on current state
                self.left_panel.setVisible(not self.left_panel.isVisible())
            else:
                self.left_panel.setVisible(checked)
            
            # Update menu action state
            if hasattr(self, 'toggle_sidebar_action'):
                self.toggle_sidebar_action.setChecked(self.left_panel.isVisible())
            
            status = "shown" if self.left_panel.isVisible() else "hidden"
            self.statusBar().showMessage(f"Sidebar {status} (Ctrl+\\ to toggle)", 2000)
    
    def toggle_compact_mode(self, checked=None):
        """Toggle compact mode to maximize query/results space (Ctrl+Shift+C)"""
        if checked is None:
            checked = not getattr(self, '_compact_mode', False)
        
        self._compact_mode = checked
        
        # Update all tabs to use compact mode
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if hasattr(tab, 'set_compact_mode'):
                tab.set_compact_mode(checked)
        
        # Toggle secondary UI elements in main window
        if hasattr(self, 'query_header'):
            self.query_header.setVisible(not checked)
        if hasattr(self, 'tab_drop_area'):
            self.tab_drop_area.setVisible(not checked)
        
        # Update menu action state
        if hasattr(self, 'compact_mode_action'):
            self.compact_mode_action.setChecked(checked)
        
        status = "enabled" if checked else "disabled"
        self.statusBar().showMessage(f"Compact mode {status} (Ctrl+Shift+C to toggle)", 2000)
    
    def toggle_docs_panel(self, checked=None):
        """Toggle the DuckDB documentation panel for the current tab (F1)"""
        current_tab = self.tab_widget.currentWidget()
        if current_tab and hasattr(current_tab, 'toggle_docs_panel'):
            current_tab.toggle_docs_panel()
            
            # Update menu action state
            if hasattr(self, 'docs_panel_action') and hasattr(current_tab, 'is_docs_panel_visible'):
                self.docs_panel_action.setChecked(current_tab.is_docs_panel_visible())
    
    def toggle_christmas_theme(self, checked=None):
        """Toggle Christmas theme decorations."""
        if checked is None:
            checked = not self.christmas_theme_enabled
        
        self.christmas_theme_enabled = checked
        
        if checked:
            self.christmas_theme_manager.enable()
        else:
            self.christmas_theme_manager.disable()
        
        # Update menu action state
        if hasattr(self, 'christmas_theme_action'):
            self.christmas_theme_action.setChecked(checked)
        
        # Save preference
        self.save_recent_projects()
        
        status = "enabled 🎄" if checked else "disabled"
        self.statusBar().showMessage(f"Christmas theme {status}", 2000)
            
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
                # For database tables, use qualified name (e.g., db.table_name)
                source = self.db_manager.loaded_tables[table_name]
                if source.startswith('database:'):
                    alias = source.split(':')[1]
                    query = f'SELECT * FROM {alias}."{table_name}"'
                else:
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
                    show_warning_notification(f"Table '{table_name}' has no data to analyze.")
                    self.statusBar().showMessage(f'Table "{table_name}" is empty - cannot analyze')
            else:
                show_warning_notification(f"Table '{table_name}' not found.")
                self.statusBar().showMessage(f'Table "{table_name}" not found')
                
        except Exception as e:
            show_error_notification(f"Analysis Error: Error analyzing table - {str(e)}")
            self.statusBar().showMessage(f'Error analyzing table: {str(e)}')
            
    def profile_table_structure(self, table_name):
        """Find candidate keys and functional dependencies in a table"""
        try:
            # Show a loading indicator
            self.statusBar().showMessage(f'Finding keys for "{table_name}"...')
            
            # Get the table data
            if table_name in self.db_manager.loaded_tables:
                # Check if table needs reloading first
                if table_name in self.tables_list.tables_needing_reload:
                    # Reload the table immediately
                    self.reload_selected_table(table_name)

                # Get the data as a dataframe
                # For database tables, use qualified name (e.g., db.table_name)
                source = self.db_manager.loaded_tables[table_name]
                if source.startswith('database:'):
                    alias = source.split(':')[1]
                    query = f'SELECT * FROM {alias}."{table_name}"'
                else:
                    query = f'SELECT * FROM "{table_name}"'
                df = self.db_manager.execute_query(query)

                if df is not None and not df.empty:
                    row_count = len(df)
                    
                    # Import the key profiler - uses our intelligent optimization system
                    from sqlshell.utils.profile_keys import visualize_profile
                    
                    # The profiler will automatically select the best optimization level
                    # and handle sampling intelligently based on dataset characteristics
                    self.statusBar().showMessage(f'Analyzing keys for "{table_name}" ({row_count:,} rows)...')
                    vis = visualize_profile(df)
                    
                    # Store a reference to prevent garbage collection
                    self._keys_profile_window = vis
                    
                    self.statusBar().showMessage(f'Keys found for "{table_name}" ({row_count:,} rows)')
                else:
                    show_warning_notification(f"Table '{table_name}' has no data to analyze.")
                    self.statusBar().showMessage(f'Table "{table_name}" is empty - cannot analyze')
            else:
                show_warning_notification(f"Table '{table_name}' not found.")
                self.statusBar().showMessage(f'Table "{table_name}" not found')
                
        except Exception as e:
            show_error_notification(f"Error: Could not find keys - {str(e)}")
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
                # For database tables, use qualified name (e.g., db.table_name)
                source = self.db_manager.loaded_tables[table_name]
                if source.startswith('database:'):
                    alias = source.split(':')[1]
                    query = f'SELECT * FROM {alias}."{table_name}"'
                else:
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
                    show_warning_notification(f"Table '{table_name}' has no data to analyze.")
                    self.statusBar().showMessage(f'Table "{table_name}" is empty - cannot analyze')
            else:
                show_warning_notification(f"Table '{table_name}' not found.")
                self.statusBar().showMessage(f'Table "{table_name}" not found')
                
        except Exception as e:
            show_error_notification(f"Profile Error: Error analyzing distributions - {str(e)}")
            self.statusBar().showMessage(f'Error analyzing distributions: {str(e)}')

    def profile_similarity(self, table_name):
        """Analyze a table's row similarity to identify patterns and outliers"""
        try:
            # Show a loading indicator
            self.statusBar().showMessage(f'Analyzing row similarity for "{table_name}"...')
            
            # Get the table data
            if table_name in self.db_manager.loaded_tables:
                # Check if table needs reloading first
                if table_name in self.tables_list.tables_needing_reload:
                    # Reload the table immediately
                    self.reload_selected_table(table_name)

                # Get the data as a dataframe
                # For database tables, use qualified name (e.g., db.table_name)
                source = self.db_manager.loaded_tables[table_name]
                if source.startswith('database:'):
                    alias = source.split(':')[1]
                    query = f'SELECT * FROM {alias}."{table_name}"'
                else:
                    query = f'SELECT * FROM "{table_name}"'
                df = self.db_manager.execute_query(query)

                if df is not None and not df.empty:
                    # Sample the data if it's larger than 1,000 rows for performance
                    row_count = len(df)
                    if row_count > 1000:
                        self.statusBar().showMessage(f'Sampling {table_name} (using 1,000 rows from {row_count} total)...')
                        df = df.sample(n=1000, random_state=42)
                    
                    # Import the similarity profiler
                    from sqlshell.utils.profile_similarity import visualize_profile
                    
                    # Create and show the visualization
                    self.statusBar().showMessage(f'Generating similarity profile for "{table_name}"...')
                    vis = visualize_profile(df)
                    
                    # Store a reference to prevent garbage collection
                    self._similarity_window = vis
                    
                    if row_count > 1000:
                        self.statusBar().showMessage(f'Similarity profile generated for "{table_name}" (sampled 1,000 rows from {row_count})')
                    else:
                        self.statusBar().showMessage(f'Similarity profile generated for "{table_name}"')
                else:
                    show_warning_notification(f"Table '{table_name}' has no data to analyze.")
                    self.statusBar().showMessage(f'Table "{table_name}" is empty - cannot analyze')
            else:
                show_warning_notification(f"Table '{table_name}' not found.")
                self.statusBar().showMessage(f'Table "{table_name}" not found')
                
        except Exception as e:
            show_error_notification(f"Profile Error: Error analyzing row similarity - {str(e)}")
            self.statusBar().showMessage(f'Error analyzing similarity: {str(e)}')

    # DataFrame-based analysis methods (work with current query results)
    def analyze_current_data_entropy(self):
        """Analyze current query results with the entropy profiler to identify important columns"""
        try:
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None or current_tab.current_df.empty:
                show_warning_notification("No data available to analyze.")
                return
            
            df = current_tab.current_df.copy()
            self.statusBar().showMessage(f'Analyzing data columns...')
            
            # Import the entropy profiler
            from sqlshell.utils.profile_entropy import visualize_profile
            
            # Create and show the visualization
            self.statusBar().showMessage(f'Generating entropy profile...')
            vis = visualize_profile(df)
            
            # Store a reference to prevent garbage collection
            self._entropy_window = vis
            
            self.statusBar().showMessage(f'Entropy profile generated for current data')
                
        except Exception as e:
            show_error_notification(f"Analysis Error: Error analyzing data - {str(e)}")
            self.statusBar().showMessage(f'Error analyzing data: {str(e)}')

    def profile_current_data_structure(self):
        """Analyze current query results structure to identify candidate keys and functional dependencies"""
        try:
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None or current_tab.current_df.empty:
                show_warning_notification("No data available to analyze.")
                return
            
            df = current_tab.current_df.copy()
            row_count = len(df)
            
            self.statusBar().showMessage(f'Finding keys ({row_count:,} rows)...')
            
            # Import the structure profiler
            from sqlshell.utils.profile_keys import visualize_profile
            
            # Create and show the visualization
            self.statusBar().showMessage(f'Analyzing keys ({row_count:,} rows)...')
            vis = visualize_profile(df)
            
            # Store a reference to prevent garbage collection
            self._keys_profile_window = vis
            
            self.statusBar().showMessage(f'Keys found ({row_count:,} rows)')
                
        except Exception as e:
            show_error_notification(f"Error: Could not find keys - {str(e)}")
            self.statusBar().showMessage(f'Error profiling data: {str(e)}')

    def profile_current_data_distributions(self):
        """Analyze current query results column distributions to understand data patterns"""
        try:
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None or current_tab.current_df.empty:
                show_warning_notification("No data available to analyze.")
                return
            
            df = current_tab.current_df.copy()
            row_count = len(df)
            
            self.statusBar().showMessage(f'Analyzing column distributions...')
            
            # Sample the data if it's larger than 10,000 rows
            if row_count > 10000:
                self.statusBar().showMessage(f'Sampling data (using 10,000 rows from {row_count} total)...')
                df = df.sample(n=10000, random_state=42)
            
            # Import the distributions profiler
            from sqlshell.utils.profile_distributions import visualize_profile
            
            # Create and show the visualization
            self.statusBar().showMessage(f'Generating distribution profile...')
            vis = visualize_profile(df)
            
            # Store a reference to prevent garbage collection
            self._distributions_window = vis
            
            if row_count > 10000:
                self.statusBar().showMessage(f'Distribution profile generated (sampled 10,000 rows from {row_count:,})')
            else:
                self.statusBar().showMessage(f'Distribution profile generated')
                
        except Exception as e:
            show_error_notification(f"Profile Error: Error analyzing distributions - {str(e)}")
            self.statusBar().showMessage(f'Error analyzing distributions: {str(e)}')

    def profile_current_data_similarity(self):
        """Analyze current query results row similarity to identify patterns and outliers"""
        try:
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None or current_tab.current_df.empty:
                show_warning_notification("No data available to analyze.")
                return
            
            df = current_tab.current_df.copy()
            row_count = len(df)
            
            self.statusBar().showMessage(f'Analyzing row similarity...')
            
            # Sample the data if it's larger than 1,000 rows for performance
            if row_count > 1000:
                self.statusBar().showMessage(f'Sampling data (using 1,000 rows from {row_count} total)...')
                df = df.sample(n=1000, random_state=42)
            
            # Import the similarity profiler
            from sqlshell.utils.profile_similarity import visualize_profile
            
            # Create and show the visualization
            self.statusBar().showMessage(f'Generating similarity profile...')
            vis = visualize_profile(df)
            
            # Store a reference to prevent garbage collection
            self._similarity_window = vis
            
            if row_count > 1000:
                self.statusBar().showMessage(f'Similarity profile generated (sampled 1,000 rows from {row_count:,})')
            else:
                self.statusBar().showMessage(f'Similarity profile generated')
                
        except Exception as e:
            show_error_notification(f"Profile Error: Error analyzing row similarity - {str(e)}")
            self.statusBar().showMessage(f'Error analyzing similarity: {str(e)}')

    def get_data_for_tool(self):
        """
        Get the appropriate DataFrame for tools.
        
        If we're in preview mode (user clicked on a table in the left panel),
        this returns the FULL table data, not just the preview rows.
        If previous transforms (like column delete) have been applied, it uses
        the transformed full dataset stored on the tab.
        
        If the user ran their own query, this returns the query results (current_df).
        
        Returns:
            Tuple of (DataFrame, is_full_table) where is_full_table indicates
            whether the full table was loaded (useful for status messages).
            Returns (None, False) if no data is available.
        """
        current_tab = self.get_current_tab()
        if not current_tab or current_tab.current_df is None:
            return None, False
        
        # Check if we're in preview mode and should use full table
        if current_tab.is_preview_mode and current_tab.preview_table_name:
            # If we've already materialized a transformed full table for this table, use it
            table_name = current_tab.preview_table_name
            transformed_full = self._preview_transforms.get(table_name)
            if transformed_full is not None:
                return transformed_full.copy(), True
            try:
                # Get the full table data from the database
                full_df = self.db_manager.get_full_table(table_name)
                return full_df, True
            except Exception as e:
                # Fall back to current_df (preview) if we can't get full table
                print(f"Warning: Could not get full table, using preview: {e}")
                return current_tab.current_df.copy(), False
        
        # Not in preview mode, use the query results
        return current_tab.current_df.copy(), False

    def get_column_name_by_index(self, column_index):
        """
        Get the column name at the given index from the DataFrame that will be used by tools.
        This ensures we get the correct column name after renames/deletes.
        
        Optimized to avoid loading full tables when in preview mode by using cached metadata.
        
        Args:
            column_index: The index of the column
            
        Returns:
            The column name, or None if the index is invalid or no data is available
        """
        current_tab = self.get_current_tab()
        if not current_tab or current_tab.current_df is None:
            return None
        
        # In preview mode, try to use cached metadata first to avoid loading full table
        if current_tab.is_preview_mode and current_tab.preview_table_name:
            table_name = current_tab.preview_table_name
            
            # First check if we have a cached transform with column info
            transformed_full = self._preview_transforms.get(table_name)
            if transformed_full is not None:
                if 0 <= column_index < len(transformed_full.columns):
                    return transformed_full.columns[column_index]
                return None
            
            # Next check if we have cached column metadata
            if hasattr(self.db_manager, 'table_columns') and table_name in self.db_manager.table_columns:
                columns = self.db_manager.table_columns[table_name]
                if 0 <= column_index < len(columns):
                    return columns[column_index]
            
            # Fall back to preview df columns (should always be available)
            if 0 <= column_index < len(current_tab.current_df.columns):
                return current_tab.current_df.columns[column_index]
            
            return None
        
        # Not in preview mode, use current_df directly
        if 0 <= column_index < len(current_tab.current_df.columns):
            return current_tab.current_df.columns[column_index]
        return None

    def explain_column(self, column_name):
        """Analyze a column to explain its relationship with other columns"""
        try:
            # Get the appropriate data (full table if preview mode, else query results)
            df, is_full_table = self.get_data_for_tool()
            if df is None:
                return
            
            # Validate that the column exists in the DataFrame (handles renamed/deleted columns)
            if column_name not in df.columns:
                show_warning_notification(
                    f"Column '{column_name}' not found in the current dataset. "
                    "This may happen if the column was renamed or deleted."
                )
                return
                
            # Show a loading indicator
            self.statusBar().showMessage(f'Analyzing column "{column_name}"...')
            
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
                # Store reference to prevent garbage collection on Windows
                self._column_profile_window = visualize_profile(df, column_name)
                
                if row_count > 100:
                    self.statusBar().showMessage(f'Column profile generated for "{column_name}" (sampled 100 rows from {row_count})')
                else:
                    self.statusBar().showMessage(f'Column profile generated for "{column_name}"')
            else:
                show_warning_notification("No data available to analyze.")
                self.statusBar().showMessage(f'No data to analyze')
                
        except Exception as e:
            show_error_notification(f"Analysis Error: Error analyzing column - {str(e)}")
            self.statusBar().showMessage(f'Error analyzing column: {str(e)}')

    def encode_text(self, column_name):
        """Generate one-hot encoding for a text column and visualize the results"""
        try:
            # Get the appropriate data (full table if preview mode, else query results)
            df, is_full_table = self.get_data_for_tool()
            if df is None:
                return
                
            # Show a loading indicator
            self.statusBar().showMessage(f'Preparing one-hot encoding for "{column_name}"...')
            
            # Get the current tab to save original row count
            current_tab = self.get_current_tab()
            if current_tab:
                current_tab.original_df_rowcount = len(df)
            
            # Validate that the column exists in the DataFrame (handles renamed/deleted columns)
            if column_name not in df.columns:
                show_warning_notification(
                    f"Column '{column_name}' not found in the current dataset. "
                    "This may happen if the column was renamed or deleted."
                )
                return
            
            # Import and use the visualize_ohe function from profile_ohe
            from sqlshell.utils.profile_ohe import visualize_ohe
            
            # Create and show the one-hot encoding visualization
            # Store reference as instance variable to prevent garbage collection on Windows
            self._ohe_visualization = visualize_ohe(df, column_name)
            
            # Connect the encodingApplied signal to our handler
            self._ohe_visualization.encodingApplied.connect(self.apply_encoding_to_current_tab)
            
            self.statusBar().showMessage(f'One-hot encoding visualization ready for "{column_name}"')
                
        except Exception as e:
            show_error_notification(f"Encoding Error: Error creating one-hot encoding - {str(e)}")
            self.statusBar().showMessage(f'Error encoding column: {str(e)}')

    def find_related_one_hot_encodings(self, target_column):
        """Find one-hot encoded signals in other columns that predict the selected column"""
        try:
            df, is_full_table = self.get_data_for_tool()
            if df is None:
                show_warning_notification("No data available. Please load a table or run a query first.")
                return
            
            if target_column not in df.columns:
                show_warning_notification(f"Column '{target_column}' not found in the current dataset.")
                return

            # Figure out the source table if possible so drilldowns can run SQL
            table_name = None
            current_tab = self.get_current_tab()
            if current_tab:
                if current_tab.is_preview_mode and current_tab.preview_table_name:
                    table_name = current_tab.preview_table_name
                elif current_tab.current_df is not None and hasattr(current_tab.current_df, '_query_source'):
                    table_name = getattr(current_tab.current_df, '_query_source')
            
            self.statusBar().showMessage(f'Finding related one-hot encodings for "{target_column}"...')
            
            from sqlshell.utils.profile_ohe import visualize_related_ohe
            self._related_ohe_window = visualize_related_ohe(
                df, target_column, table_name=table_name, drill_query_callback=self.run_sql_in_editor
            )
            
            if self._related_ohe_window is None:
                self.statusBar().showMessage(f'No predictive one-hot encodings found for "{target_column}"')
            else:
                self.statusBar().showMessage(f'Related one-hot encodings ready for "{target_column}"')
                
        except Exception as e:
            show_error_notification(f"One-Hot Analysis Error: {str(e)}")
            self.statusBar().showMessage(f'Error finding related one-hot encodings: {str(e)}')

    def run_sql_in_editor(self, query_text):
        """Set the provided SQL in the current editor and execute it."""
        try:
            current_tab = self.get_current_tab()
            if not current_tab:
                show_warning_notification("No active query tab to run the drilldown.")
                return
            
            current_tab.set_query_text(query_text)
            self.execute_query()
        except Exception as e:
            show_error_notification(f"Could not run drilldown query: {str(e)}")

    def apply_encoding_to_current_tab(self, encoded_df):
        """Apply the encoded dataframe to the current tab"""
        try:
            # Get the current tab
            current_tab = self.get_current_tab()
            if not current_tab:
                return
            
            # Update the current tab's dataframe with the encoded version
            current_tab.current_df = encoded_df
            
            # Reset preview mode - we're now showing modified data
            current_tab.is_preview_mode = False
            current_tab.preview_table_name = None
            
            # Update the table display
            self.populate_table(encoded_df)
            
            # Update status
            self.statusBar().showMessage(f'Applied one-hot encoding. New table has {len(encoded_df)} rows and {len(encoded_df.columns)} columns.')
            
        except Exception as e:
            show_error_notification(f"Apply Encoding Error: Error applying encoding - {str(e)}")
            self.statusBar().showMessage(f'Error applying encoding: {str(e)}')

    def categorize_column(self, column_name):
        """Categorize a column (bin numerical or group categorical)."""
        try:
            # Get the appropriate data (full table if preview mode, else query results)
            df, is_full_table = self.get_data_for_tool()
            if df is None:
                return

            # Show a loading indicator
            self.statusBar().showMessage(f'Preparing categorization for "{column_name}"...')

            # Get the current tab to save original row count
            current_tab = self.get_current_tab()
            if current_tab:
                current_tab.original_df_rowcount = len(df)

            # Validate that the column exists in the DataFrame (handles renamed/deleted columns)
            if column_name not in df.columns:
                show_warning_notification(
                    f"Column '{column_name}' not found in the current dataset. "
                    "This may happen if the column was renamed or deleted."
                )
                return

            # Import and use the visualize_categorize function
            from sqlshell.utils.profile_categorize import visualize_categorize

            # Create and show the categorization visualization
            # Store reference as instance variable to prevent garbage collection on Windows
            self._categorize_visualization = visualize_categorize(df, column_name)

            # Connect the categorizationApplied signal to our handler
            self._categorize_visualization.categorizationApplied.connect(
                self.apply_categorization_to_current_tab
            )

            self.statusBar().showMessage(
                f'Categorization visualization ready for "{column_name}"'
            )

        except Exception as e:
            show_error_notification(f"Categorization Error: {str(e)}")
            self.statusBar().showMessage(f'Error categorizing column: {str(e)}')

    def apply_categorization_to_current_tab(self, categorized_df):
        """Apply the categorized dataframe to the current tab."""
        try:
            # Get the current tab
            current_tab = self.get_current_tab()
            if not current_tab:
                return

            # Update the current tab's dataframe
            current_tab.current_df = categorized_df

            # Reset preview mode
            current_tab.is_preview_mode = False
            current_tab.preview_table_name = None

            # Update the table display
            self.populate_table(categorized_df)

            # Update status
            self.statusBar().showMessage(
                f'Applied categorization. Table has {len(categorized_df)} rows '
                f'and {len(categorized_df.columns)} columns.'
            )

        except Exception as e:
            show_error_notification(f"Apply Categorization Error: {str(e)}")
            self.statusBar().showMessage(f'Error applying categorization: {str(e)}')

    def discover_classification_rules(self, target_column):
        """Discover classification rules (IF-THEN rules) using CN2 algorithm"""
        try:
            # Get the appropriate data (full table if preview mode, else query results)
            df, is_full_table = self.get_data_for_tool()
            if df is None:
                show_warning_notification("No data available. Please load some data first.")
                return
                
            # Show a loading indicator
            self.statusBar().showMessage(f'Discovering classification rules for "{target_column}"...')
            
            # Validate that the column exists in the DataFrame (handles renamed/deleted columns)
            if target_column not in df.columns:
                show_warning_notification(
                    f"Column '{target_column}' not found in the current dataset. "
                    "This may happen if the column was renamed or deleted."
                )
                return
            
            # Check if there are enough columns for rule learning
            if len(df.columns) < 2:
                show_warning_notification("Need at least 2 columns (target + features) for rule discovery.")
                return
            
            # Check for NaN values in target
            n_nan = df[target_column].isna().sum()
            if n_nan > 0:
                # Will be handled by filtering, just warn
                if n_nan == len(df):
                    show_warning_notification(
                        f"Column '{target_column}' contains only missing values. "
                        "Cannot discover rules."
                    )
                    return
            
            # Check if target column has reasonable number of unique values
            n_unique = df[target_column].dropna().nunique()
            
            # Check if target is numeric with many unique values - auto-discretize
            discretizer = None
            is_numeric = pd.api.types.is_numeric_dtype(df[target_column])
            
            if is_numeric and n_unique > 15:
                # Auto-discretize numeric targets with many distinct values
                # Uses academically-grounded binning methods
                from sqlshell.utils.profile_cn2 import discretize_numeric_target
                
                self.statusBar().showMessage(
                    f'Discretizing numeric column "{target_column}" ({n_unique} unique values)...'
                )
                
                df, discretizer = discretize_numeric_target(
                    df, 
                    target_column, 
                    method='auto',  # Auto-selects best method based on distribution
                    n_bins=None     # Auto-compute optimal number of bins
                )
                
                # Update unique count after discretization
                n_unique = df[target_column].dropna().nunique()
            elif n_unique > 50:
                # Non-numeric column with too many values
                show_warning_notification(
                    f"Column '{target_column}' has {n_unique} unique values. "
                    "CN2 works best with categorical targets (fewer distinct values)."
                )
                return
            
            if n_unique < 2:
                show_warning_notification(
                    f"Column '{target_column}' has only {n_unique} unique value(s). "
                    "Need at least 2 distinct classes for classification."
                )
                return
            
            # Import and use the visualize_cn2_rules function
            from sqlshell.utils.profile_cn2 import visualize_cn2_rules
            
            # Create and show the CN2 rules visualization
            vis = visualize_cn2_rules(df, target_column, beam_width=5, min_covered_examples=5)
            
            # If we discretized, add info about the binning to the visualization
            if discretizer is not None:
                vis.setWindowTitle(
                    f"CN2 Rule Induction - {target_column} (Discretized: {discretizer.method_used_})"
                )
                # Store discretizer info for reference
                vis._discretizer = discretizer
            
            # Store reference to prevent garbage collection
            self._current_cn2_vis = vis
            
            self.statusBar().showMessage(f'Classification rules discovered for "{target_column}"')
                
        except Exception as e:
            show_error_notification(f"Rule Discovery Error: {str(e)}")
            self.statusBar().showMessage(f'Error discovering rules: {str(e)}')


    def get_current_query_tab(self):
        """Get the currently active tab if it's a query tab (has query_edit attribute)"""
        current_tab = self.get_current_tab()
        if current_tab and hasattr(current_tab, 'query_edit'):
            return current_tab
        return None

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

    def extract_table_names_from_query(self, query):
        """
        Extract table names from a SQL query using basic regex patterns.
        Returns a set of table names (lowercase).
        """
        import re
        # Patterns to match FROM, JOIN, and INTO clauses
        patterns = [
            r'FROM\s+([a-zA-Z0-9_\.]+)',
            r'JOIN\s+([a-zA-Z0-9_\.]+)',
            r'INTO\s+([a-zA-Z0-9_\.]+)',
            r'UPDATE\s+([a-zA-Z0-9_\.]+)',
            r'TABLE\s+([a-zA-Z0-9_\.]+)'
        ]
        tables = set()
        query_upper = query.upper()
        for pattern in patterns:
            matches = re.finditer(pattern, query_upper)
            for match in matches:
                table_name = match.group(1).strip('"[]`\'')
                # Skip SQL keywords
                if table_name in ('SELECT', 'WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 
                                  'UNION', 'INTERSECT', 'EXCEPT', 'WITH', 'AS', 'ON', 'USING'):
                    continue
                tables.add(table_name.lower())
        # Account for qualified table names (schema.table)
        qualified_tables = set()
        for table in tables:
            if '.' in table:
                qualified_tables.add(table.split('.')[-1])
        tables.update(qualified_tables)
        return tables

    # Drag and Drop Event Handlers
    def dragEnterEvent(self, event):
        """Handle drag enter events - accept if files are being dragged"""
        if event.mimeData().hasUrls():
            # Check if any of the dragged items are supported file types
            supported_extensions = {'.xlsx', '.xls', '.csv', '.txt', '.parquet', '.sqlite', '.db', '.delta'}
            urls = event.mimeData().urls()
            
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    # Accept if it's a supported file type or a directory (for Delta tables)
                    if file_ext in supported_extensions or os.path.isdir(file_path):
                        event.acceptProposedAction()
                        self.statusBar().showMessage("Drop files here to load them")
                        return
            
            # If we get here, no supported files were found
            event.ignore()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move events - provide visual feedback"""
        if event.mimeData().hasUrls():
            # Check if any dragged items are supported
            supported_extensions = {'.xlsx', '.xls', '.csv', '.txt', '.parquet', '.sqlite', '.db', '.delta'}
            urls = event.mimeData().urls()
            
            supported_files = []
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    if file_ext in supported_extensions or os.path.isdir(file_path):
                        supported_files.append(os.path.basename(file_path))
            
            if supported_files:
                event.acceptProposedAction()
                if len(supported_files) == 1:
                    self.statusBar().showMessage(f"Drop to load: {supported_files[0]}")
                else:
                    self.statusBar().showMessage(f"Drop to load {len(supported_files)} files")
            else:
                event.ignore()
                self.statusBar().showMessage("Unsupported file type(s)")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave events - clear status message"""
        self.statusBar().clearMessage()

    def dropEvent(self, event):
        """Handle drop events - load the dropped files"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            local_files = []
            
            # Extract local file paths
            for url in urls:
                if url.isLocalFile():
                    local_files.append(url.toLocalFile())
            
            if local_files:
                try:
                    self.process_dropped_files(local_files)
                    event.acceptProposedAction()
                except Exception as e:
                    show_error_notification(f"Error: Error processing dropped files - {str(e)}")
                    self.statusBar().showMessage(f"Error processing dropped files: {str(e)}")
            else:
                event.ignore()
        else:
            event.ignore()
        
        # Clear the status message
        self.statusBar().clearMessage()

    def process_dropped_files(self, file_paths):
        """Process the dropped files using existing file loading logic"""
        supported_extensions = {'.xlsx', '.xls', '.csv', '.txt', '.parquet', '.sqlite', '.db', '.delta'}
        
        # Ensure database connection exists
        if not self.db_manager.is_connected():
            connection_info = self.db_manager.create_memory_connection()
            self.db_info_label.setText(connection_info)
        
        # Count data files (exclude database files as they don't create tables)
        data_files = [fp for fp in file_paths 
                      if os.path.splitext(fp)[1].lower() not in {'.sqlite', '.db'}]
        
        # Ask for prefix if multiple data files are being dropped
        table_prefix = ""
        if len(data_files) > 1:
            prefix, ok = QInputDialog.getText(
                self,
                "Table Name Prefix",
                f"You are loading {len(data_files)} files.\n"
                "Enter a prefix for table names (or leave blank for no prefix):\n\n"
                "Example: 'prod_' → tables will be named 'prod_sales', 'prod_orders', etc.",
                QLineEdit.EchoMode.Normal,
                ""
            )
            if ok:
                table_prefix = prefix.strip()
            # If user cancels the dialog, continue with no prefix
        
        loaded_files = []
        errors = []
        
        for file_path in file_paths:
            try:
                file_ext = os.path.splitext(file_path)[1].lower()
                
                # Check if it's a Delta table directory
                is_delta_table = (os.path.isdir(file_path) and 
                                os.path.exists(os.path.join(file_path, '_delta_log'))) or file_ext == '.delta'
                
                if file_ext in {'.sqlite', '.db'}:
                    # Database file - use the quick_open_file method
                    self.quick_open_file(file_path)
                    loaded_files.append(os.path.basename(file_path))
                    
                elif file_ext in {'.xlsx', '.xls', '.csv', '.txt', '.parquet'} or is_delta_table:
                    # Data file - use the database manager to load
                    table_name, df = self.db_manager.load_file(file_path, table_prefix=table_prefix)
                    
                    # Update UI
                    self.tables_list.add_table_item(table_name, os.path.basename(file_path))
                    loaded_files.append(f"{os.path.basename(file_path)} as table '{table_name}'")
                    
                    # Show preview of loaded data
                    preview_df = df.head()
                    current_tab = self.get_current_tab()
                    if current_tab:
                        self.populate_table(preview_df)
                        current_tab.results_title.setText(f"PREVIEW: {table_name}")
                    
                    # Update completer
                    self.update_completer()
                    
                    # Add to recent files
                    self.add_recent_file(file_path)
                    
                else:
                    errors.append(f"Unsupported file type: {os.path.basename(file_path)} ({file_ext})")
                    
            except Exception as e:
                errors.append(f"Error loading {os.path.basename(file_path)}: {str(e)}")
        
        # Show results
        if loaded_files:
            if len(loaded_files) == 1:
                self.statusBar().showMessage(f"Loaded: {loaded_files[0]}")
            else:
                self.statusBar().showMessage(f"Loaded {len(loaded_files)} files")
        
        if errors:
            error_message = "Some files could not be loaded:\n\n" + "\n".join(errors)
            QMessageBox.warning(self, "Loading Errors", error_message)

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
        
        # Create and show main window after delay (very short to speed up startup)
        timer = QTimer()
        timer.setSingleShot(True)  # Ensure it only fires once
        timer.timeout.connect(show_main_window)
        timer.start(500)  # 0.5 second delay for a very fast splash
        
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
