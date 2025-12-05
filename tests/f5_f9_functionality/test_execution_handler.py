#!/usr/bin/env python3
"""
Test file for the SQL execution handler.
Tests F5 (execute all statements) and F9 (execute current statement) functionality.
"""

import sys
import os

# Add the project root to path so we can import our module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlshell.execution_handler import SQLExecutionHandler, ExecutionKeyHandler
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QPlainTextEdit, QLabel, 
                           QTextEdit, QSplitter)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class TestWindow(QMainWindow):
    """Test window for the execution handler functionality."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_execution_handler()
        
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("SQL Execution Handler Test")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Instructions
        instructions = QLabel("""
Test the SQL Execution Handler:
• F5: Execute all statements
• F9: Execute current statement (statement containing cursor)
• Or use the buttons below

Try multi-statement SQL with semicolons, comments, and string literals.
        """)
        instructions.setStyleSheet("background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc;")
        layout.addWidget(instructions)
        
        # Splitter for editor and output
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - SQL Editor
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        
        editor_layout.addWidget(QLabel("SQL Editor:"))
        
        self.sql_editor = QPlainTextEdit()
        self.sql_editor.setFont(QFont("Consolas", 11))
        self.sql_editor.setPlaceholderText("Enter your SQL statements here...")
        
        # Sample SQL for testing
        sample_sql = """-- Sample SQL statements for testing
SELECT 'First statement' as test;

/* Block comment */
SELECT 'Second statement' as test, 
       'with multiple lines' as description;

-- Test string with semicolon
SELECT 'This is a string with ; semicolon' as test;

SELECT 'Fourth statement' as test"""
        
        self.sql_editor.setPlainText(sample_sql)
        editor_layout.addWidget(self.sql_editor)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.f5_button = QPushButton("F5 - Execute All")
        self.f5_button.clicked.connect(self.execute_all)
        button_layout.addWidget(self.f5_button)
        
        self.f9_button = QPushButton("F9 - Execute Current")
        self.f9_button.clicked.connect(self.execute_current)
        button_layout.addWidget(self.f9_button)
        
        self.parse_button = QPushButton("Parse Statements")
        self.parse_button.clicked.connect(self.parse_statements)
        button_layout.addWidget(self.parse_button)
        
        self.clear_button = QPushButton("Clear Output")
        self.clear_button.clicked.connect(self.clear_output)
        button_layout.addWidget(self.clear_button)
        
        editor_layout.addLayout(button_layout)
        
        # Right side - Output
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        
        output_layout.addWidget(QLabel("Output:"))
        
        self.output_area = QTextEdit()
        self.output_area.setFont(QFont("Consolas", 10))
        self.output_area.setReadOnly(True)
        output_layout.addWidget(self.output_area)
        
        # Add widgets to splitter
        splitter.addWidget(editor_widget)
        splitter.addWidget(output_widget)
        splitter.setSizes([500, 500])
        
        # Install event filter for key handling
        self.sql_editor.installEventFilter(self)
        
    def setup_execution_handler(self):
        """Set up the execution handler."""
        self.execution_handler = SQLExecutionHandler(self.mock_execute_query)
        self.key_handler = ExecutionKeyHandler(self.execution_handler)
        
    def mock_execute_query(self, query: str):
        """Mock query execution function."""
        self.output_area.append(f"EXECUTING: {query}")
        self.output_area.append("✓ Query executed successfully\n")
        
    def execute_all(self):
        """Execute all statements (F5)."""
        try:
            text = self.sql_editor.toPlainText()
            executed = self.execution_handler.execute_all_statements(text)
            self.output_area.append(f"=== F5 - EXECUTE ALL ===")
            self.output_area.append(f"Executed {len(executed)} statement(s)\n")
        except Exception as e:
            self.output_area.append(f"ERROR: {e}\n")
            
    def execute_current(self):
        """Execute current statement (F9)."""
        try:
            text = self.sql_editor.toPlainText()
            cursor = self.sql_editor.textCursor()
            cursor_position = cursor.position()
            
            executed = self.execution_handler.execute_current_statement(text, cursor_position)
            self.output_area.append(f"=== F9 - EXECUTE CURRENT ===")
            if executed:
                self.output_area.append(f"Cursor position: {cursor_position}")
                self.output_area.append(f"Executed statement: {executed[:50]}{'...' if len(executed) > 50 else ''}\n")
            else:
                self.output_area.append(f"No statement found at cursor position {cursor_position}\n")
        except Exception as e:
            self.output_area.append(f"ERROR: {e}\n")
            
    def parse_statements(self):
        """Parse and display all statements."""
        try:
            text = self.sql_editor.toPlainText()
            statements = self.execution_handler.parse_sql_statements(text)
            
            self.output_area.append(f"=== PARSE STATEMENTS ===")
            self.output_area.append(f"Found {len(statements)} statement(s):")
            
            for i, (stmt, start, end) in enumerate(statements, 1):
                self.output_area.append(f"{i}. Position {start}-{end}: {stmt[:50]}{'...' if len(stmt) > 50 else ''}")
            
            self.output_area.append("")
            
        except Exception as e:
            self.output_area.append(f"ERROR: {e}\n")
            
    def clear_output(self):
        """Clear the output area."""
        self.output_area.clear()
        
    def eventFilter(self, obj, event):
        """Handle key events."""
        from PyQt6.QtCore import QEvent
        
        if obj == self.sql_editor and event.type() == QEvent.Type.KeyPress:
            # Handle F5 and F9 keys
            if self.key_handler.handle_key_press(self.sql_editor, event.key(), event.modifiers()):
                return True
                
        return super().eventFilter(obj, event)


def run_basic_tests():
    """Run basic tests without UI."""
    print("Running basic tests...")
    
    # Test 1: Simple statements
    print("\n1. Testing simple statements:")
    handler = SQLExecutionHandler()
    
    sql = "SELECT 1; SELECT 2; SELECT 3"
    statements = handler.parse_sql_statements(sql)
    print(f"Input: {sql}")
    print(f"Parsed {len(statements)} statements:")
    for i, (stmt, start, end) in enumerate(statements, 1):
        print(f"  {i}. {stmt} (pos {start}-{end})")
    
    # Test 2: Comments and strings
    print("\n2. Testing comments and strings:")
    sql = """-- Comment
SELECT 'string with ; semicolon';
/* Block comment */
SELECT 'another' as test"""
    
    statements = handler.parse_sql_statements(sql)
    print(f"Parsed {len(statements)} statements:")
    for i, (stmt, start, end) in enumerate(statements, 1):
        print(f"  {i}. {stmt} (pos {start}-{end})")
    
    # Test 3: Current statement detection
    print("\n3. Testing current statement detection:")
    sql = "SELECT 1; SELECT 2; SELECT 3"
    # Cursor at position 10 (in second statement)
    current = handler.get_current_statement(sql, 10)
    if current:
        stmt, start, end = current
        print(f"Statement at position 10: '{stmt}' (pos {start}-{end})")
    else:
        print("No statement found at position 10")
    
    print("\nBasic tests completed!")


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_basic_tests()
        return
    
    app = QApplication(sys.argv)
    
    # Run basic tests first
    run_basic_tests()
    
    # Show the test window
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 