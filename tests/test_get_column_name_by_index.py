"""
Tests for get_column_name_by_index method.

Tests edge cases and various scenarios for column name retrieval
after renames, deletes, and in different modes.
"""

import pytest
import pandas as pd

# Skip tests if PyQt6 is not available
pytest.importorskip("PyQt6")

from tests.conftest import requires_gui


@requires_gui
def test_get_column_name_by_index_invalid_negative_index(qapp, sample_df):
    """Test get_column_name_by_index with negative index."""
    from sqlshell.__main__ import SQLShell
    
    window = SQLShell()
    window.populate_table(sample_df)
    
    # Negative index should return None
    result = window.get_column_name_by_index(-1)
    assert result is None


@requires_gui
def test_get_column_name_by_index_invalid_large_index(qapp, sample_df):
    """Test get_column_name_by_index with index beyond column count."""
    from sqlshell.__main__ import SQLShell
    
    window = SQLShell()
    window.populate_table(sample_df)
    
    # Index beyond column count should return None
    num_cols = len(sample_df.columns)
    result = window.get_column_name_by_index(num_cols + 10)
    assert result is None


@requires_gui
def test_get_column_name_by_index_after_column_delete(qapp, sample_df):
    """Test get_column_name_by_index after deleting a column."""
    from sqlshell.__main__ import SQLShell
    
    window = SQLShell()
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()
    
    # Get initial column count
    initial_cols = list(current_tab.current_df.columns)
    initial_count = len(initial_cols)
    
    # Delete the first column
    if len(initial_cols) > 0:
        first_col = initial_cols[0]
        window.delete_column(first_col)
        
        # Verify column was deleted
        assert first_col not in current_tab.current_df.columns
        
        # get_column_name_by_index should now return the new first column
        if initial_count > 1:
            new_first_col = window.get_column_name_by_index(0)
            assert new_first_col is not None
            assert new_first_col != first_col
            assert new_first_col in current_tab.current_df.columns


@requires_gui
def test_get_column_name_by_index_after_multiple_deletes(qapp, sample_df):
    """Test get_column_name_by_index after deleting multiple columns."""
    from sqlshell.__main__ import SQLShell
    
    window = SQLShell()
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()
    
    initial_cols = list(current_tab.current_df.columns)
    if len(initial_cols) < 3:
        pytest.skip("Need at least 3 columns for this test")
    
    # Delete first two columns
    window.delete_column(initial_cols[0])
    window.delete_column(initial_cols[1])
    
    # Index 0 should now point to what was originally index 2
    if len(initial_cols) > 2:
        new_col_at_0 = window.get_column_name_by_index(0)
        assert new_col_at_0 == initial_cols[2]


@requires_gui
def test_get_column_name_by_index_with_no_data(qapp):
    """Test get_column_name_by_index when there's no data."""
    from sqlshell.__main__ import SQLShell
    
    window = SQLShell()
    # Don't populate any data
    
    # Should return None when no data
    result = window.get_column_name_by_index(0)
    assert result is None


@requires_gui
def test_get_column_name_by_index_in_preview_mode(qapp, sample_df):
    """Test get_column_name_by_index in preview mode."""
    from sqlshell.__main__ import SQLShell
    
    window = SQLShell()
    
    table_name = "test_table"
    
    class DummyDBManager:
        def __init__(self, df):
            self._df = df
            self.table_columns = {}  # Track column metadata
        
        def get_table_preview(self, name):
            return self._df.head()
        
        def get_full_table(self, name):
            return self._df
    
    window.db_manager = DummyDBManager(sample_df.copy())
    
    # Simulate preview mode
    current_tab = window.get_current_tab()
    current_tab.is_preview_mode = True
    current_tab.preview_table_name = table_name
    preview_df = window.db_manager.get_table_preview(table_name)
    window.populate_table(preview_df)
    
    # get_column_name_by_index should work in preview mode
    if len(sample_df.columns) > 0:
        col_name = window.get_column_name_by_index(0)
        assert col_name is not None
        assert col_name in sample_df.columns


@requires_gui
def test_get_column_name_by_index_after_rename_and_delete(qapp, sample_df, monkeypatch):
    """Test get_column_name_by_index after renaming and then deleting columns."""
    from PyQt6.QtWidgets import QInputDialog
    from sqlshell.__main__ import SQLShell
    
    window = SQLShell()
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()
    
    initial_cols = list(current_tab.current_df.columns)
    if len(initial_cols) < 2:
        pytest.skip("Need at least 2 columns for this test")
    
    # Rename first column
    def mock_get_text(*args, **kwargs):
        return "renamed_col", True
    
    monkeypatch.setattr(QInputDialog, "getText", mock_get_text)
    current_tab.handle_header_double_click(0)
    
    # Verify rename
    assert "renamed_col" in current_tab.current_df.columns
    
    # Delete a different column (second one)
    if len(initial_cols) > 1:
        second_col = initial_cols[1]
        window.delete_column(second_col)
        
        # get_column_name_by_index(0) should still return renamed column
        col_at_0 = window.get_column_name_by_index(0)
        assert col_at_0 == "renamed_col"


@requires_gui
def test_query_tab_get_column_name_by_index(qapp, sample_df):
    """Test QueryTab's get_column_name_by_index method."""
    from sqlshell.__main__ import SQLShell
    
    window = SQLShell()
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()
    
    # Test QueryTab's method directly
    if len(sample_df.columns) > 0:
        col_name = current_tab.get_column_name_by_index(0)
        assert col_name is not None
        assert col_name in sample_df.columns
    
    # Test with invalid index
    invalid_result = current_tab.get_column_name_by_index(9999)
    assert invalid_result is None


@requires_gui
def test_get_column_name_by_index_all_valid_indices(qapp, sample_df):
    """Test get_column_name_by_index for all valid column indices."""
    from sqlshell.__main__ import SQLShell
    
    window = SQLShell()
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()
    
    # Test all valid indices
    for i in range(len(sample_df.columns)):
        col_name = window.get_column_name_by_index(i)
        assert col_name is not None
        assert col_name == list(current_tab.current_df.columns)[i]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

