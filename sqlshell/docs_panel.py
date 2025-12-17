"""
DuckDB Documentation Panel Widget

A dynamic panel that displays DuckDB SQL documentation based on 
the user's typing in the SQL editor.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QSizePolicy, QPushButton, QTextBrowser, QLineEdit,
    QListWidget, QListWidgetItem, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QColor, QDesktopServices, QTextCursor
from typing import Optional, List

from sqlshell.duckdb_docs_lookup import get_docs_searcher, DocEntry


class DocEntryWidget(QFrame):
    """Widget to display a single documentation entry."""
    
    def __init__(self, doc: DocEntry, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.setObjectName("doc_entry")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        # Header with name and category
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        name_label = QLabel(self.doc.name)
        name_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            color: #2C3E50;
        """)
        header_layout.addWidget(name_label)
        
        category_label = QLabel(self.doc.category)
        category_label.setStyleSheet("""
            font-size: 11px;
            color: #7F8C8D;
            background-color: #ECF0F1;
            padding: 2px 8px;
            border-radius: 10px;
        """)
        header_layout.addWidget(category_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Syntax
        syntax_frame = QFrame()
        syntax_frame.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #E9ECEF;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        syntax_layout = QVBoxLayout(syntax_frame)
        syntax_layout.setContentsMargins(8, 6, 8, 6)
        
        syntax_label = QLabel(self.doc.syntax)
        syntax_label.setWordWrap(True)
        syntax_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        syntax_label.setStyleSheet("""
            font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
            font-size: 12px;
            color: #E74C3C;
        """)
        syntax_layout.addWidget(syntax_label)
        layout.addWidget(syntax_frame)
        
        # Description
        desc_label = QLabel(self.doc.description)
        desc_label.setWordWrap(True)
        desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        desc_label.setStyleSheet("""
            font-size: 12px;
            color: #34495E;
            line-height: 1.4;
        """)
        layout.addWidget(desc_label)
        
        # Examples
        if self.doc.examples:
            examples_label = QLabel("Examples:")
            examples_label.setStyleSheet("""
                font-size: 11px;
                font-weight: bold;
                color: #7F8C8D;
                margin-top: 4px;
            """)
            layout.addWidget(examples_label)
            
            for example in self.doc.examples[:3]:  # Show max 3 examples
                example_frame = QFrame()
                example_frame.setStyleSheet("""
                    QFrame {
                        background-color: #2C3E50;
                        border-radius: 4px;
                    }
                """)
                example_layout = QVBoxLayout(example_frame)
                example_layout.setContentsMargins(8, 6, 8, 6)
                
                example_label = QLabel(example)
                example_label.setWordWrap(True)
                example_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                example_label.setStyleSheet("""
                    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
                    font-size: 11px;
                    color: #ECF0F1;
                """)
                example_layout.addWidget(example_label)
                layout.addWidget(example_frame)
        
        # Related functions
        if self.doc.related:
            related_label = QLabel(f"Related: {', '.join(self.doc.related[:5])}")
            related_label.setWordWrap(True)
            related_label.setStyleSheet("""
                font-size: 11px;
                color: #3498DB;
                margin-top: 4px;
            """)
            layout.addWidget(related_label)
        
        # Documentation link
        if self.doc.url:
            link_btn = QPushButton("📖 Open Documentation")
            link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            link_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #3498DB;
                    border: none;
                    font-size: 11px;
                    text-align: left;
                    padding: 2px 0;
                }
                QPushButton:hover {
                    color: #2980B9;
                    text-decoration: underline;
                }
            """)
            link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.doc.url)))
            layout.addWidget(link_btn)
        
        self.setStyleSheet("""
            #doc_entry {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                margin-bottom: 8px;
            }
            #doc_entry:hover {
                border-color: #3498DB;
            }
        """)


class DocsPanel(QWidget):
    """
    A panel that displays DuckDB documentation dynamically based on user typing.
    
    This widget monitors text changes in the SQL editor and searches the
    DuckDB documentation for relevant information.
    """
    
    # Signal emitted when a doc entry is clicked to insert into editor
    insert_requested = pyqtSignal(str)  # Emits the syntax string
    
    # Signal to request closing the panel
    close_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.searcher = get_docs_searcher()
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
        self._pending_query = ""
        self._current_results: List[DocEntry] = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the panel UI."""
        self.setMinimumWidth(280)
        self.setMaximumWidth(450)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #3498DB;
                border: none;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        title = QLabel("📚 DuckDB Docs")
        title.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            color: white;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
        close_btn.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(close_btn)
        
        main_layout.addWidget(header)
        
        # Search box
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #ECF0F1;
                border: none;
            }
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(12, 8, 12, 8)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search functions, syntax...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3498DB;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_input)
        
        main_layout.addWidget(search_frame)
        
        # Status label
        self.status_label = QLabel("Type in the editor or search above")
        self.status_label.setStyleSheet("""
            font-size: 11px;
            color: #7F8C8D;
            padding: 8px 12px;
            background-color: #FAFAFA;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Results area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FAFAFA;
            }
            QScrollBar:vertical {
                width: 8px;
                background-color: #F0F0F0;
            }
            QScrollBar::handle:vertical {
                background-color: #BDC3C7;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #95A5A6;
            }
        """)
        
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setContentsMargins(8, 8, 8, 8)
        self.results_layout.setSpacing(8)
        self.results_layout.addStretch()
        
        self.scroll_area.setWidget(self.results_widget)
        main_layout.addWidget(self.scroll_area, 1)
        
        # Category quick links
        categories_frame = QFrame()
        categories_frame.setStyleSheet("""
            QFrame {
                background-color: #ECF0F1;
                border-top: 1px solid #BDC3C7;
            }
        """)
        categories_layout = QHBoxLayout(categories_frame)
        categories_layout.setContentsMargins(8, 6, 8, 6)
        categories_layout.setSpacing(4)
        
        quick_categories = ["String", "Aggregate", "Window", "Date/Time", "Regex"]
        for cat in quick_categories:
            btn = QPushButton(cat)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #34495E;
                    border: 1px solid #BDC3C7;
                    border-radius: 3px;
                    padding: 3px 6px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #3498DB;
                    color: white;
                    border-color: #3498DB;
                }
            """)
            btn.clicked.connect(lambda checked, c=cat: self._search_category(c))
            categories_layout.addWidget(btn)
        
        categories_layout.addStretch()
        main_layout.addWidget(categories_frame)
        
        self.setStyleSheet("""
            DocsPanel {
                background-color: #FAFAFA;
                border-left: 1px solid #BDC3C7;
            }
        """)
    
    def _on_search_text_changed(self, text: str):
        """Handle search input text change."""
        self._pending_query = text
        self._search_timer.start(150)  # Debounce
    
    def _search_category(self, category: str):
        """Search for a specific category."""
        self.search_input.setText(category)
    
    def search_from_editor(self, text: str):
        """
        Called when the editor text changes.
        Extracts the current word/context and searches.
        """
        if not text:
            return
        
        # Don't override if user is manually searching
        if self.search_input.hasFocus():
            return
        
        # Extract the current word being typed
        word = self._extract_current_word(text)
        if word and len(word) >= 2:
            self._pending_query = word
            self._search_timer.start(300)  # Slightly longer debounce for editor
    
    def _extract_current_word(self, text: str) -> str:
        """Extract the current word from the text at cursor position."""
        if not text:
            return ""
        
        # Get the last word being typed
        # Look for word characters (alphanumeric and underscore)
        import re
        
        # Find the last word in the text
        words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text)
        if words:
            return words[-1]
        return ""
    
    def _do_search(self):
        """Perform the actual search."""
        query = self._pending_query.strip()
        
        if not query or len(query) < 2:
            self._clear_results()
            self.status_label.setText("Type at least 2 characters to search")
            self.status_label.show()
            return
        
        results = self.searcher.search(query, max_results=8)
        self._current_results = results
        self._display_results(results, query)
    
    def _clear_results(self):
        """Clear all result widgets."""
        while self.results_layout.count() > 1:  # Keep the stretch
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _display_results(self, results: List[DocEntry], query: str):
        """Display search results."""
        self._clear_results()
        
        if not results:
            self.status_label.setText(f"No results for '{query}'")
            self.status_label.show()
            return
        
        self.status_label.setText(f"Found {len(results)} result{'s' if len(results) != 1 else ''}")
        
        for doc in results:
            entry_widget = DocEntryWidget(doc)
            # Insert before the stretch
            self.results_layout.insertWidget(self.results_layout.count() - 1, entry_widget)
        
        # Scroll to top
        self.scroll_area.verticalScrollBar().setValue(0)
    
    def update_from_cursor_position(self, text_before_cursor: str):
        """
        Update documentation based on cursor position in the editor.
        
        Args:
            text_before_cursor: All text before the current cursor position
        """
        if not text_before_cursor:
            return
        
        # Extract the current context (last word or function being typed)
        word = self._extract_current_word(text_before_cursor)
        
        if word and len(word) >= 2:
            # Don't update if the search input is focused (user is manually searching)
            if not self.search_input.hasFocus():
                self._pending_query = word
                self._search_timer.start(250)


class DocsPanelManager:
    """
    Manages the documentation panel integration with the SQL editor.
    
    This class handles:
    - Creating and positioning the docs panel
    - Connecting editor signals to the panel
    - Managing panel visibility
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.panel: Optional[DocsPanel] = None
        self._is_visible = False
    
    def create_panel(self) -> DocsPanel:
        """Create the documentation panel if it doesn't exist."""
        if self.panel is None:
            self.panel = DocsPanel()
            self.panel.close_requested.connect(self.hide_panel)
        return self.panel
    
    def show_panel(self):
        """Show the documentation panel."""
        self.create_panel()
        self._is_visible = True
        self.panel.show()
    
    def hide_panel(self):
        """Hide the documentation panel."""
        if self.panel:
            self._is_visible = False
            self.panel.hide()
    
    def toggle_panel(self):
        """Toggle the documentation panel visibility."""
        if self._is_visible:
            self.hide_panel()
        else:
            self.show_panel()
    
    def is_visible(self) -> bool:
        """Check if the panel is currently visible."""
        return self._is_visible
    
    def update_from_editor(self, text_before_cursor: str):
        """Update the panel based on editor content."""
        if self.panel and self._is_visible:
            self.panel.update_from_cursor_position(text_before_cursor)

