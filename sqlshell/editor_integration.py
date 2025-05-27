"""
Integration module to add F5/F9 execution functionality to SQLEditor.
This module provides a clean way to enhance the editor without modifying the original code.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPlainTextEdit
from .execution_handler import SQLExecutionHandler, ExecutionKeyHandler


class EditorExecutionIntegration:
    """
    Integration class to add F5/F9 execution functionality to SQLEditor.
    """
    
    def __init__(self, editor: QPlainTextEdit, execute_callback=None):
        """
        Initialize the integration.
        
        Args:
            editor: The SQLEditor instance
            execute_callback: Function to call to execute queries
        """
        self.editor = editor
        self.execution_handler = SQLExecutionHandler(execute_callback)
        self.key_handler = ExecutionKeyHandler(self.execution_handler)
        
        # Store original keyPressEvent to preserve existing functionality
        self.original_key_press_event = editor.keyPressEvent
        
        # Replace keyPressEvent with our enhanced version
        editor.keyPressEvent = self.enhanced_key_press_event
        
    def set_execute_callback(self, callback):
        """Set the execution callback function."""
        self.execution_handler.set_execute_callback(callback)
        
    def enhanced_key_press_event(self, event):
        """Enhanced keyPressEvent that handles F5/F9 while preserving original functionality."""
        
        # First, try to handle F5/F9 keys
        if self.key_handler.handle_key_press(self.editor, event.key(), event.modifiers()):
            # Key was handled by our execution handler
            return
        
        # If not F5/F9, use the original keyPressEvent
        self.original_key_press_event(event)
    
    def execute_all_statements(self):
        """Execute all statements in the editor (F5 functionality)."""
        try:
            return self.execution_handler.execute_from_editor(self.editor, "all")
        except Exception as e:
            print(f"Error executing all statements: {e}")
            return None
    
    def execute_current_statement(self):
        """Execute the current statement (F9 functionality)."""
        try:
            return self.execution_handler.execute_from_editor(self.editor, "current")
        except Exception as e:
            print(f"Error executing current statement: {e}")
            return None
    
    def get_current_statement_info(self):
        """Get information about the current statement at cursor position."""
        text = self.editor.toPlainText()
        cursor = self.editor.textCursor()
        cursor_position = cursor.position()
        
        current_stmt = self.execution_handler.get_current_statement(text, cursor_position)
        if current_stmt:
            stmt_text, start_pos, end_pos = current_stmt
            return {
                'text': stmt_text,
                'start': start_pos,
                'end': end_pos,
                'cursor_position': cursor_position
            }
        return None
    
    def get_all_statements_info(self):
        """Get information about all statements in the editor."""
        text = self.editor.toPlainText()
        statements = self.execution_handler.parse_sql_statements(text)
        
        return [
            {
                'text': stmt_text,
                'start': start_pos,
                'end': end_pos,
                'index': i
            }
            for i, (stmt_text, start_pos, end_pos) in enumerate(statements)
        ]


def integrate_execution_functionality(editor: QPlainTextEdit, execute_callback=None):
    """
    Convenience function to integrate F5/F9 execution functionality into an editor.
    
    Args:
        editor: The SQLEditor instance
        execute_callback: Function to call to execute queries
        
    Returns:
        EditorExecutionIntegration instance for further customization
    """
    integration = EditorExecutionIntegration(editor, execute_callback)
    
    # Store the integration instance on the editor for later access
    editor._execution_integration = integration
    
    return integration


def get_execution_integration(editor: QPlainTextEdit):
    """
    Get the execution integration instance from an editor.
    
    Args:
        editor: The SQLEditor instance
        
    Returns:
        EditorExecutionIntegration instance or None if not integrated
    """
    return getattr(editor, '_execution_integration', None) 