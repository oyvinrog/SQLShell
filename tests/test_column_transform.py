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
    assert "age" not in current_tab.current_df.columns
    assert len(current_tab.current_df.columns) == original_col_count - 1

    # The visible table should also reflect the change
    assert window.current_df is not None
    assert "age" not in window.current_df.columns
    assert window.get_current_tab().results_table.columnCount() == original_col_count - 1


