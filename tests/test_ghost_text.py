"""
Tests for ghost text autocomplete functionality in SQLEditor.

These tests cover the edge cases and fixes for:
1. Tab key accepting ghost text only at correct positions
2. Ghost text position tracking
3. Preventing accidental acceptance when indenting on new lines
4. Partial word completion and validation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

# Ensure QApplication exists for widget tests
@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def editor(qapp):
    """Create a fresh SQLEditor instance for testing."""
    from sqlshell.editor import SQLEditor
    editor = SQLEditor()
    return editor


class TestGhostTextDisplay:
    """Tests for ghost text display functionality."""
    
    def test_initial_state(self, editor):
        """Test initial ghost text state."""
        assert editor.ghost_text == ""
        assert editor.ghost_text_position == -1
        assert editor.ghost_text_suggestion == ""
        assert editor.ghost_text_partial_word == ""
    
    def test_show_ghost_text_with_matching_prefix(self, editor):
        """Test showing ghost text when suggestion matches current word."""
        # Set up editor with partial word
        editor.setPlainText("SELECT * FROM users WHERE name = 'mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        
        # Show ghost text suggestion
        editor.show_ghost_text("macchiato", position)
        
        # Should store the full suggestion
        assert editor.ghost_text_suggestion == "macchiato"
        assert editor.ghost_text_position == position
        
        # Should show only the remaining part (since 'mac' is already typed)
        assert editor.ghost_text == "chiato"
        assert editor.ghost_text_partial_word == "mac"
    
    def test_show_ghost_text_without_matching_prefix(self, editor):
        """Test showing ghost text when suggestion doesn't match current word."""
        editor.setPlainText("SELECT ")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        
        # Show ghost text that doesn't match current context
        editor.show_ghost_text("FROM users", position)
        
        # Should show the full suggestion
        assert editor.ghost_text_suggestion == "FROM users"
        assert editor.ghost_text == "FROM users"
        assert editor.ghost_text_position == position
    
    def test_clear_ghost_text(self, editor):
        """Test clearing ghost text."""
        # Set up ghost text
        editor.ghost_text = "test"
        editor.ghost_text_suggestion = "testing"
        editor.ghost_text_position = 10
        editor.ghost_text_partial_word = "test"
        
        # Clear it
        editor.clear_ghost_text()
        
        # All fields should be reset
        assert editor.ghost_text == ""
        assert editor.ghost_text_suggestion == ""
        assert editor.ghost_text_position == -1
        assert editor.ghost_text_partial_word == ""


class TestGhostTextAcceptance:
    """Tests for ghost text acceptance logic."""
    
    def test_accept_ghost_text_basic(self, editor):
        """Test basic ghost text acceptance."""
        # Set up text with partial word
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        
        # Show ghost text
        editor.show_ghost_text("macchiato", position)
        
        # Accept it
        result = editor.accept_ghost_text()
        
        assert result is True
        assert "macchiato" in editor.toPlainText()
        # Ghost text should be cleared
        assert editor.ghost_text == ""
        assert editor.ghost_text_suggestion == ""
    
    def test_accept_ghost_text_completion_suffix(self, editor):
        """Test accepting ghost text that is just a completion suffix (not full word)."""
        # Set up text with partial word
        editor.setPlainText("SELECT Macchiat")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        
        # AI returns just "o" as the completion suffix
        editor.show_ghost_text("o", position)
        
        # Accept it
        result = editor.accept_ghost_text()
        
        assert result is True
        assert "Macchiato" in editor.toPlainText()
        assert editor.toPlainText() == "SELECT Macchiato"
        # Ghost text should be cleared
        assert editor.ghost_text == ""
        assert editor.ghost_text_suggestion == ""
    
    def test_accept_ghost_text_with_continued_typing(self, editor):
        """Test accepting ghost text after user continues typing."""
        # Set up text
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        original_position = cursor.position()
        
        # Show ghost text for "mac"
        editor.show_ghost_text("macchiato", original_position)
        
        # User continues typing 'c' and 'h'
        editor.insertPlainText("ch")
        
        # Position has moved, but still within tolerance
        # Accept should still work
        result = editor.accept_ghost_text()
        
        assert result is True
        assert "macchiato" in editor.toPlainText()
    
    def test_reject_ghost_text_wrong_prefix(self, editor):
        """Test rejecting ghost text when user types non-matching characters."""
        # Set up text
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        
        # Show ghost text for "mac" with full word replacement
        editor.show_ghost_text("macchiato", position)
        
        # User backspaces and types something that doesn't match
        editor.insertPlainText("\b\b\bxyz")  # Replace "mac" with "xyz"
        
        # Accept should fail because "macchiato" doesn't start with "xyz"
        result = editor.accept_ghost_text()
        
        assert result is False
        # Ghost text should be cleared
        assert editor.ghost_text_suggestion == ""
    
    def test_reject_ghost_text_position_moved_too_far(self, editor):
        """Test rejecting ghost text when cursor moves too far."""
        # Set up text
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        
        # Show ghost text
        editor.show_ghost_text("macchiato", position)
        
        # Move cursor to beginning (simulates pressing Home or clicking elsewhere)
        cursor.movePosition(cursor.MoveOperation.Start)
        editor.setTextCursor(cursor)
        
        # Accept should fail
        result = editor.accept_ghost_text()
        
        assert result is False
        assert editor.ghost_text_suggestion == ""
    
    def test_accept_ghost_text_no_suggestion(self, editor):
        """Test accepting ghost text when there's no suggestion."""
        result = editor.accept_ghost_text()
        assert result is False


class TestTabKeyBehavior:
    """Tests for Tab key handling with ghost text."""
    
    def test_tab_accepts_ghost_text_at_correct_position(self, editor):
        """Test that Tab accepts ghost text when cursor is at the right position."""
        # Set up text
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        
        # Show ghost text
        editor.show_ghost_text("macchiato", position)
        
        # Create Tab key event
        tab_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Tab,
            Qt.KeyboardModifier.NoModifier
        )
        
        # Press Tab
        editor.keyPressEvent(tab_event)
        
        # Should accept the ghost text
        assert "macchiato" in editor.toPlainText()
    
    def test_tab_indents_when_no_ghost_text(self, editor):
        """Test that Tab inserts spaces when there's no ghost text."""
        editor.setPlainText("SELECT")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        # Create Tab key event
        tab_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Tab,
            Qt.KeyboardModifier.NoModifier
        )
        
        # Press Tab
        editor.keyPressEvent(tab_event)
        
        # Should insert 4 spaces
        assert editor.toPlainText() == "SELECT    "
    
    def test_tab_indents_on_new_line_not_accepting_old_ghost_text(self, editor):
        """Test that Tab indents on new line instead of accepting stale ghost text.
        
        This is the key bug fix: when user presses Enter to go to a new line,
        Tab should indent, not accept ghost text from previous line.
        """
        # Set up text with ghost text
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        
        # Show ghost text
        editor.show_ghost_text("macchiato", position)
        
        # User presses Enter to go to new line
        enter_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(enter_event)
        
        # Ghost text should be cleared when pressing Enter
        assert editor.ghost_text == ""
        
        # Now cursor is on new line, far from ghost_text_position
        current_pos = editor.textCursor().position()
        position_diff = current_pos - position
        
        # Press Tab to indent
        tab_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Tab,
            Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(tab_event)
        
        # Should insert spaces for indentation, not accept ghost text
        text = editor.toPlainText()
        lines = text.split('\n')
        assert len(lines) >= 2
        # Second line should start with spaces
        assert lines[1].startswith("    ")
        # Should NOT have inserted "macchiato" on second line
        assert "macchiato" not in lines[1]
    
    def test_tab_accepts_ghost_text_with_continued_typing(self, editor):
        """Test that Tab accepts ghost text even after user continues typing.
        
        This ensures the position tolerance works correctly.
        """
        # Set up text
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        original_position = cursor.position()
        
        # Show ghost text
        editor.show_ghost_text("macchiato", original_position)
        
        # User continues typing 'c'
        editor.insertPlainText("c")
        
        # Position has moved by 1, but should still be within tolerance
        current_pos = editor.textCursor().position()
        assert current_pos == original_position + 1
        assert (current_pos - editor.ghost_text_position) <= 20  # Within tolerance
        
        # Press Tab
        tab_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Tab,
            Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(tab_event)
        
        # Should accept the ghost text
        assert "macchiato" in editor.toPlainText()


class TestGhostTextWithQuotes:
    """Tests for ghost text with quoted strings (the original bug scenario)."""
    
    def test_quoted_string_completion(self, editor):
        """Test completing a quoted string without breaking the quotes."""
        # Set up SQL with quoted string
        editor.setPlainText("WHERE song = 'Caffe Mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        
        # Show ghost text for completing "Mac" to "Macchiato"
        editor.show_ghost_text("Macchiato", position)
        
        # Accept the ghost text
        result = editor.accept_ghost_text()
        
        assert result is True
        
        # Should have replaced "Mac" with "Macchiato"
        text = editor.toPlainText()
        assert "Macchiato" in text
        assert "'Caffe Macchiato" in text or "Caffe Macchiato" in text
    
    def test_partial_word_in_quotes_with_position_change(self, editor):
        """Test that position tracking prevents wrong replacements in quotes."""
        # Original problematic scenario from the bug report
        editor.setPlainText("WHERE song = 'Caffe Machi")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        original_position = cursor.position()
        
        # AI suggestion comes in for the current position
        editor.show_ghost_text("Macchiato", original_position)
        
        # But cursor has moved far away (user edited elsewhere - e.g., beginning of line)
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, 5)
        editor.setTextCursor(cursor)
        
        new_position = cursor.position()
        position_diff = new_position - original_position
        
        # Verify cursor moved backwards significantly (beyond tolerance)
        assert position_diff < 0  # Moved backwards
        
        # Try to accept ghost text
        result = editor.accept_ghost_text()
        
        # Should be rejected due to position mismatch (moved backwards)
        assert result is False
        
        # Original text should be unchanged
        assert editor.toPlainText() == "WHERE song = 'Caffe Machi"


class TestGhostTextClearingBehavior:
    """Tests for when ghost text should be automatically cleared."""
    
    def test_clear_on_navigation_keys(self, editor):
        """Test that ghost text clears on arrow keys and navigation."""
        # Set up ghost text
        editor.setPlainText("SELECT")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        editor.show_ghost_text("SELECT * FROM users", cursor.position())
        assert editor.ghost_text != ""
        
        # Press Left arrow
        left_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Left,
            Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(left_event)
        
        # Ghost text should be cleared
        assert editor.ghost_text == ""
    
    def test_clear_on_escape(self, editor):
        """Test that Escape key clears ghost text."""
        # Set up ghost text
        editor.setPlainText("SELECT")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        editor.show_ghost_text("SELECT * FROM users", cursor.position())
        assert editor.ghost_text != ""
        
        # Press Escape
        esc_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(esc_event)
        
        # Ghost text should be cleared
        assert editor.ghost_text == ""
    
    def test_clear_on_enter(self, editor):
        """Test that Enter key clears ghost text."""
        # Set up ghost text
        editor.setPlainText("SELECT")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        editor.show_ghost_text("SELECT * FROM users", cursor.position())
        assert editor.ghost_text != ""
        
        # Press Enter
        enter_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.NoModifier
        )
        editor.keyPressEvent(enter_event)
        
        # Ghost text should be cleared
        assert editor.ghost_text == ""
    
    def test_clear_on_space(self, editor):
        """Test that space clears ghost text."""
        # Set up ghost text
        editor.setPlainText("SELECT")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        editor.show_ghost_text("SELECT * FROM users", cursor.position())
        assert editor.ghost_text != ""
        
        # Press Space
        space_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Space,
            Qt.KeyboardModifier.NoModifier,
            " "
        )
        editor.keyPressEvent(space_event)
        
        # Ghost text should be cleared
        assert editor.ghost_text == ""


class TestGhostTextPositionTracking:
    """Tests for position tracking accuracy."""
    
    def test_position_stored_correctly(self, editor):
        """Test that ghost text position is stored correctly."""
        editor.setPlainText("SELECT")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        assert position == 6
        
        editor.show_ghost_text("SELECT * FROM users", position)
        
        assert editor.ghost_text_position == position
        assert editor.ghost_text_position == 6
    
    def test_partial_word_stored_correctly(self, editor):
        """Test that partial word is tracked correctly."""
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        editor.show_ghost_text("macchiato", cursor.position())
        
        assert editor.ghost_text_partial_word == "mac"
    
    def test_position_tolerance_calculation(self, editor):
        """Test the position difference calculation in accept_ghost_text."""
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        original_position = cursor.position()
        
        editor.show_ghost_text("macchiato", original_position)
        
        # Type a few more characters (within tolerance)
        for char in "chi":
            editor.insertPlainText(char)
        
        current_position = editor.textCursor().position()
        chars_typed = current_position - editor.ghost_text_position
        
        # Should be 3 characters typed
        assert chars_typed == 3
        
        # Should still be within tolerance (< 10 + len(partial_word))
        max_allowed = len(editor.ghost_text_partial_word) + 10
        assert chars_typed <= max_allowed
        
        # Accept should work
        result = editor.accept_ghost_text()
        assert result is True


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_empty_editor(self, editor):
        """Test ghost text with empty editor."""
        editor.show_ghost_text("SELECT", 0)
        
        assert editor.ghost_text == "SELECT"
        assert editor.ghost_text_position == 0
    
    def test_ghost_text_at_end_of_long_query(self, editor):
        """Test ghost text at the end of a long query."""
        long_query = "SELECT * FROM users u JOIN orders o ON u.id = o.user_id WHERE u.status = 'active' AND o.total > 100 ORDER BY o.created_at DESC LIMIT "
        editor.setPlainText(long_query)
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        editor.show_ghost_text("10", position)
        
        assert editor.ghost_text == "10"
        assert editor.ghost_text_position == position
    
    def test_multiple_ghost_text_updates(self, editor):
        """Test updating ghost text multiple times."""
        editor.setPlainText("SE")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        # First suggestion
        editor.show_ghost_text("SELECT", cursor.position())
        assert editor.ghost_text == "LECT"
        
        # Type more
        editor.insertPlainText("L")
        cursor = editor.textCursor()
        
        # New suggestion
        editor.show_ghost_text("SELECT", cursor.position())
        assert editor.ghost_text == "ECT"
    
    def test_accept_ghost_text_with_empty_current_word(self, editor):
        """Test accepting ghost text when current word is empty."""
        editor.setPlainText("SELECT ")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        editor.show_ghost_text("FROM", position)
        
        # Current word should be empty
        current_word = editor.get_word_under_cursor()
        assert current_word == ""
        
        # Accept should work
        result = editor.accept_ghost_text()
        assert result is True
        assert "FROM" in editor.toPlainText()
    
    def test_cursor_position_unchanged_after_ghost_text_display(self, editor):
        """Test that cursor position doesn't change when ghost text is displayed."""
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        original_position = cursor.position()
        
        # Show ghost text
        editor.show_ghost_text("macchiato", original_position)
        
        # Cursor should not have moved
        assert editor.textCursor().position() == original_position
    
    def test_cursor_position_unchanged_after_accept(self, editor):
        """Test that cursor is at correct position after accepting ghost text."""
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        original_position = cursor.position()
        
        # Show and accept ghost text
        editor.show_ghost_text("macchiato", original_position)
        editor.accept_ghost_text()
        
        # Cursor should be at end of "macchiato"
        text = editor.toPlainText()
        expected_position = text.find("macchiato") + len("macchiato")
        assert editor.textCursor().position() == expected_position
    
    def test_ghost_text_rejected_when_cursor_moves_during_display(self, editor):
        """Test that ghost text is not shown if cursor moves between request and display."""
        editor.setPlainText("SELECT mac")
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)
        
        position = cursor.position()
        
        # Cursor moves before showing ghost text
        cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.MoveAnchor, 3)
        editor.setTextCursor(cursor)
        
        # Try to show ghost text at old position
        editor.show_ghost_text("macchiato", position)
        
        # Ghost text should not be shown
        assert editor.ghost_text == ""
        assert editor.ghost_text_suggestion == ""
