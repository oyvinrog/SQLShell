from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QCompleter
from PyQt6.QtCore import Qt, QSize, QRect, QStringListModel
from PyQt6.QtGui import QFont, QColor, QTextCursor, QPainter, QBrush

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
        
        # Track last key press for better completion behavior
        self.last_key_was_tab = False
        
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
        
    def update_completer_model(self, words_or_model):
        """Update the completer model with new words or a new model
        
        Args:
            words_or_model: Either a list of words or a QStringListModel
        """
        if not self.completer:
            return
        
        # If a model is passed directly, use it
        if isinstance(words_or_model, QStringListModel):
            self.completer.setModel(words_or_model)
            return
        
        # Otherwise, combine SQL keywords with table/column names and create a new model
        # Use set operations for efficiency
        words_set = set(words_or_model)  # Remove duplicates
        sql_keywords_set = set(self.sql_keywords)
        all_words = list(sql_keywords_set.union(words_set))
        
        # Sort the combined words for better autocomplete experience
        all_words.sort(key=lambda x: (not x.isupper(), x))  # Prioritize SQL keywords (all uppercase)
        
        # Create an optimized model with all words
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
        
        # Get the current prefix for proper replacement
        current_prefix = self.completer.completionPrefix()
        
        # When completing, replace the entire prefix with the completion
        # This ensures exact matches are handled correctly
        if current_prefix:
            # Get positions for text manipulation
            cursor_pos = tc.position()
            tc.setPosition(cursor_pos - len(current_prefix))
            tc.setPosition(cursor_pos, QTextCursor.MoveMode.KeepAnchor)
            tc.removeSelectedText()
        
        # Don't automatically add space when completing with Tab
        # or when completion already ends with special characters
        special_endings = ["(", ")", ",", ";", "."]
        if any(completion.endswith(char) for char in special_endings):
            tc.insertText(completion)
        else:
            # Add space for normal words, but only if activated with Enter/Return
            # not when using Tab for completion
            from_keyboard = self.sender() is None
            add_space = from_keyboard or not self.last_key_was_tab
            tc.insertText(completion + (" " if add_space else ""))
        
        self.setTextCursor(tc)

    def complete(self):
        """Show completion popup"""
        prefix = self.text_under_cursor()
        
        # Don't show popup for empty text or too short prefixes
        if not prefix or len(prefix) < 2:  
            if self.completer and self.completer.popup().isVisible():
                self.completer.popup().hide()
            return
        
        # Track if we're in the middle of a word
        cursor = self.textCursor()
        position = cursor.position()
        block = cursor.block()
        text = block.text()
        
        # Don't show completions if cursor is in the middle of a longer word
        if position < len(text):
            if position < len(text) and position > 0:
                next_char = text[position]
                if next_char.isalnum() or next_char == '_':
                    if self.completer and self.completer.popup().isVisible():
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
            # Handle Tab key to complete the current selection
            if event.key() == Qt.Key.Key_Tab:
                # Get the SELECTED completion (not just the current one)
                popup = self.completer.popup()
                current_index = popup.currentIndex()
                selected_completion = popup.model().data(current_index)
                
                # Accept the selected completion and close popup
                if selected_completion:
                    self.last_key_was_tab = True
                    self.completer.popup().hide()
                    self.insert_completion(selected_completion)
                    self.last_key_was_tab = False
                    return
                event.ignore()
                return
                
            # Let Enter key escape/close the popup without completing
            if event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
                self.completer.popup().hide()
                super().keyPressEvent(event)
                return
            
            # Let Space key escape/close the popup without completing
            if event.key() == Qt.Key.Key_Space:
                self.completer.popup().hide()
                super().keyPressEvent(event)
                return
            
            # Hide popup on Escape
            if event.key() == Qt.Key.Key_Escape:
                self.completer.popup().hide()
                event.ignore()
                return
                
            # Let Up/Down keys navigate the popup
            if event.key() in [Qt.Key.Key_Up, Qt.Key.Key_Down]:
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
            # Only show completion if user is actively typing
            self.complete()
        elif event.key() == Qt.Key.Key_Backspace:
            # Re-evaluate completion when backspacing
            self.complete()
        else:
            # Hide completion popup when inserting space or non-text characters
            if self.completer and self.completer.popup().isVisible():
                self.completer.popup().hide()

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