"""
Modular SQL execution handler for SQLShell.
Provides F5 (execute all statements) and F9 (execute current statement) functionality.
"""

import re
from typing import List, Tuple, Optional, Callable
from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtGui import QTextCursor


class SQLExecutionHandler:
    """
    Handles SQL statement parsing and execution for different execution modes.
    
    Supports:
    - F5: Execute all statements in the editor
    - F9: Execute the current statement (statement containing cursor)
    """
    
    def __init__(self, execute_callback: Callable[[str], None] = None):
        """
        Initialize the execution handler.
        
        Args:
            execute_callback: Function to call to execute a SQL query string
        """
        self.execute_callback = execute_callback
        
    def set_execute_callback(self, callback: Callable[[str], None]):
        """Set the callback function for executing queries."""
        self.execute_callback = callback
    
    def parse_sql_statements(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Parse SQL text into individual statements.
        
        Args:
            text: SQL text to parse
            
        Returns:
            List of tuples: (statement_text, start_position, end_position)
        """
        statements = []
        if not text.strip():
            return statements
        
        # Create position mapping between original text and comment-removed text
        original_to_clean, clean_to_original = self._create_position_mapping(text)
        
        # Remove comments while preserving position information
        text_without_comments = self._remove_comments(text)
        
        # Split by semicolons, but be smart about it
        # Handle string literals and quoted identifiers properly
        current_statement = ""
        statement_start_pos = 0
        i = 0
        in_string = False
        string_char = None
        escaped = False
        
        # Find the first non-whitespace character to start
        while statement_start_pos < len(text_without_comments) and text_without_comments[statement_start_pos].isspace():
            statement_start_pos += 1
        
        while i < len(text_without_comments):
            char = text_without_comments[i]
            
            if escaped:
                escaped = False
                current_statement += char
                i += 1
                continue
            
            if char == '\\':
                escaped = True
                current_statement += char
                i += 1
                continue
            
            if not in_string and char in ('"', "'"):
                in_string = True
                string_char = char
                current_statement += char
            elif in_string and char == string_char:
                # Check for escaped quotes (double quotes)
                if i + 1 < len(text_without_comments) and text_without_comments[i + 1] == string_char:
                    current_statement += char + string_char
                    i += 2
                    continue
                else:
                    in_string = False
                    string_char = None
                    current_statement += char
            elif not in_string and char == ';':
                # End of statement
                statement_text = current_statement.strip()
                if statement_text:
                    # Convert clean text positions back to original text positions
                    original_start = clean_to_original.get(statement_start_pos, statement_start_pos)
                    original_end = clean_to_original.get(i + 1, len(text))
                    statements.append((statement_text, original_start, original_end))
                
                # Find next non-whitespace character for next statement start
                j = i + 1
                while j < len(text_without_comments) and text_without_comments[j].isspace():
                    j += 1
                statement_start_pos = j
                current_statement = ""
            else:
                current_statement += char
            
            i += 1
        
        # Handle the last statement if it doesn't end with semicolon
        statement_text = current_statement.strip()
        if statement_text:
            original_start = clean_to_original.get(statement_start_pos, statement_start_pos)
            original_end = len(text)
            statements.append((statement_text, original_start, original_end))
        
        return statements
    
    def _create_position_mapping(self, text: str) -> tuple[dict, dict]:
        """
        Create bidirectional position mapping between original text and comment-removed text.
        
        Args:
            text: Original SQL text
            
        Returns:
            Tuple of (original_to_clean, clean_to_original) position mappings
        """
        original_to_clean = {}
        clean_to_original = {}
        clean_pos = 0
        i = 0
        in_string = False
        string_char = None
        
        while i < len(text):
            char = text[i]
            
            if not in_string:
                # Check for string start
                if char in ('"', "'"):
                    in_string = True
                    string_char = char
                    original_to_clean[i] = clean_pos
                    clean_to_original[clean_pos] = i
                    clean_pos += 1
                # Check for line comment
                elif char == '-' and i + 1 < len(text) and text[i + 1] == '-':
                    # Skip to end of line, but preserve newline
                    while i < len(text) and text[i] != '\n':
                        original_to_clean[i] = clean_pos
                        i += 1
                    if i < len(text):  # Add the newline
                        original_to_clean[i] = clean_pos
                        clean_to_original[clean_pos] = i
                        clean_pos += 1
                    continue
                # Check for block comment
                elif char == '/' and i + 1 < len(text) and text[i + 1] == '*':
                    # Skip to end of block comment
                    start_i = i
                    i += 2
                    while i + 1 < len(text):
                        original_to_clean[i] = clean_pos
                        if text[i] == '*' and text[i + 1] == '/':
                            original_to_clean[i + 1] = clean_pos
                            i += 2
                            break
                        i += 1
                    continue
                else:
                    original_to_clean[i] = clean_pos
                    clean_to_original[clean_pos] = i
                    clean_pos += 1
            else:
                # In string
                if char == string_char:
                    # Check for escaped quote
                    if i + 1 < len(text) and text[i + 1] == string_char:
                        original_to_clean[i] = clean_pos
                        original_to_clean[i + 1] = clean_pos + 1
                        clean_to_original[clean_pos] = i
                        clean_to_original[clean_pos + 1] = i + 1
                        clean_pos += 2
                        i += 2
                        continue
                    else:
                        in_string = False
                        string_char = None
                        original_to_clean[i] = clean_pos
                        clean_to_original[clean_pos] = i
                        clean_pos += 1
                else:
                    original_to_clean[i] = clean_pos
                    clean_to_original[clean_pos] = i
                    clean_pos += 1
            
            i += 1
        
        return original_to_clean, clean_to_original
    
    def _remove_comments(self, text: str) -> str:
        """
        Remove SQL comments while preserving string literals.
        
        Args:
            text: SQL text
            
        Returns:
            Text with comments removed
        """
        result = []
        i = 0
        in_string = False
        string_char = None
        
        while i < len(text):
            char = text[i]
            
            if not in_string:
                # Check for string start
                if char in ('"', "'"):
                    in_string = True
                    string_char = char
                    result.append(char)
                # Check for line comment
                elif char == '-' and i + 1 < len(text) and text[i + 1] == '-':
                    # Skip to end of line
                    while i < len(text) and text[i] != '\n':
                        i += 1
                    if i < len(text):
                        result.append('\n')  # Preserve newline
                    continue
                # Check for block comment
                elif char == '/' and i + 1 < len(text) and text[i + 1] == '*':
                    # Skip to end of block comment
                    i += 2
                    while i + 1 < len(text):
                        if text[i] == '*' and text[i + 1] == '/':
                            i += 2
                            break
                        i += 1
                    continue
                else:
                    result.append(char)
            else:
                # In string
                if char == string_char:
                    # Check for escaped quote
                    if i + 1 < len(text) and text[i + 1] == string_char:
                        result.append(char + string_char)
                        i += 2
                        continue
                    else:
                        in_string = False
                        string_char = None
                        result.append(char)
                else:
                    result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    def get_current_statement(self, text: str, cursor_position: int) -> Optional[Tuple[str, int, int]]:
        """
        Get the statement that contains the cursor position.
        If cursor is not inside any statement, returns the closest statement before the cursor.
        
        Args:
            text: SQL text
            cursor_position: Current cursor position
            
        Returns:
            Tuple of (statement_text, start_position, end_position) or None
        """
        statements = self.parse_sql_statements(text)
        
        # First try to find a statement containing the cursor
        for statement_text, start_pos, end_pos in statements:
            if start_pos <= cursor_position <= end_pos:
                return (statement_text, start_pos, end_pos)
        
        # If no statement contains the cursor, find the closest statement before the cursor
        closest_statement = None
        closest_distance = float('inf')
        
        for statement_text, start_pos, end_pos in statements:
            if end_pos <= cursor_position:  # Statement is before cursor
                distance = cursor_position - end_pos
                if distance < closest_distance:
                    closest_distance = distance
                    closest_statement = (statement_text, start_pos, end_pos)
        
        return closest_statement
    
    def execute_all_statements(self, text: str) -> List[str]:
        """
        Execute all statements in the text (F5 functionality).
        
        Args:
            text: SQL text containing one or more statements
            
        Returns:
            List of executed statement texts
        """
        if not self.execute_callback:
            raise ValueError("No execute callback set")
        
        statements = self.parse_sql_statements(text)
        executed_statements = []
        
        for statement_text, _, _ in statements:
            if statement_text.strip():
                self.execute_callback(statement_text)
                executed_statements.append(statement_text)
        
        return executed_statements
    
    def execute_current_statement(self, text: str, cursor_position: int) -> Optional[str]:
        """
        Execute the statement containing the cursor (F9 functionality).
        
        Args:
            text: SQL text
            cursor_position: Current cursor position
            
        Returns:
            Executed statement text or None if no statement found
        """
        if not self.execute_callback:
            raise ValueError("No execute callback set")
        
        current_statement = self.get_current_statement(text, cursor_position)
        
        if current_statement:
            statement_text, _, _ = current_statement
            if statement_text.strip():
                self.execute_callback(statement_text)
                return statement_text
        
        return None
    
    def execute_from_editor(self, editor: QPlainTextEdit, mode: str = "current") -> Optional[str]:
        """
        Execute statements from a QPlainTextEdit widget.
        
        Args:
            editor: The text editor widget
            mode: "current" for F9 or "all" for F5
            
        Returns:
            Executed statement(s) or None
        """
        text = editor.toPlainText()
        cursor = editor.textCursor()
        cursor_position = cursor.position()
        
        if mode == "all":
            executed = self.execute_all_statements(text)
            return "; ".join(executed) if executed else None
        elif mode == "current":
            return self.execute_current_statement(text, cursor_position)
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'current' or 'all'")


class ExecutionKeyHandler:
    """
    Key handler for F5 and F9 execution functionality.
    Integrates with QPlainTextEdit widgets.
    """
    
    def __init__(self, execution_handler: SQLExecutionHandler):
        """
        Initialize the key handler.
        
        Args:
            execution_handler: The execution handler to use
        """
        self.execution_handler = execution_handler
    
    def handle_key_press(self, editor: QPlainTextEdit, key: int, modifiers: int) -> bool:
        """
        Handle key press events for execution shortcuts.
        
        Args:
            editor: The text editor widget
            key: Key code
            modifiers: Keyboard modifiers
            
        Returns:
            True if the key was handled, False otherwise
        """
        from PyQt6.QtCore import Qt
        
        # F5 - Execute all statements
        if key == Qt.Key.Key_F5:
            try:
                executed = self.execution_handler.execute_from_editor(editor, "all")
                return True
            except Exception as e:
                print(f"Error executing all statements: {e}")
                return True
        
        # F9 - Execute current statement
        elif key == Qt.Key.Key_F9:
            try:
                executed = self.execution_handler.execute_from_editor(editor, "current")
                return True
            except Exception as e:
                print(f"Error executing current statement: {e}")
                return True
        
        return False 