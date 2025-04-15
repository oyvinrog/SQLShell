import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QHeaderView, QTableWidget, QSplitter, QApplication, 
                             QToolButton, QMenu)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from sqlshell.editor import SQLEditor
from sqlshell.syntax_highlighter import SQLSyntaxHighlighter
from sqlshell.ui import FilterHeader
from sqlshell.styles import get_row_count_label_stylesheet

class QueryTab(QWidget):
    def __init__(self, parent, results_title="RESULTS"):
        super().__init__()
        self.parent = parent
        self.current_df = None
        self.filter_widgets = []
        self.results_title_text = results_title
        self.init_ui()
        
    def init_ui(self):
        """Initialize the tab's UI components"""
        # Set main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for query and results
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(8)
        self.splitter.setChildrenCollapsible(False)
        
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
        
        # Ensure a default completer is available
        if not self.query_edit.completer:
            from PyQt6.QtCore import QStringListModel
            from PyQt6.QtWidgets import QCompleter
            
            # Create a basic completer with SQL keywords if one doesn't exist
            if hasattr(self.query_edit, 'all_sql_keywords'):
                model = QStringListModel(self.query_edit.all_sql_keywords)
                completer = QCompleter()
                completer.setModel(model)
                self.query_edit.set_completer(completer)
        
        # Connect keyboard events for direct handling of Ctrl+Enter
        self.query_edit.installEventFilter(self)
        
        query_layout.addWidget(self.query_edit)
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.execute_btn = QPushButton('Execute Query')
        self.execute_btn.setObjectName("primary_button")
        self.execute_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.execute_btn.clicked.connect(self.execute_query)
        
        self.clear_btn = QPushButton('Clear')
        self.clear_btn.clicked.connect(self.clear_query)
        
        button_layout.addWidget(self.execute_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        self.export_excel_btn = QPushButton('Export to Excel')
        self.export_excel_btn.setIcon(QIcon.fromTheme("x-office-spreadsheet"))
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        
        self.export_parquet_btn = QPushButton('Export to Parquet')
        self.export_parquet_btn.setIcon(QIcon.fromTheme("application-octet-stream"))
        self.export_parquet_btn.clicked.connect(self.export_to_parquet)
        
        button_layout.addWidget(self.export_excel_btn)
        button_layout.addWidget(self.export_parquet_btn)
        
        query_layout.addLayout(button_layout)
        
        # Bottom part - Results section
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(16, 16, 16, 16)
        results_layout.setSpacing(12)
        
        # Results header with row count
        header_layout = QHBoxLayout()
        self.results_title = QLabel(self.results_title_text)
        self.results_title.setObjectName("header_label")
        header_layout.addWidget(self.results_title)
        
        header_layout.addStretch()
        
        self.row_count_label = QLabel("")
        self.row_count_label.setStyleSheet(get_row_count_label_stylesheet())
        header_layout.addWidget(self.row_count_label)
        
        results_layout.addLayout(header_layout)
        
        # Results table with customized header
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        
        # Use custom FilterHeader for filtering
        header = FilterHeader(self.results_table)
        header.set_main_window(self.parent)  # Set reference to main window
        self.results_table.setHorizontalHeader(header)
        
        # Set table properties for better performance with large datasets
        self.results_table.setShowGrid(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.verticalHeader().setVisible(True)
        
        results_layout.addWidget(self.results_table)
        
        # Add widgets to splitter
        self.splitter.addWidget(query_widget)
        self.splitter.addWidget(results_widget)
        
        # Set initial sizes - default 40% query, 60% results
        # This will be better for most uses of the app
        screen = QApplication.primaryScreen()
        if screen:
            # Get available screen height
            available_height = screen.availableGeometry().height()
            # Calculate reasonable query pane size (25-35% depending on screen size)
            if available_height >= 1080:  # Large screens
                query_height = int(available_height * 0.3)  # 30% for query area
                self.splitter.setSizes([query_height, available_height - query_height])
            else:  # Smaller screens
                self.splitter.setSizes([300, 500])  # Default values for smaller screens
        else:
            # Fallback to fixed values if screen detection fails
            self.splitter.setSizes([300, 500])
        
        main_layout.addWidget(self.splitter)
        
    def get_query_text(self):
        """Get the current query text"""
        return self.query_edit.toPlainText()
        
    def set_query_text(self, text):
        """Set the query text"""
        self.query_edit.setPlainText(text)
        
    def execute_query(self):
        """Execute the current query"""
        if hasattr(self.parent, 'execute_query'):
            self.parent.execute_query()
        
    def clear_query(self):
        """Clear the query editor"""
        if hasattr(self.parent, 'clear_query'):
            self.parent.clear_query()
        
    def export_to_excel(self):
        """Export results to Excel"""
        if hasattr(self.parent, 'export_to_excel'):
            self.parent.export_to_excel()
        
    def export_to_parquet(self):
        """Export results to Parquet"""
        if hasattr(self.parent, 'export_to_parquet'):
            self.parent.export_to_parquet()
            
    def eventFilter(self, obj, event):
        """Event filter to intercept Ctrl+Enter and send it to the main window"""
        from PyQt6.QtCore import QEvent, Qt
        
        # Check if it's a key press event
        if event.type() == QEvent.Type.KeyPress:
            # Check for Ctrl+Enter specifically
            if (event.key() == Qt.Key.Key_Return and 
                event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                
                # Hide any autocomplete popup if it's visible
                if hasattr(obj, 'completer') and obj.completer and obj.completer.popup().isVisible():
                    obj.completer.popup().hide()
                
                # Execute the query via the parent (main window)
                if hasattr(self.parent, 'execute_query'):
                    self.parent.execute_query()
                    # Mark event as handled
                    return True
                    
        # Default - let the event propagate normally
        return super().eventFilter(obj, event) 