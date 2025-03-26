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
                           QCheckBox, QWidgetAction, QMenuBar, QInputDialog, QProgressDialog,
                           QListWidgetItem)
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

class DraggableTablesList(QListWidget):
    """Custom QListWidget that provides better drag functionality for table names."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        
        # Apply custom styling
        self.setStyleSheet("""
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
        
    def startDrag(self, supportedActions):
        """Override startDrag to customize the drag data."""
        item = self.currentItem()
        if not item:
            return
            
        # Extract the table name without the file info in parentheses
        table_name = item.text().split(' (')[0]
        
        # Create mime data with the table name
        mime_data = QMimeData()
        mime_data.setText(table_name)
        
        # Create drag object
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        # Create a visually appealing drag pixmap
        font = self.font()
        font.setBold(True)
        metrics = self.fontMetrics()
        text_width = metrics.horizontalAdvance(table_name)
        text_height = metrics.height()
        
        # Make the pixmap large enough for the text plus padding and a small icon
        padding = 10
        pixmap = QPixmap(text_width + padding * 2 + 16, text_height + padding)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Begin painting
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw a nice rounded rectangle background
        bg_color = QColor(44, 62, 80, 220)  # Dark blue with transparency
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, pixmap.width(), pixmap.height(), 5, 5)
        
        # Draw text
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(font)
        painter.drawText(int(padding + 16), int(text_height + (padding / 2) - 2), table_name)
        
        # Draw a small database icon (simulated)
        icon_x = padding / 2
        icon_y = (pixmap.height() - 12) / 2
        
        # Draw a simple database icon as a blue circle with lines
        table_icon_color = QColor("#3498DB")
        painter.setBrush(QBrush(table_icon_color))
        painter.setPen(Qt.GlobalColor.white)
        painter.drawEllipse(int(icon_x), int(icon_y), 12, 12)
        
        # Draw "table" lines inside the circle
        painter.setPen(Qt.GlobalColor.white)
        painter.drawLine(int(icon_x + 3), int(icon_y + 4), int(icon_x + 9), int(icon_y + 4))
        painter.drawLine(int(icon_x + 3), int(icon_y + 6), int(icon_x + 9), int(icon_y + 6))
        painter.drawLine(int(icon_x + 3), int(icon_y + 8), int(icon_x + 9), int(icon_y + 8))
        
        painter.end()
        
        # Set the drag pixmap
        drag.setPixmap(pixmap)
        
        # Set hotspot to be at the top-left corner of the text
        drag.setHotSpot(QPoint(padding, pixmap.height() // 2))
        
        # Execute drag operation
        result = drag.exec(supportedActions)
        
        # Optional: add a highlight effect after dragging
        if result == Qt.DropAction.CopyAction and item:
            # Briefly highlight the dragged item
            orig_bg = item.background()
            item.setBackground(QBrush(QColor(26, 188, 156, 100)))  # Light green highlight
            
            # Reset after a short delay
            QTimer.singleShot(300, lambda: item.setBackground(orig_bg))

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
        
        # Add View menu for window management
        view_menu = menubar.addMenu('&View')
        
        # Maximized window option
        maximize_action = view_menu.addAction('Maximize Window')
        maximize_action.setShortcut('F11')
        maximize_action.triggered.connect(self.toggle_maximize_window)
        
        # Zoom submenu
        zoom_menu = view_menu.addMenu('Zoom')
        
        zoom_in_action = zoom_menu.addAction('Zoom In')
        zoom_in_action.setShortcut('Ctrl++')
        zoom_in_action.triggered.connect(lambda: self.change_zoom(1.1))
        
        zoom_out_action = zoom_menu.addAction('Zoom Out')
        zoom_out_action.setShortcut('Ctrl+-')
        zoom_out_action.triggered.connect(lambda: self.change_zoom(0.9))
        
        reset_zoom_action = zoom_menu.addAction('Reset Zoom')
        reset_zoom_action.setShortcut('Ctrl+0')
        reset_zoom_action.triggered.connect(lambda: self.reset_zoom())
        
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
        self.tables_list = DraggableTablesList()
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
        
        # Connect double-click signal for direct tab renaming
        self.tab_widget.tabBarDoubleClicked.connect(self.handle_tab_double_click)
        
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
                    # Clear existing database tables from the list widget
                    for i in range(self.tables_list.count() - 1, -1, -1):
                        item = self.tables_list.item(i)
                        if item and item.text().endswith('(database)'):
                            self.tables_list.takeItem(i)
                    
                    # Use the database manager to open the database
                    self.db_manager.open_database(filename)
                    
                    # Update UI with tables from the database
                    for table_name, source in self.db_manager.loaded_tables.items():
                        if source == 'database':
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
        """Update the completer with table and column names in a non-blocking way"""
        try:
            # Check if any tabs exist
            if self.tab_widget.count() == 0:
                return
            
            # Start a background update with a timer
            self.statusBar().showMessage("Updating auto-completion...", 2000)
            
            # Track query history and frequently used terms
            if not hasattr(self, 'query_history'):
                self.query_history = []
                self.completion_usage = {}  # Track usage frequency
            
            # Get completion words from the database manager
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
                for term, _ in frequent_terms:
                    if term not in completion_words:
                        completion_words.append(term)
            
            # Limit to a reasonable number of items to prevent performance issues
            MAX_COMPLETION_ITEMS = 2000  # Increased from 1000 to accommodate more smart suggestions
            if len(completion_words) > MAX_COMPLETION_ITEMS:
                # Create a more advanced prioritization strategy
                prioritized_words = []
                
                # First, include all table names
                tables = list(self.db_manager.loaded_tables.keys())
                prioritized_words.extend(tables)
                
                # Then add most common SQL keywords and patterns
                sql_keywords = [w for w in completion_words if w.isupper() and len(w) > 1]
                prioritized_words.extend(sql_keywords[:200])  # Cap at 200 keywords
                
                # Add frequently used items
                if hasattr(self, 'completion_usage'):
                    frequent_items = [
                        item for item, _ in sorted(
                            self.completion_usage.items(), 
                            key=lambda x: x[1], 
                            reverse=True
                        )[:100]  # Top 100 most used
                    ]
                    prioritized_words.extend(frequent_items)
                
                # Add table.column patterns which are very useful
                qualified_columns = [w for w in completion_words if '.' in w and w.split('.')[0] in tables]
                prioritized_words.extend(qualified_columns[:300])  # Cap at 300 qualified columns
                
                # Add common completion patterns
                patterns = [w for w in completion_words if ' ' in w]  # Spaces indicate phrases/patterns
                prioritized_words.extend(patterns[:200])  # Cap at 200 patterns
                
                # Finally add other columns
                remaining_slots = MAX_COMPLETION_ITEMS - len(prioritized_words)
                remaining_words = [
                    w for w in completion_words 
                    if w not in prioritized_words 
                    and not w.isupper() 
                    and '.' not in w 
                    and ' ' not in w
                ]
                prioritized_words.extend(remaining_words[:remaining_slots])
                
                # Remove duplicates while preserving order
                seen = set()
                completion_words = []
                for item in prioritized_words:
                    if item not in seen:
                        seen.add(item)
                        completion_words.append(item)
                
                # Ensure we don't exceed the maximum
                completion_words = completion_words[:MAX_COMPLETION_ITEMS]
            
            # Use a single model for all tabs to save memory and improve performance
            model = QStringListModel(completion_words)
            
            # Keep a reference to the model to prevent garbage collection
            self._current_completer_model = model
            
            # Only update the current tab immediately
            current_index = self.tab_widget.currentIndex()
            if current_index >= 0:
                current_tab = self.tab_widget.widget(current_index)
                if current_tab and hasattr(current_tab, 'query_edit'):
                    try:
                        current_tab.query_edit.update_completer_model(model)
                    except Exception as e:
                        self.statusBar().showMessage(f"Error updating current tab completer: {str(e)}", 2000)
            
            # Only schedule updates for additional tabs if we have more than 3 tabs
            # This reduces overhead for common usage patterns
            if self.tab_widget.count() > 1:
                # Calculate a reasonable maximum delay (ms)
                max_delay = min(500, 50 * self.tab_widget.count())
                
                # Store timers to prevent garbage collection
                if not hasattr(self, '_completer_timers'):
                    self._completer_timers = []
                
                # Clear old timers
                for timer in self._completer_timers:
                    if timer.isActive():
                        timer.stop()
                self._completer_timers = []
                
                # Schedule updates for other tabs with increasing delays
                for i in range(self.tab_widget.count()):
                    if i != current_index:
                        tab = self.tab_widget.widget(i)
                        if tab and not tab.isHidden() and hasattr(tab, 'query_edit'):
                            delay = int((i + 1) / self.tab_widget.count() * max_delay)
                            
                            timer = QTimer()
                            timer.setSingleShot(True)
                            # Store tab and model as local variables for the lambda
                            # to avoid closure issues
                            tab_ref = tab
                            model_ref = model
                            timer.timeout.connect(
                                lambda t=tab_ref, m=model_ref: self._update_tab_completer(t, m))
                            self._completer_timers.append(timer)
                            timer.start(delay)
            
            # Process events to keep UI responsive
            QApplication.processEvents()
            
            # Return True to indicate success
            return True
            
        except Exception as e:
            # Catch any errors to prevent hanging
            self.statusBar().showMessage(f"Auto-completion update error: {str(e)}", 2000)
            return False
            
    def _update_tab_completer(self, tab, model):
        """Helper method to update a tab's completer with the given model"""
        if tab and not tab.isHidden() and hasattr(tab, 'query_edit'):  # Only update visible tabs with query editors
            try:
                tab.query_edit.update_completer_model(model)
                QApplication.processEvents()  # Keep UI responsive
            except Exception as e:
                print(f"Error updating tab completer: {e}")
                # Try a simpler approach as fallback
                try:
                    if hasattr(tab.query_edit, 'all_sql_keywords'):
                        fallback_model = QStringListModel(tab.query_edit.all_sql_keywords)
                        tab.query_edit.completer.setModel(fallback_model)
                except Exception:
                    pass  # Last resort: ignore errors to prevent crashes

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
                
                # Record query in history and update completion usage
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
                'connection_type': self.db_manager.connection_type,
                'database_path': None  # Initialize to None
            }
            
            # If we have a database connection, save the path
            if self.db_manager.is_connected() and hasattr(self.db_manager, 'database_path'):
                project_data['database_path'] = self.db_manager.database_path
            
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
                self.new_project()
                progress.setValue(15)
                QApplication.processEvents()
                
                # Check if there's a database path in the project
                has_database_path = 'database_path' in project_data and project_data['database_path']
                has_database_tables = any(table_info.get('file_path') == 'database' 
                                       for table_info in project_data.get('tables', {}).values())
                
                # Set a flag to track if database tables are loaded
                database_tables_loaded = False
                
                # If the project contains database tables and a database path, try to connect to it
                progress.setLabelText("Connecting to database...")
                if has_database_path and has_database_tables:
                    database_path = project_data['database_path']
                    try:
                        if os.path.exists(database_path):
                            # Connect to the database
                            self.db_manager.open_database(database_path)
                            self.db_info_label.setText(self.db_manager.get_connection_info())
                            self.statusBar().showMessage(f"Connected to database: {database_path}")
                            
                            # Add all database tables to the tables list
                            for table_name, source in self.db_manager.loaded_tables.items():
                                if source == 'database':
                                    self.tables_list.addItem(f"{table_name} (database)")
                            
                            # Mark database tables as loaded
                            database_tables_loaded = True
                        else:
                            database_tables_loaded = False
                            QMessageBox.warning(self, "Database Not Found",
                                f"The project's database file was not found at:\n{database_path}\n\n"
                                "Database tables will be shown but not accessible until you reconnect to the database.")
                    except Exception as e:
                        database_tables_loaded = False
                        QMessageBox.warning(self, "Database Connection Error",
                            f"Failed to connect to the project's database:\n{str(e)}\n\n"
                            "Database tables will be shown but not accessible until you reconnect to the database.")
                else:
                    # Create connection if needed (we don't have a specific database to connect to)
                    database_tables_loaded = False
                    if not self.db_manager.is_connected():
                        connection_info = self.db_manager.create_memory_connection()
                        self.db_info_label.setText(connection_info)
                    elif 'connection_type' in project_data and project_data['connection_type'] != self.db_manager.connection_type:
                        # If connected but with a different database type than what was saved in the project
                        QMessageBox.warning(self, "Database Type Mismatch",
                            f"The project was saved with a {project_data['connection_type']} database, but you're currently using {self.db_manager.connection_type}.\n\n"
                            "Some database-specific features may not work correctly. Consider reconnecting to the correct database type.")
                
                progress.setValue(30)
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
                        
                    progress.setLabelText(f"Loading table: {table_name}")
                    file_path = table_info['file_path']
                    try:
                        if file_path == 'database':
                            # Skip if we already loaded database tables by connecting to the database
                            if database_tables_loaded:
                                continue
                                
                            # For database tables, we need to check if the original database is connected
                            # Don't try to SELECT from non-existent tables
                            # Instead just register the table name for UI display
                            self.db_manager.loaded_tables[table_name] = 'database'
                            
                            # If we have column information, use it
                            if 'columns' in table_info:
                                self.db_manager.table_columns[table_name] = table_info['columns']
                            
                            # Add to the UI list
                            self.tables_list.addItem(f"{table_name} (database)")
                        elif file_path == 'query_result':
                            # For tables from query results, we'll need to re-run the query
                            # For now, just note it as a query result table
                            self.db_manager.loaded_tables[table_name] = 'query_result'
                            self.tables_list.addItem(f"{table_name} (query result)")
                        elif os.path.exists(file_path):
                            # Use the database manager to load the file
                            try:
                                loaded_table_name, df = self.db_manager.load_file(file_path)
                                self.tables_list.addItem(f"{loaded_table_name} ({os.path.basename(file_path)})")
                            except Exception as e:
                                QMessageBox.warning(self, "Warning",
                                    f"Failed to load file for table {table_name}:\n{str(e)}")
                                continue
                        else:
                            QMessageBox.warning(self, "Warning",
                                f"Could not find file for table {table_name}: {file_path}")
                            continue
                            
                    except Exception as e:
                        QMessageBox.warning(self, "Warning",
                            f"Failed to load table {table_name}:\n{str(e)}")
                
                    # Update progress for this table
                    current_progress += table_progress_step
                    progress.setValue(int(current_progress))
                    QApplication.processEvents()  # Keep UI responsive
                
                # If the project had database tables but we couldn't connect automatically, notify the user
                if has_database_tables and not database_tables_loaded:
                    QMessageBox.information(self, "Database Connection Required",
                        "This project contains database tables. You need to reconnect to the database to use them.\n\n"
                        "Use the 'Open Database' button to connect to your database file.")
                
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
                
                self.statusBar().showMessage(f'Project loaded from {file_name}')
                progress.close()
                
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
            
            # Save window settings
            window_settings = self.save_window_state()
            settings['window'] = window_settings
            
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
            
        # Block signals temporarily to improve performance when removing multiple tabs
        was_blocked = self.tab_widget.blockSignals(True)
        
        # Remove the tab
        widget = self.tab_widget.widget(index)
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

def main():
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