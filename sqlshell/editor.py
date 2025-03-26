from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QCompleter
from PyQt6.QtCore import Qt, QSize, QRect, QStringListModel
from PyQt6.QtGui import QFont, QColor, QTextCursor, QPainter, QBrush
import re

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
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # SQL Keywords for autocomplete, organized by category for context-aware completion
        self.sql_keywords = {
            'basic': [
                "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "EXISTS", 
                "LIKE", "BETWEEN", "IS NULL", "IS NOT NULL", "AS"
            ],
            'join': [
                "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", 
                "LEFT OUTER JOIN", "RIGHT OUTER JOIN", "FULL OUTER JOIN", 
                "CROSS JOIN", "NATURAL JOIN", "ON", "USING"
            ],
            'aggregation': [
                "GROUP BY", "HAVING", "SUM", "COUNT", "AVG", "MIN", "MAX", 
                "COUNT(*)", "COUNT(DISTINCT"
            ],
            'ordering': [
                "ORDER BY", "ASC", "DESC", "NULLS FIRST", "NULLS LAST", 
                "LIMIT", "OFFSET"
            ],
            'table_ops': [
                "CREATE TABLE", "DROP TABLE", "ALTER TABLE", "ADD COLUMN", 
                "DROP COLUMN", "TRUNCATE TABLE", "RENAME TO"
            ],
            'data_ops': [
                "INSERT INTO", "VALUES", "UPDATE", "SET", "DELETE FROM", 
                "MERGE INTO", "UPSERT"
            ],
            'conditionals': [
                "CASE", "WHEN", "THEN", "ELSE", "END", "COALESCE", "NULLIF", 
                "GREATEST", "LEAST"
            ],
            'functions': [
                "CAST(", "CONVERT(", "TO_CHAR(", "TO_DATE(", "TO_NUMBER(", 
                "EXTRACT(", "SUBSTR(", "LOWER(", "UPPER(", "TRIM(", "ROUND(",
                "DATE_TRUNC(", "CONCAT(", "REPLACE(", "REGEXP_REPLACE(",
                "CURRENT_DATE", "CURRENT_TIME", "CURRENT_TIMESTAMP", "NOW()"
            ],
            'types': [
                "INTEGER", "INT", "BIGINT", "SMALLINT", "TINYINT", "NUMERIC", 
                "DECIMAL", "FLOAT", "REAL", "DOUBLE", "BOOLEAN", "CHAR", 
                "VARCHAR", "TEXT", "DATE", "TIME", "TIMESTAMP", "INTERVAL", 
                "UUID", "JSON", "JSONB", "ARRAY", "BLOB"
            ],
            'window': [
                "OVER (", "PARTITION BY", "ORDER BY", "ROWS BETWEEN", "RANGE BETWEEN", 
                "UNBOUNDED PRECEDING", "CURRENT ROW", "UNBOUNDED FOLLOWING", 
                "ROW_NUMBER()", "RANK()", "DENSE_RANK()", "LEAD(", "LAG("
            ],
            'other': [
                "WITH", "UNION", "UNION ALL", "INTERSECT", "EXCEPT", "DISTINCT", 
                "ALL", "ANY", "SOME", "RECURSIVE", "GROUPING SETS", "CUBE", "ROLLUP"
            ]
        }
        
        # Flattened list of all SQL keywords
        self.all_sql_keywords = []
        for category in self.sql_keywords.values():
            self.all_sql_keywords.extend(category)
        
        # Common SQL patterns with placeholders
        self.sql_patterns = [
            "SELECT * FROM $table WHERE $column = $value",
            "SELECT $columns FROM $table GROUP BY $column HAVING $condition",
            "SELECT $columns FROM $table ORDER BY $column $direction LIMIT $limit",
            "SELECT $table1.$column1, $table2.$column2 FROM $table1 JOIN $table2 ON $table1.$column = $table2.$column",
            "INSERT INTO $table ($columns) VALUES ($values)",
            "UPDATE $table SET $column = $value WHERE $condition",
            "DELETE FROM $table WHERE $condition",
            "WITH $cte AS (SELECT * FROM $table) SELECT * FROM $cte WHERE $condition"
        ]
        
        # Initialize with SQL keywords
        self.set_completer(QCompleter(self.all_sql_keywords))
        
        # Set modern selection color
        self.selection_color = QColor("#3498DB")
        self.selection_color.setAlpha(50)  # Make it semi-transparent
        
        # Tables and columns cache for context-aware completion
        self.tables_cache = {}  # {table_name: [columns]}
        self.last_update_time = 0

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
            
            # Update our tables and columns cache for context-aware completion
            try:
                words = words_or_model.stringList()
                self._update_tables_cache(words)
            except Exception:
                pass
                
            return
        
        # Update tables cache
        self._update_tables_cache(words_or_model)
        
        # Otherwise, combine SQL keywords with table/column names and create a new model
        # Use set operations for efficiency
        words_set = set(words_or_model)  # Remove duplicates
        sql_keywords_set = set(self.all_sql_keywords)
        all_words = list(sql_keywords_set.union(words_set))
        
        # Sort the combined words for better autocomplete experience
        all_words.sort(key=lambda x: (not x.isupper(), x))  # Prioritize SQL keywords (all uppercase)
        
        # Create an optimized model with all words
        model = QStringListModel()
        model.setStringList(all_words)
        
        # Set the model to the completer
        self.completer.setModel(model)
        
    def _update_tables_cache(self, words):
        """Update internal tables and columns cache from word list"""
        self.tables_cache = {}
        
        # Create a map of tables to columns
        for word in words:
            if '.' in word:
                # This is a qualified column (table.column)
                parts = word.split('.')
                if len(parts) == 2:
                    table, column = parts
                    if table not in self.tables_cache:
                        self.tables_cache[table] = []
                    if column not in self.tables_cache[table]:
                        self.tables_cache[table].append(column)
            else:
                # Could be a table or a standalone column
                # We'll assume tables as being words that don't have special characters
                if not any(c in word for c in ',;()[]+-*/=<>%|&!?:'):
                    # Add as potential table
                    if word not in self.tables_cache:
                        self.tables_cache[word] = []
        
    def get_word_under_cursor(self):
        """Get the complete word under the cursor for completion, handling dot notation"""
        tc = self.textCursor()
        current_position = tc.position()
        
        # Get the current line of text
        tc.select(QTextCursor.SelectionType.LineUnderCursor)
        line_text = tc.selectedText()
        
        # Calculate cursor position within the line
        start_of_line_pos = current_position - tc.selectionStart()
        
        # Identify word boundaries including dots
        start_pos = start_of_line_pos
        while start_pos > 0 and (line_text[start_pos-1].isalnum() or line_text[start_pos-1] in '_$.'):
            start_pos -= 1
            
        end_pos = start_of_line_pos
        while end_pos < len(line_text) and (line_text[end_pos].isalnum() or line_text[end_pos] in '_$'):
            end_pos += 1
            
        if start_pos == end_pos:
            return ""
            
        word = line_text[start_pos:end_pos]
        return word
        
    def text_under_cursor(self):
        """Get the text under cursor for standard completion behavior"""
        # Get the complete word including table prefixes
        word = self.get_word_under_cursor()
        
        # For table.col completions, only return portion after the dot
        if '.' in word and word.endswith('.'):
            # For "table." return empty to trigger whole column list
            return ""
        elif '.' in word:
            # For "table.co", return "co" for completion
            return word.split('.')[-1]
        
        # Otherwise return the whole word
        return word
        
    def insert_completion(self, completion):
        """Insert the completion text with enhanced context awareness"""
        if self.completer.widget() != self:
            return
            
        tc = self.textCursor()
        
        # Handle table.column completion differently
        word = self.get_word_under_cursor()
        if '.' in word and not word.endswith('.'):
            # We're completing something like "table.co" to "table.column"
            # Replace only the part after the last dot
            prefix_parts = word.split('.')
            prefix = '.'.join(prefix_parts[:-1]) + '.'
            suffix = prefix_parts[-1]
            
            # Get positions for text manipulation
            cursor_pos = tc.position()
            tc.setPosition(cursor_pos - len(suffix))
            tc.setPosition(cursor_pos, QTextCursor.MoveMode.KeepAnchor)
            tc.removeSelectedText()
            tc.insertText(completion)
        else:
            # Standard completion behavior 
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
            special_endings = ["(", ")", ",", ";", ".", "*"]
            if any(completion.endswith(char) for char in special_endings):
                tc.insertText(completion)
            else:
                # Add space for normal words, but only if activated with Enter/Return
                # not when using Tab for completion
                from_keyboard = self.sender() is None
                add_space = from_keyboard or not self.last_key_was_tab
                tc.insertText(completion + (" " if add_space else ""))
        
        self.setTextCursor(tc)

    def get_context_at_cursor(self):
        """Analyze the query to determine the current SQL context for smarter completions"""
        # Get text up to cursor to analyze context
        tc = self.textCursor()
        position = tc.position()
        
        # Select all text from start to cursor
        doc = self.document()
        tc_context = QTextCursor(doc)
        tc_context.setPosition(0)
        tc_context.setPosition(position, QTextCursor.MoveMode.KeepAnchor)
        text_before_cursor = tc_context.selectedText().upper()
        
        # Get the current line
        tc.select(QTextCursor.SelectionType.LineUnderCursor)
        current_line = tc.selectedText().strip().upper()
        
        # Extract the last few keywords to determine context
        words = re.findall(r'\b[A-Z_]+\b', text_before_cursor)
        last_keywords = words[-3:] if words else []
        
        # Get the current word being typed (including table prefixes)
        current_word = self.get_word_under_cursor()
        
        # Check for specific contexts
        context = {
            'type': 'unknown',
            'table_prefix': None,
            'after_from': False,
            'after_join': False,
            'after_select': False,
            'after_where': False,
            'after_group_by': False,
            'after_order_by': False
        }
        
        # Check for table.column context
        if '.' in current_word:
            parts = current_word.split('.')
            if len(parts) == 2:
                context['type'] = 'column'
                context['table_prefix'] = parts[0]
                
        # FROM/JOIN context - likely to be followed by table names
        if any(kw in last_keywords for kw in ['FROM', 'JOIN']):
            context['type'] = 'table'
            context['after_from'] = 'FROM' in last_keywords
            context['after_join'] = any(k.endswith('JOIN') for k in last_keywords)
            
        # WHERE/AND/OR context - likely to be followed by columns or expressions
        elif any(kw in last_keywords for kw in ['WHERE', 'AND', 'OR']):
            context['type'] = 'column_or_expression'
            context['after_where'] = True
            
        # SELECT context - likely to be followed by columns
        elif 'SELECT' in last_keywords:
            context['type'] = 'column'
            context['after_select'] = True
            
        # GROUP BY context
        elif 'GROUP' in last_keywords or any('GROUP BY' in ' '.join(last_keywords[-2:]) for i in range(len(last_keywords)-1)):
            context['type'] = 'column'
            context['after_group_by'] = True
            
        # ORDER BY context
        elif 'ORDER' in last_keywords or any('ORDER BY' in ' '.join(last_keywords[-2:]) for i in range(len(last_keywords)-1)):
            context['type'] = 'column'
            context['after_order_by'] = True
            
        # Check for function context (inside parentheses)
        if '(' in text_before_cursor and text_before_cursor.count('(') > text_before_cursor.count(')'):
            context['type'] = 'function_arg'
            
        return context

    def get_context_aware_completions(self, prefix):
        """Get completions based on the current context in the query"""
        import time
        
        # Don't waste time on empty prefixes or if we don't have tables
        if not prefix and not self.tables_cache:
            return self.all_sql_keywords
            
        # Get context information
        context = self.get_context_at_cursor()
        
        # Default completions - all keywords and names
        all_completions = []
        
        # Add keywords appropriate for the current context
        if context['type'] == 'table' or prefix.upper() in [k.upper() for k in self.all_sql_keywords]:
            # After FROM/JOIN, prioritize table keywords
            all_completions.extend(self.sql_keywords['basic'])
            all_completions.extend(self.sql_keywords['table_ops'])
            
            # Also include table names
            all_completions.extend(self.tables_cache.keys())
            
        elif context['type'] == 'column' and context['table_prefix']:
            # For "table." completions, only show columns from that table
            table = context['table_prefix']
            if table in self.tables_cache:
                all_completions.extend(self.tables_cache[table])
                
        elif context['type'] == 'column' or context['type'] == 'column_or_expression':
            # Add column-related keywords
            all_completions.extend(self.sql_keywords['basic'])
            all_completions.extend(self.sql_keywords['aggregation'])
            all_completions.extend(self.sql_keywords['functions'])
            
            # Add all columns from all tables
            for table, columns in self.tables_cache.items():
                all_completions.extend(columns)
                # Also add qualified columns (table.column)
                all_completions.extend([f"{table}.{col}" for col in columns])
                
        elif context['type'] == 'function_arg':
            # Inside a function, suggest columns
            for columns in self.tables_cache.values():
                all_completions.extend(columns)
                
        else:
            # Default case - include everything
            all_completions.extend(self.all_sql_keywords)
            
            # Add all table and column names
            all_completions.extend(self.tables_cache.keys())
            for columns in self.tables_cache.values():
                all_completions.extend(columns)
        
        # If the prefix looks like the start of a SQL statement or clause
        if prefix and len(prefix) > 2 and prefix.isupper():
            # Check each category for matching keywords
            for category, keywords in self.sql_keywords.items():
                for keyword in keywords:
                    if keyword.startswith(prefix):
                        all_completions.append(keyword)
        
        # If the prefix looks like the start of a JOIN
        if prefix and "JOIN" in prefix.upper():
            all_completions.extend(self.sql_keywords['join'])
            
        # Filter duplicates while preserving order
        seen = set()
        filtered_completions = []
        for item in all_completions:
            if item not in seen:
                seen.add(item)
                filtered_completions.append(item)
        
        return filtered_completions

    def complete(self):
        """Show improved completion popup with context awareness"""
        import re
        
        # Get the text under cursor
        prefix = self.text_under_cursor()
        
        # Don't show popup for empty text or too short prefixes unless it's a table prefix
        is_table_prefix = '.' in self.get_word_under_cursor() and self.get_word_under_cursor().endswith('.')
        if not prefix and not is_table_prefix:
            if self.completer and self.completer.popup().isVisible():
                self.completer.popup().hide()
            return
        
        # Get context-aware completions 
        if self.tables_cache:
            # Use our custom context-aware completion
            completions = self.get_context_aware_completions(prefix)
            if completions:
                # Create a temporary model for the filtered completions
                model = QStringListModel()
                model.setStringList(completions)
                self.completer.setModel(model)
        
        # Set the completion prefix
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
            elif event.key() == Qt.Key.Key_Slash:
                # Also allow Ctrl+/ for commenting (common shortcut in other editors)
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

    def dragEnterEvent(self, event):
        """Handle drag enter events to allow dropping table names."""
        # Accept text/plain mime data (used for table names)
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event):
        """Handle drag move events to show valid drop locations."""
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """Handle drop event to insert table name at cursor position."""
        if event.mimeData().hasText():
            # Get table name from dropped text
            text = event.mimeData().text()
            
            # Extract actual table name (if it includes parentheses)
            if " (" in text:
                table_name = text.split(" (")[0]
            else:
                table_name = text
                
            # Get current cursor position and surrounding text
            cursor = self.textCursor()
            document = self.document()
            current_block = cursor.block()
            block_text = current_block.text()
            position_in_block = cursor.positionInBlock()
            
            # Get text before cursor in current line
            text_before = block_text[:position_in_block].strip().upper()
            
            # Determine how to insert the table name based on context
            if (text_before.endswith("FROM") or
                text_before.endswith("JOIN") or
                text_before.endswith("INTO") or
                text_before.endswith("UPDATE") or
                text_before.endswith(",")):
                # Just insert the table name with a space before it
                cursor.insertText(f" {table_name}")
            elif text_before.endswith("FROM ") or text_before.endswith("JOIN ") or text_before.endswith("INTO ") or text_before.endswith(", "):
                # Just insert the table name without a space
                cursor.insertText(table_name)
            elif not text_before and not block_text:
                # If at empty line, insert a SELECT statement
                cursor.insertText(f"SELECT * FROM {table_name}")
            else:
                # Default: just insert the table name at cursor position
                cursor.insertText(table_name)
            
            # Accept the action
            event.acceptProposedAction()
        else:
            event.ignore() 