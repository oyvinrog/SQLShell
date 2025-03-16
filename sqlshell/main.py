import sys
import os
import duckdb
import sqlite3
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTextEdit, QPushButton, QFileDialog,
                           QLabel, QSplitter, QListWidget, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox, QPlainTextEdit,
                           QCompleter, QFrame, QToolButton, QSizePolicy, QTabWidget,
                           QStyleFactory, QToolBar, QStatusBar)
from PyQt6.QtCore import Qt, QAbstractTableModel, QRegularExpression, QRect, QSize, QStringListModel, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat, QPainter, QTextFormat, QTextCursor, QIcon, QPalette, QLinearGradient, QBrush, QPixmap
import numpy as np
from datetime import datetime
from sqlshell.sqlshell import create_test_data  # Import from the correct location

class SQLSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        # SQL Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))  # Blue
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "\\bSELECT\\b", "\\bFROM\\b", "\\bWHERE\\b", "\\bAND\\b", "\\bOR\\b",
            "\\bINNER\\b", "\\bOUTER\\b", "\\bLEFT\\b", "\\bRIGHT\\b", "\\bJOIN\\b",
            "\\bON\\b", "\\bGROUP\\b", "\\bBY\\b", "\\bHAVING\\b", "\\bORDER\\b",
            "\\bLIMIT\\b", "\\bOFFSET\\b", "\\bUNION\\b", "\\bEXCEPT\\b", "\\bINTERSECT\\b",
            "\\bCREATE\\b", "\\bTABLE\\b", "\\bINDEX\\b", "\\bVIEW\\b", "\\bINSERT\\b",
            "\\bINTO\\b", "\\bVALUES\\b", "\\bUPDATE\\b", "\\bSET\\b", "\\bDELETE\\b",
            "\\bTRUNCATE\\b", "\\bALTER\\b", "\\bADD\\b", "\\bDROP\\b", "\\bCOLUMN\\b",
            "\\bCONSTRAINT\\b", "\\bPRIMARY\\b", "\\bKEY\\b", "\\bFOREIGN\\b", "\\bREFERENCES\\b",
            "\\bUNIQUE\\b", "\\bNOT\\b", "\\bNULL\\b", "\\bIS\\b", "\\bDISTINCT\\b",
            "\\bCASE\\b", "\\bWHEN\\b", "\\bTHEN\\b", "\\bELSE\\b", "\\bEND\\b",
            "\\bAS\\b", "\\bWITH\\b", "\\bBETWEEN\\b", "\\bLIKE\\b", "\\bIN\\b",
            "\\bEXISTS\\b", "\\bALL\\b", "\\bANY\\b", "\\bSOME\\b", "\\bDESC\\b", "\\bASC\\b"
        ]
        for pattern in keywords:
            regex = QRegularExpression(pattern, QRegularExpression.PatternOption.CaseInsensitiveOption)
            self.highlighting_rules.append((regex, keyword_format))

        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#AA00AA"))  # Purple
        functions = [
            "\\bAVG\\b", "\\bCOUNT\\b", "\\bSUM\\b", "\\bMAX\\b", "\\bMIN\\b",
            "\\bCOALESCE\\b", "\\bNVL\\b", "\\bNULLIF\\b", "\\bCAST\\b", "\\bCONVERT\\b",
            "\\bLOWER\\b", "\\bUPPER\\b", "\\bTRIM\\b", "\\bLTRIM\\b", "\\bRTRIM\\b",
            "\\bLENGTH\\b", "\\bSUBSTRING\\b", "\\bREPLACE\\b", "\\bCONCAT\\b",
            "\\bROUND\\b", "\\bFLOOR\\b", "\\bCEIL\\b", "\\bABS\\b", "\\bMOD\\b",
            "\\bCURRENT_DATE\\b", "\\bCURRENT_TIME\\b", "\\bCURRENT_TIMESTAMP\\b",
            "\\bEXTRACT\\b", "\\bDATE_PART\\b", "\\bTO_CHAR\\b", "\\bTO_DATE\\b"
        ]
        for pattern in functions:
            regex = QRegularExpression(pattern, QRegularExpression.PatternOption.CaseInsensitiveOption)
            self.highlighting_rules.append((regex, function_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#009900"))  # Green
        self.highlighting_rules.append((
            QRegularExpression("\\b[0-9]+\\b"),
            number_format
        ))

        # Single-line string literals
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CC6600"))  # Orange/Brown
        self.highlighting_rules.append((
            QRegularExpression("'[^']*'"),
            string_format
        ))
        self.highlighting_rules.append((
            QRegularExpression("\"[^\"]*\""),
            string_format
        ))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#777777"))  # Gray
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((
            QRegularExpression("--[^\n]*"),
            comment_format
        ))
        
        # Multi-line comments
        self.comment_start_expression = QRegularExpression("/\\*")
        self.comment_end_expression = QRegularExpression("\\*/")
        self.multi_line_comment_format = comment_format

    def highlightBlock(self, text):
        # Apply regular expression highlighting rules
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

        # Handle multi-line comments
        self.setCurrentBlockState(0)
        
        # If previous block was inside a comment, check if this block continues it
        start_index = 0
        if self.previousBlockState() != 1:
            # Find the start of a comment
            start_match = self.comment_start_expression.match(text)
            if start_match.hasMatch():
                start_index = start_match.capturedStart()
            else:
                return
            
        while start_index >= 0:
            # Find the end of the comment
            end_match = self.comment_end_expression.match(text, start_index)
            
            # If end match found
            if end_match.hasMatch():
                end_index = end_match.capturedStart()
                comment_length = end_index - start_index + end_match.capturedLength()
                self.setFormat(start_index, comment_length, self.multi_line_comment_format)
                
                # Look for next comment
                start_match = self.comment_start_expression.match(text, start_index + comment_length)
                if start_match.hasMatch():
                    start_index = start_match.capturedStart()
                else:
                    start_index = -1
            else:
                # No end found, comment continues to next block
                self.setCurrentBlockState(1)  # Still inside comment
                comment_length = len(text) - start_index
                self.setFormat(start_index, comment_length, self.multi_line_comment_format)
                start_index = -1

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

class SQLEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        
        # Set monospaced font
        font = QFont("Consolas", 12)  # Increased font size for better readability
        font.setFixedPitch(True)
        self.setFont(font)
        
        # Connect signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        
        # Initialize
        self.update_line_number_area_width(0)
        
        # Set tab width to 4 spaces
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(' '))
        
        # Set placeholder text
        self.setPlaceholderText("Enter your SQL query here...")
        
        # Initialize completer
        self.completer = None
        
        # SQL Keywords for autocomplete
        self.sql_keywords = [
            "SELECT", "FROM", "WHERE", "AND", "OR", "INNER", "OUTER", "LEFT", "RIGHT", "JOIN",
            "ON", "GROUP", "BY", "HAVING", "ORDER", "LIMIT", "OFFSET", "UNION", "EXCEPT", "INTERSECT",
            "CREATE", "TABLE", "INDEX", "VIEW", "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE",
            "TRUNCATE", "ALTER", "ADD", "DROP", "COLUMN", "CONSTRAINT", "PRIMARY", "KEY", "FOREIGN", "REFERENCES",
            "UNIQUE", "NOT", "NULL", "IS", "DISTINCT", "CASE", "WHEN", "THEN", "ELSE", "END",
            "AS", "WITH", "BETWEEN", "LIKE", "IN", "EXISTS", "ALL", "ANY", "SOME", "DESC", "ASC",
            "AVG", "COUNT", "SUM", "MAX", "MIN", "COALESCE", "CAST", "CONVERT"
        ]
        
        # Initialize with SQL keywords
        self.set_completer(QCompleter(self.sql_keywords))
        
        # Set modern selection color
        self.selection_color = QColor("#3498DB")
        self.selection_color.setAlpha(50)  # Make it semi-transparent

    def set_completer(self, completer):
        """Set the completer for the editor"""
        if self.completer:
            self.completer.disconnect(self)
            
        self.completer = completer
        
        if not self.completer:
            return
            
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.activated.connect(self.insert_completion)
        
    def update_completer_model(self, words):
        """Update the completer model with new words"""
        if not self.completer:
            return
            
        # Combine SQL keywords with table/column names
        all_words = self.sql_keywords + words
        
        # Create a model with all words
        model = QStringListModel()
        model.setStringList(all_words)
        
        # Set the model to the completer
        self.completer.setModel(model)
        
    def text_under_cursor(self):
        """Get the text under the cursor for completion"""
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()
        
    def insert_completion(self, completion):
        """Insert the completion text"""
        if self.completer.widget() != self:
            return
            
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:] + " ")
        self.setTextCursor(tc)
        
    def complete(self):
        """Show completion popup"""
        prefix = self.text_under_cursor()
        
        if not prefix or len(prefix) < 2:  # Only show completions for words with at least 2 characters
            if self.completer.popup().isVisible():
                self.completer.popup().hide()
            return
            
        self.completer.setCompletionPrefix(prefix)
        
        # If no completions, hide popup
        if self.completer.completionCount() == 0:
            self.completer.popup().hide()
            return
            
        # Get popup and position it under the current text
        popup = self.completer.popup()
        popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
        
        # Calculate position for the popup
        cr = self.cursorRect()
        cr.setWidth(self.completer.popup().sizeHintForColumn(0) + 
                   self.completer.popup().verticalScrollBar().sizeHint().width())
        
        # Show the popup
        self.completer.complete(cr)

    def keyPressEvent(self, event):
        # Handle completer popup navigation
        if self.completer and self.completer.popup().isVisible():
            # Handle navigation keys for the popup
            if event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab, 
                              Qt.Key.Key_Escape, Qt.Key.Key_Up, Qt.Key.Key_Down]:
                event.ignore()
                return
        
        # Handle special key combinations
        if event.key() == Qt.Key.Key_Tab:
            # Insert 4 spaces instead of a tab character
            self.insertPlainText("    ")
            return
            
        # Auto-indentation for new lines
        if event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text()
            
            # Get the indentation of the current line
            indentation = ""
            for char in text:
                if char.isspace():
                    indentation += char
                else:
                    break
            
            # Check if line ends with an opening bracket or keywords that should increase indentation
            increase_indent = ""
            if text.strip().endswith("(") or any(text.strip().upper().endswith(keyword) for keyword in 
                                               ["SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING"]):
                increase_indent = "    "
                
            # Insert new line with proper indentation
            super().keyPressEvent(event)
            self.insertPlainText(indentation + increase_indent)
            return
            
        # Handle keyboard shortcuts
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Space:
                # Show completion popup
                self.complete()
                return
            elif event.key() == Qt.Key.Key_K:
                # Comment/uncomment the selected lines
                self.toggle_comment()
                return
                
        # For normal key presses
        super().keyPressEvent(event)
        
        # Check for autocomplete after typing
        if event.text() and not event.text().isspace():
            self.complete()

    def paintEvent(self, event):
        # Call the parent's paintEvent first
        super().paintEvent(event)
        
        # Get the current cursor
        cursor = self.textCursor()
        
        # If there's a selection, paint custom highlight
        if cursor.hasSelection():
            # Create a painter for this widget
            painter = QPainter(self.viewport())
            
            # Get the selection start and end positions
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            
            # Create temporary cursor to get the rectangles
            temp_cursor = QTextCursor(cursor)
            
            # Move to start and get the starting position
            temp_cursor.setPosition(start)
            start_pos = self.cursorRect(temp_cursor)
            
            # Move to end and get the ending position
            temp_cursor.setPosition(end)
            end_pos = self.cursorRect(temp_cursor)
            
            # Set the highlight color with transparency
            painter.setBrush(QBrush(self.selection_color))
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Draw the highlight rectangle
            if start_pos.top() == end_pos.top():
                # Single line selection
                painter.drawRect(QRect(start_pos.left(), start_pos.top(),
                                     end_pos.right() - start_pos.left(), start_pos.height()))
            else:
                # Multi-line selection
                # First line
                painter.drawRect(QRect(start_pos.left(), start_pos.top(),
                                     self.viewport().width() - start_pos.left(), start_pos.height()))
                
                # Middle lines (if any)
                if end_pos.top() > start_pos.top() + start_pos.height():
                    painter.drawRect(QRect(0, start_pos.top() + start_pos.height(),
                                         self.viewport().width(),
                                         end_pos.top() - (start_pos.top() + start_pos.height())))
                
                # Last line
                painter.drawRect(QRect(0, end_pos.top(), end_pos.right(), end_pos.height()))
            
            painter.end()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        # Show temporary hint in status bar when editor gets focus
        if hasattr(self.parent(), 'statusBar'):
            self.parent().parent().parent().statusBar().showMessage('Press Ctrl+Space for autocomplete', 2000)

    def toggle_comment(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            # Get the selected text
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            
            # Remember the selection
            cursor.setPosition(start)
            start_block = cursor.blockNumber()
            cursor.setPosition(end)
            end_block = cursor.blockNumber()
            
            # Process each line in the selection
            cursor.setPosition(start)
            cursor.beginEditBlock()
            
            for _ in range(start_block, end_block + 1):
                # Move to start of line
                cursor.movePosition(cursor.MoveOperation.StartOfLine)
                
                # Check if the line is already commented
                line_text = cursor.block().text().lstrip()
                if line_text.startswith('--'):
                    # Remove comment
                    pos = cursor.block().text().find('--')
                    cursor.setPosition(cursor.block().position() + pos)
                    cursor.deleteChar()
                    cursor.deleteChar()
                else:
                    # Add comment
                    cursor.insertText('--')
                
                # Move to next line if not at the end
                if not cursor.atEnd():
                    cursor.movePosition(cursor.MoveOperation.NextBlock)
            
            cursor.endEditBlock()
        else:
            # Comment/uncomment current line
            cursor.movePosition(cursor.MoveOperation.StartOfLine)
            cursor.movePosition(cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor)
            line_text = cursor.selectedText().lstrip()
            
            cursor.movePosition(cursor.MoveOperation.StartOfLine)
            if line_text.startswith('--'):
                # Remove comment
                pos = cursor.block().text().find('--')
                cursor.setPosition(cursor.block().position() + pos)
                cursor.deleteChar()
                cursor.deleteChar()
            else:
                # Add comment
                cursor.insertText('--')

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#f0f0f0"))  # Light gray background
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#808080"))  # Gray text
                painter.drawText(0, top, self.line_number_area.width() - 5, 
                                self.fontMetrics().height(),
                                Qt.AlignmentFlag.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

class SQLShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_db_type = 'duckdb'  # Default to DuckDB
        self.conn = duckdb.connect(':memory:')  # Create in-memory DuckDB connection by default
        self.loaded_tables = {}  # Keep track of loaded tables
        self.table_columns = {}  # Keep track of table columns
        
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
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.horizontalHeader().setSectionsMovable(True)
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

    def format_value(self, value):
        """Format values for display"""
        if pd.isna(value):
            return 'NULL'
        elif isinstance(value, (int, np.integer)):
            return f"{value:,}"
        elif isinstance(value, (float, np.floating)):
            return f"{value:,.2f}"
        elif isinstance(value, (datetime, pd.Timestamp)):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        return str(value)

    def populate_table(self, df):
        """Populate the table widget with DataFrame content"""
        if len(df) == 0:
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(0)
            self.row_count_label.setText("No results")
            return

        # Set dimensions
        self.results_table.setRowCount(len(df))
        self.results_table.setColumnCount(len(df.columns))
        
        # Set headers
        self.results_table.setHorizontalHeaderLabels(df.columns)
        
        # Populate data
        for i, (_, row) in enumerate(df.iterrows()):
            for j, value in enumerate(row):
                formatted_value = self.format_value(value)
                item = QTableWidgetItem(formatted_value)
                
                # Set alignment based on data type
                if isinstance(value, (int, float, np.integer, np.floating)):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
                # Make cells read-only
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Apply special styling for NULL values
                if pd.isna(value):
                    item.setForeground(QColor(self.colors['text_light']))
                    item.setBackground(QColor("#F8F9FA"))
                
                self.results_table.setItem(i, j, item)
        
        # Auto-adjust column widths while ensuring minimum and maximum sizes
        self.results_table.resizeColumnsToContents()
        for i in range(len(df.columns)):
            width = self.results_table.columnWidth(i)
            self.results_table.setColumnWidth(i, min(max(width, 80), 300))
        
        # Update row count
        row_text = "row" if len(df) == 1 else "rows"
        self.row_count_label.setText(f"{len(df):,} {row_text}")
        
        # Apply zebra striping
        for i in range(len(df)):
            if i % 2 == 0:
                for j in range(len(df.columns)):
                    item = self.results_table.item(i, j)
                    if item and not pd.isna(df.iloc[i, j]):
                        item.setBackground(QColor("#FFFFFF"))
            else:
                for j in range(len(df.columns)):
                    item = self.results_table.item(i, j)
                    if item and not pd.isna(df.iloc[i, j]):
                        item.setBackground(QColor("#F8F9FA"))

    def browse_files(self):
        if not self.conn:
            # Create a default in-memory DuckDB connection if none exists
            self.conn = duckdb.connect(':memory:')
            self.current_db_type = 'duckdb'
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
                if self.current_db_type == 'sqlite':
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
        """Open a database file (DuckDB or SQLite)"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Database File",
            "",
            "Database Files (*.db);;All Files (*)"
        )
        
        if not file_name:
            return
            
        try:
            # Try to detect database type
            is_sqlite = self.is_sqlite_db(file_name)
            
            # Close existing connection if any
            if self.conn:
                self.conn.close()
            
            # Connect to the database
            if is_sqlite:
                self.conn = sqlite3.connect(file_name)
                self.current_db_type = 'sqlite'
            else:
                self.conn = duckdb.connect(file_name)
                self.current_db_type = 'duckdb'
            
            # Clear existing tables
            self.loaded_tables.clear()
            self.tables_list.clear()
            
            # Load tables
            self.load_database_tables()
            
            # Update UI
            db_type = "SQLite" if is_sqlite else "DuckDB"
            self.db_info_label.setText(f"Connected to: {os.path.basename(file_name)} ({db_type})")
            self.statusBar().showMessage(f'Successfully opened {db_type} database: {file_name}')
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open database: {str(e)}")
            self.statusBar().showMessage('Error opening database')

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
            if self.current_db_type == 'sqlite':
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
        query = self.query_edit.toPlainText().strip()
        if not query:
            return
        
        if not self.conn:
            QMessageBox.warning(self, "No Connection", "No database connection available. Creating an in-memory DuckDB database.")
            self.conn = duckdb.connect(':memory:')
            self.current_db_type = 'duckdb'
            self.db_info_label.setText("Connected to: in-memory DuckDB")
        
        # Show loading indicator in status bar
        self.statusBar().showMessage('Executing query...')
        
        try:
            # Reset results title
            results_title = self.findChild(QLabel, "header_label", Qt.FindChildOption.FindChildrenRecursively)
            if results_title:
                results_title.setText("RESULTS")
            
            if self.current_db_type == 'sqlite':
                # Execute SQLite query and convert to DataFrame
                result = pd.read_sql_query(query, self.conn)
            else:
                # Execute DuckDB query
                result = self.conn.execute(query).fetchdf()
                
            self.populate_table(result)
            
            # Show success message with query stats
            execution_time = datetime.now().strftime("%H:%M:%S")
            row_count = len(result)
            self.statusBar().showMessage(f'Query executed successfully at {execution_time} - {row_count:,} rows returned')
            
        except Exception as e:
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(0)
            self.row_count_label.setText("Error")
            self.statusBar().showMessage('Error executing query')
            
            # Show error message with modern styling
            error_msg = str(e)
            if "not found" in error_msg.lower():
                error_msg += "\nMake sure the table name is correct and the table is loaded."
            elif "syntax error" in error_msg.lower():
                error_msg += "\nPlease check your SQL syntax."
                
            error_box = QMessageBox(self)
            error_box.setIcon(QMessageBox.Icon.Critical)
            error_box.setWindowTitle("Query Error")
            error_box.setText("Error executing query")
            error_box.setInformativeText(error_msg)
            error_box.setDetailedText(f"Query:\n{query}")
            error_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            error_box.exec()

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
                if self.current_db_type == 'sqlite':
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
    s.orderid,
    s.orderdate,
    c.customername,
    p.productname,
    s.quantity,
    s.unitprice,
    (s.quantity * s.unitprice) AS total_amount
FROM 
    sample_sales_data s
    INNER JOIN customer_data c ON c.customerid = s.customerid
    INNER JOIN product_catalog p ON p.productid = s.productid
ORDER BY 
    s.orderdate DESC
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
            
            self.statusBar().showMessage(f'Data exported to {file_name}')
            
            # Show success message
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"Data has been exported to:\n{file_name}",
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
            
            self.statusBar().showMessage(f'Data exported to {file_name}')
            
            # Show success message
            QMessageBox.information(
                self, 
                "Export Successful", 
                f"Data has been exported to:\n{file_name}",
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

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Apply custom palette for the entire application
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#ECF0F1"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#2C3E50"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F5F5F5"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2C3E50"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#2C3E50"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#3498DB"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#3498DB"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#3498DB"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)
    
    # Set default font
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)
    
    # Create and show the application
    sql_shell = SQLShell()
    
    # Set application icon (if available)
    try:
        app_icon = QIcon("sqlshell/resources/icon.png")
        sql_shell.setWindowIcon(app_icon)
    except:
        # If icon not found, continue without it
        pass
    
    sql_shell.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 