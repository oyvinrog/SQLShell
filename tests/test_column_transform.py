import pytest

from tests.conftest import requires_gui


@requires_gui
def test_transform_delete_column_updates_results(qapp, sample_df):
    """Deleting a column via the transform helper should update current_df and the table."""
    from sqlshell.__main__ import SQLShell

    window = SQLShell()

    # Populate the table with a known DataFrame
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Sanity checks before deletion
    assert current_tab is not None
    assert current_tab.current_df is not None
    assert "age" in current_tab.current_df.columns

    original_col_count = len(current_tab.current_df.columns)

    # Perform the delete transform
    window.delete_column("age")

    # current_df should be updated
    assert current_tab.current_df is not None
    assert "age" not in current_tab.current_df.columns
    assert len(current_tab.current_df.columns) == original_col_count - 1

    # The visible table should also reflect the change
    assert window.current_df is not None
    assert "age" not in window.current_df.columns
    assert window.get_current_tab().results_table.columnCount() == original_col_count - 1


@requires_gui
def test_preview_mode_delete_uses_full_table_and_persists_across_navigation(qapp, sample_df, monkeypatch):
    """
    In preview mode, deleting a column should:
    - operate on the full table (not just the 5-row preview),
    - cache a transformed full DataFrame for that table,
    - and be reflected again when previewing the same table later in the session.
    """
    from sqlshell.__main__ import SQLShell

    window = SQLShell()

    # Fake a loaded table in the DatabaseManager
    table_name = "users"

    class DummyDBManager:
        def __init__(self, df):
            self._df = df

        def get_table_preview(self, name):
            assert name == table_name
            # Return a small preview
            return self._df.head()

        def get_full_table(self, name):
            assert name == table_name
            # Return the full DataFrame
            return self._df

    # Swap in our dummy DB manager
    window.db_manager = DummyDBManager(sample_df.copy())

    # Simulate previewing the table from the sidebar
    current_tab = window.get_current_tab()
    current_tab.is_preview_mode = True
    current_tab.preview_table_name = table_name

    # Manually mimic what show_table_preview does for this test
    preview_df = window.db_manager.get_table_preview(table_name)
    window.populate_table(preview_df)

    # Sanity check: preview is a subset but still has the column
    assert "age" in preview_df.columns
    assert window.current_df is not None
    assert len(window.current_df) == len(preview_df)

    # Delete the column in preview mode
    window.delete_column("age")

    # The cached transformed full table should no longer have the column
    assert table_name in window._preview_transforms
    full_transformed = window._preview_transforms[table_name]
    assert "age" not in full_transformed.columns

    # The current preview shown in the UI should also not have the column
    current_tab = window.get_current_tab()
    assert current_tab.current_df is not None
    assert "age" not in current_tab.current_df.columns

    # Simulate navigating away and back: calling show_table_preview logic again
    # should use the transformed full table from _preview_transforms
    preview_df_again = window._preview_transforms[table_name].head()
    window.populate_table(preview_df_again)

    current_tab = window.get_current_tab()
    assert current_tab.current_df is not None
    assert "age" not in current_tab.current_df.columns

