import pytest

from tests.conftest import requires_gui


@requires_gui
def test_rename_column_analysis_uses_new_name(qapp, sample_df, monkeypatch):
    """After renaming a column, analysis functions should use the new column name."""
    from PyQt6.QtWidgets import QInputDialog
    from sqlshell.__main__ import SQLShell

    window = SQLShell()

    # Populate the table
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Rename "age" to "age_renamed"
    age_idx = list(current_tab.current_df.columns).index("age")
    
    def mock_get_text(*args, **kwargs):
        return "age_renamed", True
    
    monkeypatch.setattr(QInputDialog, "getText", mock_get_text)
    current_tab.handle_header_double_click(age_idx)

    # Verify rename occurred
    assert "age_renamed" in current_tab.current_df.columns
    assert "age" not in current_tab.current_df.columns

    # Now try to analyze the column - should use new name
    # Mock the visualize_profile to capture the column name used
    captured_column_name = None
    
    def mock_visualize_profile(df, column_name):
        nonlocal captured_column_name
        captured_column_name = column_name
        # Return a mock window
        from PyQt6.QtWidgets import QMainWindow
        return QMainWindow()
    
    monkeypatch.setattr("sqlshell.utils.profile_column.visualize_profile", mock_visualize_profile)
    
    # Get the column name using the helper method (simulating what the UI does)
    column_name = window.get_column_name_by_index(age_idx)
    assert column_name == "age_renamed", f"Expected 'age_renamed', got '{column_name}'"
    
    # Call explain_column with the new name
    window.explain_column(column_name)
    
    # Verify the analysis used the new column name
    assert captured_column_name == "age_renamed", \
        f"Analysis should use 'age_renamed', but used '{captured_column_name}'"


@requires_gui
def test_rename_column_cell_double_click_uses_new_name(qapp, sample_df, monkeypatch):
    """Double-clicking a cell after renaming should use the new column name."""
    from PyQt6.QtWidgets import QInputDialog
    from sqlshell.__main__ import SQLShell

    window = SQLShell()

    # Populate the table
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Rename "age" to "age_renamed"
    age_idx = list(current_tab.current_df.columns).index("age")
    
    def mock_get_text(*args, **kwargs):
        return "age_renamed", True
    
    monkeypatch.setattr(QInputDialog, "getText", mock_get_text)
    current_tab.handle_header_double_click(age_idx)

    # Verify rename occurred
    assert "age_renamed" in current_tab.current_df.columns

    # Double-click a cell in the renamed column
    # This should use the new column name
    current_tab.handle_cell_double_click(0, age_idx)
    
    # Check that the query editor contains the new column name
    query_text = current_tab.get_query_text()
    assert "age_renamed" in query_text or '"age_renamed"' in query_text, \
        f"Query should contain 'age_renamed', but got: {query_text}"
    assert "age" not in query_text or query_text.count("age") == query_text.count("age_renamed"), \
        f"Query should not contain old 'age' name, but got: {query_text}"


@requires_gui
def test_rename_column_header_context_menu_uses_new_name(qapp, sample_df, monkeypatch):
    """Right-clicking header after rename should show new column name in menu."""
    from PyQt6.QtWidgets import QInputDialog, QMenu
    from sqlshell.__main__ import SQLShell

    window = SQLShell()

    # Populate the table
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Rename "age" to "age_renamed"
    age_idx = list(current_tab.current_df.columns).index("age")
    
    def mock_get_text(*args, **kwargs):
        return "age_renamed", True
    
    # Mock QMenu.exec() to return immediately without blocking
    def mock_menu_exec(self, *args, **kwargs):
        """Mock QMenu.exec to return immediately without blocking"""
        return None  # Return None to indicate no action was selected
    
    monkeypatch.setattr(QInputDialog, "getText", mock_get_text)
    monkeypatch.setattr(QMenu, "exec", mock_menu_exec)
    
    current_tab.handle_header_double_click(age_idx)

    # Verify rename occurred
    assert "age_renamed" in current_tab.current_df.columns

    # Simulate header context menu - should use new name
    # The _show_header_context_menu method should get the column name correctly
    current_tab._show_header_context_menu(age_idx)
    
    # The column name should be retrieved correctly
    col_name = current_tab.get_column_name_by_index(age_idx)
    assert col_name == "age_renamed", f"Expected 'age_renamed', got '{col_name}'"


@requires_gui
def test_rename_column_preview_mode_analysis_uses_new_name(qapp, sample_df):
    """In preview mode, after renaming, analysis should use the new column name."""
    from sqlshell.__main__ import SQLShell

    window = SQLShell()

    table_name = "users"

    class DummyDBManager:
        def __init__(self, df):
            self._df = df

        def get_table_preview(self, name):
            return self._df.head()

        def get_full_table(self, name):
            return self._df

    window.db_manager = DummyDBManager(sample_df.copy())

    # Simulate previewing the table
    current_tab = window.get_current_tab()
    current_tab.is_preview_mode = True
    current_tab.preview_table_name = table_name
    preview_df = window.db_manager.get_table_preview(table_name)
    window.populate_table(preview_df)

    # Rename the column
    window.rename_column("age", "age_renamed")

    # Verify the rename in the transformed DataFrame
    assert table_name in window._preview_transforms
    transformed_df = window._preview_transforms[table_name]
    assert "age_renamed" in transformed_df.columns
    assert "age" not in transformed_df.columns

    # Get column name using helper - should return new name
    age_idx = list(transformed_df.columns).index("age_renamed")
    column_name = window.get_column_name_by_index(age_idx)
    assert column_name == "age_renamed", \
        f"get_column_name_by_index should return 'age_renamed', got '{column_name}'"

    # Verify get_data_for_tool returns DataFrame with new name
    df, _ = window.get_data_for_tool()
    assert df is not None
    assert "age_renamed" in df.columns
    assert "age" not in df.columns

