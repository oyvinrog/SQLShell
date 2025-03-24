import sys
import os
import json

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
                           QCheckBox, QWidgetAction, QMenuBar, QInputDialog)
from PyQt6.QtCore import Qt, QAbstractTableModel, QRegularExpression, QRect, QSize, QStringListModel, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat, QPainter, QTextFormat, QTextCursor, QIcon, QPalette, QLinearGradient, QBrush, QPixmap, QPolygon, QPainterPath
import numpy as np
from datetime import datetime

from sqlshell import create_test_data
from sqlshell.splash_screen import AnimatedSplashScreen
from sqlshell.syntax_highlighter import SQLSyntaxHighlighter
from sqlshell.editor import LineNumberArea, SQLEditor
from sqlshell.ui import FilterHeader, BarChartDelegate
from sqlshell.db import DatabaseManager
from sqlshell.query_tab import QueryTab

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
        
        # Load recent projects from settings
        self.load_recent_projects()
        
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
            
            QTabWidget::pane {{
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                top: -1px;
                background-color: white;
            }}
            
            QTabBar::tab {{
                background-color: {self.colors['light_bg']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 12px;
                margin-right: 2px;
                min-width: 80px;
            }}
            
            QTabBar::tab:selected {{
                background-color: white;
                border-bottom: 1px solid white;
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: #E3F2FD;
            }}
            
            QTabBar::close-button {{
                image: url(close.png);
                subcontrol-position: right;
            }}
            
            QTabBar::close-button:hover {{
                background-color: rgba(255, 0, 0, 0.2);
                border-radius: 2px;
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
        
        # Add Recent Projects submenu
        self.recent_projects_menu = file_menu.addMenu('Recent Projects')
        self.update_recent_projects_menu()
        
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
        
        # Add Tab menu
        tab_menu = menubar.addMenu('&Tab')
        
        new_tab_action = tab_menu.addAction('New Tab')
        new_tab_action.setShortcut('Ctrl+T')
        new_tab_action.triggered.connect(self.add_tab)
        
        duplicate_tab_action = tab_menu.addAction('Duplicate Current Tab')
        duplicate_tab_action.setShortcut('Ctrl+D')
        duplicate_tab_action.triggered.connect(self.duplicate_current_tab)
        
        rename_tab_action = tab_menu.addAction('Rename Current Tab')
        rename_tab_action.setShortcut('Ctrl+R')
        rename_tab_action.triggered.connect(self.rename_current_tab)
        
        close_tab_action = tab_menu.addAction('Close Current Tab')
        close_tab_action.setShortcut('Ctrl+W')
        close_tab_action.triggered.connect(self.close_current_tab)
        
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
        
        # Create tab widget for multiple queries
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # Add a "+" button to the tab bar
        self.tab_widget.setCornerWidget(self.create_tab_corner_widget())
        
        right_layout.addWidget(self.tab_widget)

        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 4)

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
        add_tab_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
                font-weight: bold;
                font-size: 16px;
                color: #3498DB;
            }
            QToolButton:hover {
                background-color: rgba(52, 152, 219, 0.2);
            }
            QToolButton:pressed {
                background-color: rgba(52, 152, 219, 0.4);
            }
        """)
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
                # Use the database manager to load the file
                table_name, df = self.db_manager.load_file(file_name)
                
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

    def remove_selected_table(self):
        current_item = self.tables_list.currentItem()
        if current_item:
            table_name = current_item.text().split(' (')[0]
            if self.db_manager.remove_table(table_name):
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
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Open Database",
                "",
                "All Database Files (*.db *.sqlite *.sqlite3);;All Files (*)"
            )
            
            if filename:
                try:
                    # Use the database manager to open the database
                    self.db_manager.open_database(filename)
                    
                    # Update UI with tables from the database
                    self.tables_list.clear()
                    for table_name in self.db_manager.loaded_tables:
                        self.tables_list.addItem(f"{table_name} (database)")
                    
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
        """Update the completer with table and column names"""
        # Get completion words from the database manager
        completion_words = self.db_manager.get_all_table_columns()
        
        # Update the completer in all tab query editors
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            tab.query_edit.update_completer_model(completion_words)

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

            start_time = datetime.now()
            
            try:
                # Use the database manager to execute the query
                result = self.db_manager.execute_query(query)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                self.populate_table(result)
                self.statusBar().showMessage(f"Query executed successfully. Time: {execution_time:.2f}s. Rows: {len(result)}")
                
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
        if not item:
            return
            
        # Get the current tab
        current_tab = self.get_current_tab()
        if not current_tab:
            return
            
        table_name = item.text().split(' (')[0]
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
            
            # Register the tables in the database manager
            self.db_manager.register_dataframe(sales_df, 'sample_sales_data', 'test_data/sample_sales_data.xlsx')
            self.db_manager.register_dataframe(product_df, 'product_catalog', 'test_data/product_catalog.xlsx')
            self.db_manager.register_dataframe(customer_df, 'customer_data', 'test_data/customer_data.parquet')
            
            # Update UI
            self.tables_list.clear()
            for table_name, file_path in self.db_manager.loaded_tables.items():
                self.tables_list.addItem(f"{table_name} ({os.path.basename(file_path)})")
            
            # Set the sample query in the current tab
            current_tab = self.get_current_tab()
            if current_tab:
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
                current_tab.set_query_text(sample_query.strip())
            
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
            self.db_manager.table_columns[table_name] = df.columns.tolist()
            
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
            self.db_manager.table_columns[table_name] = df.columns.tolist()
            
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
        return pd.DataFrame(data, columns=headers)

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
        item = self.tables_list.itemAt(position)
        if not item:
            return

        # Get current tab
        current_tab = self.get_current_tab()
        if not current_tab:
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
        context_menu.addSeparator()
        rename_action = context_menu.addAction("Rename table...")
        delete_action = context_menu.addAction("Delete table")
        delete_action.setIcon(QIcon.fromTheme("edit-delete"))

        # Show menu and get selected action
        action = context_menu.exec(self.tables_list.mapToGlobal(position))

        if action == select_from_action:
            # Insert "SELECT * FROM table_name" at cursor position
            cursor = current_tab.query_edit.textCursor()
            cursor.insertText(f"SELECT * FROM {table_name}")
            current_tab.query_edit.setFocus()
        elif action == add_to_editor_action:
            # Just insert the table name at cursor position
            cursor = current_tab.query_edit.textCursor()
            cursor.insertText(table_name)
            current_tab.query_edit.setFocus()
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
                    source = item.text().split(' (')[1][:-1]  # Get the source part
                    item.setText(f"{new_name} ({source})")
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

    def new_project(self):
        """Create a new project by clearing current state"""
        if self.db_manager.is_connected():
            reply = QMessageBox.question(self, 'New Project',
                                       'Are you sure you want to start a new project? All unsaved changes will be lost.',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                # Close existing connection
                self.db_manager.close_connection()
                
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
                'tabs': tabs_data,
                'connection_type': self.db_manager.connection_type
            }
            
            # Save table information
            for table_name, file_path in self.db_manager.loaded_tables.items():
                # For database tables and query results, store the special identifier
                if file_path in ['database', 'query_result']:
                    source_path = file_path
                else:
                    # For file-based tables, store the absolute path
                    source_path = os.path.abspath(file_path)
                
                project_data['tables'][table_name] = {
                    'file_path': source_path,
                    'columns': self.db_manager.table_columns.get(table_name, [])
                }
            
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
                if not self.db_manager.is_connected():
                    connection_info = self.db_manager.create_memory_connection()
                    self.db_info_label.setText(connection_info)
                
                # Load tables
                for table_name, table_info in project_data['tables'].items():
                    file_path = table_info['file_path']
                    try:
                        if file_path == 'database':
                            # For tables from database, we need to recreate them from their data
                            # Execute a SELECT to get the data and recreate the table
                            query = f"SELECT * FROM {table_name}"
                            df = self.db_manager.execute_query(query)
                            self.db_manager.register_dataframe(df, table_name, 'database')
                            self.tables_list.addItem(f"{table_name} (database)")
                        elif file_path == 'query_result':
                            # For tables from query results, we'll need to re-run the query
                            # For now, just note it as a query result table
                            self.db_manager.loaded_tables[table_name] = 'query_result'
                            self.tables_list.addItem(f"{table_name} (query result)")
                        elif os.path.exists(file_path):
                            # Use the database manager to load the file
                            try:
                                table_name, df = self.db_manager.load_file(file_path)
                                self.tables_list.addItem(f"{table_name} ({os.path.basename(file_path)})")
                            except Exception as e:
                                QMessageBox.warning(self, "Warning",
                                    f"Failed to load file for table {table_name}:\n{str(e)}")
                                continue
                        else:
                            QMessageBox.warning(self, "Warning",
                                f"Could not find file for table {table_name}: {file_path}")
                            continue
                            
                        # The columns are already set by the database manager
                            
                    except Exception as e:
                        QMessageBox.warning(self, "Warning",
                            f"Failed to load table {table_name}:\n{str(e)}")
                
                # Load tabs
                if 'tabs' in project_data and project_data['tabs']:
                    # Remove the default tab
                    while self.tab_widget.count() > 0:
                        self.close_tab(0)
                        
                    # Create tabs from saved data
                    for tab_data in project_data['tabs']:
                        tab = self.add_tab(tab_data.get('title', 'Query'))
                        tab.set_query_text(tab_data.get('query', ''))
                
                # Update UI
                self.current_project_file = file_name
                self.setWindowTitle(f'SQL Shell - {os.path.basename(file_name)}')
                
                # Add to recent projects
                self.add_recent_project(os.path.abspath(file_name))
                
                self.statusBar().showMessage(f'Project loaded from {file_name}')
                self.update_completer()
                
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
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving recent projects: {e}")

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

    def add_tab(self, title="Query 1"):
        """Add a new query tab"""
        # Ensure title is a string
        title = str(title)
        
        # Create a new tab with a unique name if needed
        if title == "Query 1" and self.tab_widget.count() > 0:
            # Generate a unique tab name (Query 2, Query 3, etc.)
            base_name = "Query"
            counter = 1
            while True:
                counter += 1
                test_name = f"{base_name} {counter}"
                found = False
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.tabText(i) == test_name:
                        found = True
                        break
                if not found:
                    title = test_name
                    break
        
        # Create the tab content
        tab = QueryTab(self)
        
        # Add to our list of tabs
        self.tabs.append(tab)
        
        # Add tab to widget
        index = self.tab_widget.addTab(tab, title)
        self.tab_widget.setCurrentIndex(index)
        
        # Focus the new tab's query editor
        tab.query_edit.setFocus()
        
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
    
    def close_tab(self, index):
        """Close the tab at the given index"""
        if self.tab_widget.count() <= 1:
            # Don't close the last tab, just clear it
            tab = self.get_tab_at_index(index)
            tab.set_query_text("")
            tab.results_table.setRowCount(0)
            tab.results_table.setColumnCount(0)
            return
            
        # Remove the tab
        widget = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        
        # Remove from our list of tabs
        if widget in self.tabs:
            self.tabs.remove(widget)
        
        # Delete the widget to free resources
        widget.deleteLater()
    
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