"""
Tests for SQL execution handler (query parsing and execution).

This module tests the SQLExecutionHandler class which provides
F5 (execute all) and F9 (execute current) functionality.
"""

import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlshell.execution_handler import SQLExecutionHandler


@pytest.fixture
def handler():
    """Create a SQLExecutionHandler instance."""
    return SQLExecutionHandler()


@pytest.fixture
def handler_with_callback():
    """Create a SQLExecutionHandler with a tracking callback."""
    executed = []
    
    def callback(query):
        executed.append(query)
    
    handler = SQLExecutionHandler(execute_callback=callback)
    handler._executed = executed  # Attach for test access
    return handler


class TestStatementParsing:
    """Tests for SQL statement parsing."""

    def test_parse_single_statement(self, handler):
        """Test parsing a single SQL statement."""
        text = "SELECT * FROM users;"
        statements = handler.parse_sql_statements(text)
        
        assert len(statements) == 1
        assert "SELECT * FROM users" in statements[0][0]

    def test_parse_multiple_statements(self, handler):
        """Test parsing multiple SQL statements."""
        text = """SELECT * FROM users;
SELECT * FROM orders;
SELECT * FROM products;"""
        statements = handler.parse_sql_statements(text)
        
        assert len(statements) == 3

    def test_parse_statement_without_semicolon(self, handler):
        """Test parsing a statement without trailing semicolon."""
        text = "SELECT * FROM users"
        statements = handler.parse_sql_statements(text)
        
        assert len(statements) == 1

    def test_parse_with_string_containing_semicolon(self, handler):
        """Test that semicolons inside strings are not treated as delimiters."""
        text = "SELECT * FROM users WHERE name = 'John; Doe';"
        statements = handler.parse_sql_statements(text)
        
        assert len(statements) == 1
        assert "John; Doe" in statements[0][0]

    def test_parse_with_line_comments(self, handler):
        """Test parsing with single-line comments."""
        text = """-- This is a comment
SELECT * FROM users;
-- Another comment
SELECT * FROM orders;"""
        statements = handler.parse_sql_statements(text)
        
        assert len(statements) == 2

    def test_parse_with_block_comments(self, handler):
        """Test parsing with block comments."""
        text = """/* Block comment */
SELECT * FROM users;
/* Multi-line
   comment */
SELECT * FROM orders;"""
        statements = handler.parse_sql_statements(text)
        
        assert len(statements) == 2

    def test_parse_empty_text(self, handler):
        """Test parsing empty text."""
        statements = handler.parse_sql_statements("")
        assert len(statements) == 0
        
        statements = handler.parse_sql_statements("   ")
        assert len(statements) == 0

    def test_parse_only_comments(self, handler):
        """Test parsing text with only comments."""
        text = """-- Just a comment
/* Another comment */"""
        statements = handler.parse_sql_statements(text)
        
        # Should return empty or just the comments depending on implementation
        # The key is it shouldn't error
        assert statements is not None


class TestCurrentStatementDetection:
    """Tests for detecting the current statement at cursor position."""

    def test_get_current_statement_single(self, handler):
        """Test getting current statement with single statement."""
        text = "SELECT * FROM users;"
        result = handler.get_current_statement(text, 10)
        
        assert result is not None
        stmt, start, end = result
        assert "SELECT" in stmt

    def test_get_current_statement_multiple(self, handler):
        """Test getting current statement from multiple statements."""
        text = "SELECT 1; SELECT 2; SELECT 3;"
        
        # Cursor at position in second statement (after first semicolon)
        result = handler.get_current_statement(text, 12)
        
        assert result is not None
        stmt, start, end = result
        assert "2" in stmt

    def test_get_current_statement_at_end(self, handler):
        """Test getting statement when cursor is at the end."""
        text = "SELECT * FROM users;"
        result = handler.get_current_statement(text, len(text))
        
        assert result is not None


class TestStatementExecution:
    """Tests for statement execution."""

    def test_execute_all_statements(self, handler_with_callback):
        """Test executing all statements."""
        text = """SELECT 1;
SELECT 2;
SELECT 3;"""
        
        result = handler_with_callback.execute_all_statements(text)
        
        assert len(result) == 3
        assert len(handler_with_callback._executed) == 3

    def test_execute_current_statement(self, handler_with_callback):
        """Test executing current statement."""
        text = "SELECT 1; SELECT 2; SELECT 3;"
        
        # Execute statement at position 12 (second statement)
        result = handler_with_callback.execute_current_statement(text, 12)
        
        assert result is not None
        assert len(handler_with_callback._executed) == 1

    def test_execute_without_callback(self, handler):
        """Test execution without callback raises appropriate error."""
        text = "SELECT * FROM users;"
        
        # Handler requires a callback to execute - should raise ValueError
        with pytest.raises(ValueError, match="No execute callback set"):
            handler.execute_all_statements(text)


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_nested_quotes(self, handler):
        """Test handling nested quotes."""
        text = """SELECT "column with 'quotes'" FROM users;"""
        statements = handler.parse_sql_statements(text)
        
        assert len(statements) == 1

    def test_escaped_quotes(self, handler):
        """Test handling escaped quotes."""
        text = """SELECT * FROM users WHERE name = 'O''Brien';"""
        statements = handler.parse_sql_statements(text)
        
        assert len(statements) == 1
        assert "O''Brien" in statements[0][0]

    def test_multiline_statement(self, handler):
        """Test parsing multiline statement."""
        text = """SELECT 
    column1,
    column2,
    column3
FROM 
    users
WHERE 
    active = 1;"""
        statements = handler.parse_sql_statements(text)
        
        assert len(statements) == 1

    def test_statement_positions(self, handler):
        """Test that statement positions are correctly reported."""
        text = "SELECT 1; SELECT 2;"
        statements = handler.parse_sql_statements(text)
        
        assert len(statements) == 2
        
        # Each statement should have (text, start_pos, end_pos)
        for stmt, start, end in statements:
            assert isinstance(start, int)
            assert isinstance(end, int)
            assert start >= 0
            assert end > start
