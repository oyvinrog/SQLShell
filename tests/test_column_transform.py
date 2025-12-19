import pytest

from tests.conftest import requires_gui

# Globally disable heavy startup actions to keep GUI tests fast and non-blocking
from sqlshell.__main__ import SQLShell as _SQLShellClass
_SQLShellClass.load_recent_projects = lambda self: None
_SQLShellClass.load_most_recent_project = lambda self: None
_SQLShellClass.update_completer = lambda self: None


def create_sqlshell_for_tests(monkeypatch=None):
    """Create SQLShell instance with heavy startup steps disabled."""
    from sqlshell.__main__ import SQLShell
    window = SQLShell()
    window.auto_load_recent_project = False
    return window


@requires_gui
def test_rename_column_analysis_uses_new_name(qapp, sample_df, monkeypatch):
    """After renaming a column, analysis functions should use the new column name."""
    from PyQt6.QtWidgets import QInputDialog
    window = create_sqlshell_for_tests(monkeypatch)

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
    window = create_sqlshell_for_tests(monkeypatch)

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
    window = create_sqlshell_for_tests(monkeypatch)

    # Populate the table
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Rename "age" to "age_renamed"
    age_idx = list(current_tab.current_df.columns).index("age")
    
    def mock_get_text(*args, **kwargs):
        return "age_renamed", True
    
    # Mock QMenu.exec() to return immediately without blocking
    original_exec = QMenu.exec
    
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
def test_rename_column_preview_mode_analysis_uses_new_name(qapp, sample_df, monkeypatch):
    """In preview mode, after renaming, analysis should use the new column name."""
    window = create_sqlshell_for_tests(monkeypatch)

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


@requires_gui
def test_transform_delete_column_updates_results(qapp, sample_df, monkeypatch):
    """Deleting a column via the transform helper should update current_df and the table."""
    window = create_sqlshell_for_tests(monkeypatch)

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
    window = create_sqlshell_for_tests(monkeypatch)

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


@requires_gui
def test_convert_to_query_friendly_names_for_table_creates_new_table(qapp, sample_df, monkeypatch):
    """
    Converting a table's column names via the left-hand table menu should:
    - operate on the full table (not just the preview),
    - create a NEW query result table with transformed column names,
    - show the transformed data in the current tab,
    - leave the original table untouched.
    """
    window = create_sqlshell_for_tests(monkeypatch)

    table_name = "users"

    class DummyDBManager:
        def __init__(self, df):
            self._df = df
            self.loaded_tables = {table_name: "file.csv"}
            self.table_columns = {table_name: list(df.columns)}
            self._registered_tables = {}

        def get_table_preview(self, name):
            assert name == table_name
            return self._df.head()

        def get_full_table(self, name):
            assert name == table_name
            return self._df

        def register_dataframe(self, df, new_table_name, source="query_result"):
            """Register a new DataFrame as a table."""
            self._registered_tables[new_table_name] = df
            self.loaded_tables[new_table_name] = source
            self.table_columns[new_table_name] = list(df.columns)
            return new_table_name

    window.db_manager = DummyDBManager(sample_df.copy())

    # Simulate previewing the table
    current_tab = window.get_current_tab()
    current_tab.is_preview_mode = True
    current_tab.preview_table_name = table_name
    preview_df = window.db_manager.get_table_preview(table_name)
    window.populate_table(preview_df)

    # Apply transform via table-level helper
    window.convert_to_query_friendly_names(table_name)

    # Check that a new table was created (not overwriting the original)
    # Should use pattern: {table_name}_transformed_{hash}
    new_tables = [name for name in window.db_manager.loaded_tables.keys() if name.startswith(f"{table_name}_transformed_")]
    assert len(new_tables) > 0, f"Should create a table with prefix '{table_name}_transformed_'"
    expected_new_table = new_tables[-1]
    assert expected_new_table in window.db_manager._registered_tables
    
    # Check the new table has transformed column names
    transformed_df = window.db_manager._registered_tables[expected_new_table]
    expected_columns = [col.strip().lower().replace(" ", "_") for col in sample_df.columns]
    assert list(transformed_df.columns) == expected_columns

    # Original table should still exist and be unchanged
    assert table_name in window.db_manager.loaded_tables
    original_df = window.db_manager.get_full_table(table_name)
    assert list(original_df.columns) == list(sample_df.columns)

    # Current tab should show the transformed data (full, not preview)
    current_tab = window.get_current_tab()
    assert current_tab is not None
    assert current_tab.current_df is not None
    assert current_tab.is_preview_mode == False  # Should be reset
    assert list(current_tab.current_df.columns) == expected_columns


@requires_gui
def test_convert_to_query_friendly_names_creates_new_table_for_queries(qapp, monkeypatch):
    """
    After converting a table's column names to query-friendly form, a NEW table is created.
    SQL queries against the NEW table name should see the new column names.
    The original table remains unchanged.
    """
    import pandas as pd
    window = create_sqlshell_for_tests(monkeypatch)

    # Create a DataFrame with a problematic column name that includes spaces
    df = pd.DataFrame(
        {
            "Artist ": ["a", "b", "c"],
            "Year": [2000, 2001, 2002],
        }
    )

    # Register this DataFrame as a table in the in-memory DuckDB
    table_name = window.db_manager.register_dataframe(df, "songs", source="file.csv")

    # Sanity check: initial columns in DuckDB should include the spaced name
    orig = window.db_manager.get_full_table(table_name)
    assert list(orig.columns) == ["Artist ", "Year"]

    # Apply the table-level transform
    window.convert_to_query_friendly_names(table_name)

    # A new table should be created with _transformed_{hash} pattern
    new_tables = [name for name in window.db_manager.loaded_tables.keys() if name.startswith(f"{table_name}_transformed_")]
    assert len(new_tables) > 0, f"Should create a table with prefix '{table_name}_transformed_'"
    new_table_name = new_tables[-1]

    # The new table should have query-friendly column names
    new_table_df = window.db_manager.get_full_table(new_table_name)
    assert list(new_table_df.columns) == ["artist", "year"]

    # SQL queries against the NEW table should work with the new column names
    result = window.db_manager.execute_query(f"SELECT artist, year FROM {new_table_name}")
    assert list(result.columns) == ["artist", "year"]

    # Original table should still have the original column names
    orig_after = window.db_manager.get_full_table(table_name)
    assert list(orig_after.columns) == ["Artist ", "Year"]


@requires_gui
def test_convert_current_results_to_query_friendly_names_creates_new_table(qapp, sample_df, monkeypatch):
    """
    Converting current results via the results table transform menu should:
    - create a NEW query result table with transformed column names,
    - contain only the current results (not the full original table),
    - use a hash-based name to avoid collisions.
    """
    window = create_sqlshell_for_tests(monkeypatch)

    # Populate the table with a known DataFrame (non-preview mode)
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Sanity checks
    assert current_tab is not None
    assert current_tab.current_df is not None
    assert list(current_tab.current_df.columns) == list(sample_df.columns)
    original_row_count = len(current_tab.current_df)

    # Apply transform
    window.convert_current_results_to_query_friendly_names()

    # Verify a new table was created (should start with "query_result_" since no base table name)
    new_tables = [name for name in window.db_manager.loaded_tables.keys() if name.startswith("query_result_")]
    assert len(new_tables) > 0, "Should create at least one new query_result table"
    
    # Get the most recently created one (should be the last in the list)
    new_table_name = new_tables[-1]
    
    # Verify the new table has transformed column names
    new_table_df = window.db_manager.get_full_table(new_table_name)
    expected_cols = [col.strip().lower().replace(" ", "_") for col in sample_df.columns]
    assert list(new_table_df.columns) == expected_cols
    
    # Verify the new table contains the same number of rows as the current results
    assert len(new_table_df) == original_row_count, \
        f"New table should have {original_row_count} rows (same as current results), got {len(new_table_df)}"

    # Verify current_df is updated
    assert current_tab.current_df is not None
    assert list(current_tab.current_df.columns) == expected_cols

    # Visible table headers should also match
    headers = [
        current_tab.results_table.horizontalHeaderItem(i).text()
        for i in range(current_tab.results_table.columnCount())
    ]
    assert headers == expected_cols


@requires_gui
def test_convert_preview_mode_uses_full_table_not_preview(qapp, monkeypatch):
    """
    When in preview mode (clicking a table in the sidebar), the transform should use
    the FULL underlying table data, not just the 5-row preview.
    """
    import pandas as pd
    window = create_sqlshell_for_tests(monkeypatch)

    # Create a larger DataFrame (more than 5 rows) to test preview vs full table
    full_table = pd.DataFrame({
        'id': range(1, 11),  # 10 rows
        'name': [f'User_{i}' for i in range(1, 11)],
        'age': [20 + i for i in range(10)],
        'salary': [50000.0 + i * 1000 for i in range(10)],
        'department': ['Engineering', 'Marketing', 'Sales'] * 3 + ['Engineering']
    })
    table_name = "users"

    class DummyDBManager:
        def __init__(self, df):
            self._df = df
            self.loaded_tables = {table_name: "file.csv"}
            self.table_columns = {table_name: list(df.columns)}
            self._registered_tables = {}

        def get_table_preview(self, name):
            # Return only 5 rows (preview)
            return self._df.head()

        def get_full_table(self, name):
            # Return full table
            return self._df

        def register_dataframe(self, df, new_table_name, source="query_result"):
            self._registered_tables[new_table_name] = df
            self.loaded_tables[new_table_name] = source
            self.table_columns[new_table_name] = list(df.columns)
            return new_table_name

    window.db_manager = DummyDBManager(full_table.copy())

    # Simulate previewing the table (showing only 5 rows)
    current_tab = window.get_current_tab()
    current_tab.is_preview_mode = True
    current_tab.preview_table_name = table_name
    preview_df = window.db_manager.get_table_preview(table_name)
    window.populate_table(preview_df)

    # Verify we're in preview mode with only 5 rows shown
    assert current_tab.is_preview_mode == True
    assert len(current_tab.current_df) == 5  # Preview has 5 rows
    assert len(full_table) > 5  # Full table has more rows

    # Apply transform from results menu
    window.convert_current_results_to_query_friendly_names()

    # Find the newly created table (should use table name prefix since in preview mode)
    new_tables = [name for name in window.db_manager.loaded_tables.keys() if name.startswith(f"{table_name}_transformed_")]
    assert len(new_tables) > 0, f"Should create a table with prefix '{table_name}_transformed_'"
    new_table_name = new_tables[-1]

    # Verify the new table contains the FULL table data (all rows), not just the 5-row preview
    new_table_df = window.db_manager.get_full_table(new_table_name)
    assert len(new_table_df) == len(full_table), \
        f"New table should have {len(full_table)} rows (full table), not {len(new_table_df)} (preview only)"
    
    # Verify column names are transformed
    expected_cols = [col.strip().lower().replace(" ", "_") for col in full_table.columns]
    assert list(new_table_df.columns) == expected_cols


@requires_gui
def test_convert_filtered_results_creates_table_with_only_filtered_data(qapp, monkeypatch):
    """
    When converting filtered/selected results (e.g., WHERE song LIKE '%love%'),
    the new table should contain ONLY those filtered rows, not the full original table.
    """
    import pandas as pd
    window = create_sqlshell_for_tests(monkeypatch)

    # Create a DataFrame with songs data
    songs_df = pd.DataFrame({
        "song": ["Love Story", "Love Me Do", "Happy", "Love is All", "Sad Song"],
        "artist": ["Taylor Swift", "Beatles", "Pharrell", "Beatles", "Unknown"],
        "year": [2008, 1962, 2013, 1967, 2020]
    })

    # Simulate a filtered query result (e.g., WHERE song LIKE '%love%')
    filtered_df = songs_df[songs_df["song"].str.contains("love", case=False)]
    assert len(filtered_df) == 3, "Should have 3 songs with 'love' in the name"
    assert len(filtered_df) < len(songs_df), "Filtered should be smaller than original"

    # Populate with the filtered results
    window.populate_table(filtered_df)
    current_tab = window.get_current_tab()
    
    # Verify we have the filtered data
    assert len(current_tab.current_df) == 3
    assert all("love" in song.lower() for song in current_tab.current_df["song"])

    # Apply transform
    window.convert_current_results_to_query_friendly_names()

    # Find the newly created table
    new_tables = [name for name in window.db_manager.loaded_tables.keys() if name.startswith("query_result_")]
    assert len(new_tables) > 0
    new_table_name = new_tables[-1]

    # Verify the new table contains ONLY the filtered rows (3 rows), not the full original (5 rows)
    new_table_df = window.db_manager.get_full_table(new_table_name)
    assert len(new_table_df) == 3, \
        f"New table should have 3 rows (filtered results), not {len(new_table_df)} (full table)"
    
    # Verify all rows in the new table have 'love' in the song name
    assert all("love" in song.lower() for song in new_table_df["song"]), \
        "All rows in new table should match the original filter"
    
    # Verify column names are transformed
    assert "song" in new_table_df.columns
    assert "artist" in new_table_df.columns
    assert "year" in new_table_df.columns


@requires_gui
def test_multiple_transforms_create_different_tables(qapp, monkeypatch):
    """
    Multiple transforms of different result sets should create different tables
    (hash-based naming prevents collisions).
    """
    import pandas as pd
    window = create_sqlshell_for_tests(monkeypatch)

    # Create first result set
    df1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    window.populate_table(df1)
    window.convert_current_results_to_query_friendly_names()

    # Create second result set with different data
    df2 = pd.DataFrame({"X": [10, 20], "Y": [30, 40]})
    window.populate_table(df2)
    window.convert_current_results_to_query_friendly_names()

    # Both should create different tables
    new_tables = [name for name in window.db_manager.loaded_tables.keys() if name.startswith("query_result_")]
    assert len(new_tables) >= 2, "Should create at least 2 different tables"
    
    # Verify they have different data
    table1_df = window.db_manager.get_full_table(new_tables[-2])
    table2_df = window.db_manager.get_full_table(new_tables[-1])
    
    assert list(table1_df.columns) != list(table2_df.columns), \
        "Different result sets should create tables with different schemas"

@requires_gui
def test_query_friendly_names_trims_whitespace(qapp, monkeypatch):
    """
    The query-friendly name conversion should properly trim leading and trailing whitespace.
    Tests cases like "artist ", " artist", " artist ", etc.
    """
    import pandas as pd
    window = create_sqlshell_for_tests(monkeypatch)

    # Create a DataFrame with column names that have whitespace issues
    df_with_whitespace = pd.DataFrame({
        " artist ": [1, 2, 3],  # Leading and trailing spaces
        "artist ": [4, 5, 6],   # Trailing space
        " artist": [7, 8, 9],   # Leading space
        "Artist Name": [10, 11, 12],  # Multiple words with spaces
        "  Multiple   Spaces  ": [13, 14, 15],  # Multiple spaces and leading/trailing
        "normal_column": [16, 17, 18],  # Normal column (no spaces)
    })

    # Test the helper method directly
    assert window._make_query_friendly_name(" artist ") == "artist"
    assert window._make_query_friendly_name("artist ") == "artist"
    assert window._make_query_friendly_name(" artist") == "artist"
    assert window._make_query_friendly_name("Artist Name") == "artist_name"
    assert window._make_query_friendly_name("  Multiple   Spaces  ") == "multiple_spaces"
    assert window._make_query_friendly_name("normal_column") == "normal_column"

    # Test on actual DataFrame via current results transform
    window.populate_table(df_with_whitespace)
    current_tab = window.get_current_tab()

    # Apply transform
    window.convert_current_results_to_query_friendly_names()

    # Verify all columns are properly trimmed and converted
    expected_columns = [
        "artist",           # " artist " -> trimmed, lowercased
        "artist",           # "artist " -> trimmed, lowercased
        "artist",           # " artist" -> trimmed, lowercased
        "artist_name",      # "Artist Name" -> lowercased, spaces to underscores
        "multiple_spaces",  # "  Multiple   Spaces  " -> trimmed, lowercased, spaces to underscores, collapsed
        "normal_column",    # "normal_column" -> unchanged (already friendly)
    ]

    assert list(current_tab.current_df.columns) == expected_columns

    # Verify visible table headers also match
    headers = [
        current_tab.results_table.horizontalHeaderItem(i).text()
        for i in range(current_tab.results_table.columnCount())
    ]
    assert headers == expected_columns


@requires_gui
def test_rename_column_updates_results(qapp, sample_df, monkeypatch):
    """Renaming a column via the rename helper should update current_df and the table."""

    # Populate the table with a known DataFrame
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Sanity checks before rename
    assert current_tab is not None
    assert current_tab.current_df is not None
    assert "age" in current_tab.current_df.columns
    assert "age_renamed" not in current_tab.current_df.columns

    original_col_count = len(current_tab.current_df.columns)

    # Perform the rename
    window.rename_column("age", "age_renamed")

    # current_df should be updated
    assert current_tab.current_df is not None
    assert "age" not in current_tab.current_df.columns
    assert "age_renamed" in current_tab.current_df.columns
    assert len(current_tab.current_df.columns) == original_col_count  # Same number of columns

    # The visible table should also reflect the change
    assert window.current_df is not None
    assert "age" not in window.current_df.columns
    assert "age_renamed" in window.current_df.columns
    assert window.get_current_tab().results_table.columnCount() == original_col_count

    # Verify visible table headers also match
    headers = [
        current_tab.results_table.horizontalHeaderItem(i).text()
        for i in range(current_tab.results_table.columnCount())
    ]
    assert "age" not in headers
    assert "age_renamed" in headers


@requires_gui
def test_preview_mode_rename_uses_full_table_and_persists_across_navigation(qapp, sample_df, monkeypatch):
    """
    In preview mode, renaming a column should:
    - operate on the full table (not just the 5-row preview),
    - cache a transformed full DataFrame for that table,
    - and be reflected again when previewing the same table later in the session.
    """
    window = create_sqlshell_for_tests(monkeypatch)

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

    # Rename the column in preview mode
    window.rename_column("age", "age_renamed")

    # The cached transformed full table should have the renamed column
    assert table_name in window._preview_transforms
    full_transformed = window._preview_transforms[table_name]
    assert "age" not in full_transformed.columns
    assert "age_renamed" in full_transformed.columns

    # The current preview shown in the UI should also have the renamed column
    current_tab = window.get_current_tab()
    assert current_tab.current_df is not None
    assert "age" not in current_tab.current_df.columns
    assert "age_renamed" in current_tab.current_df.columns

    # Simulate reopening the table - should use the cached transformed version
    # This mimics what happens when you click the table again in the sidebar
    preview_df_after_reopen = window._preview_transforms[table_name].head()
    window.populate_table(preview_df_after_reopen)

    # Verify the rename persists after reopening
    current_tab = window.get_current_tab()
    assert current_tab.current_df is not None
    assert "age" not in current_tab.current_df.columns
    assert "age_renamed" in current_tab.current_df.columns

    # Verify the full table also has the rename
    full_table_after_reopen = window._preview_transforms[table_name]
    assert "age" not in full_table_after_reopen.columns
    assert "age_renamed" in full_table_after_reopen.columns
    assert len(full_table_after_reopen) == len(sample_df)  # Full table should have all rows


@requires_gui
def test_rename_column_prevents_duplicate_names(qapp, sample_df, monkeypatch):
    """Renaming a column to an existing name should fail."""

    # Populate the table with a known DataFrame
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Sanity checks
    assert current_tab is not None
    assert current_tab.current_df is not None
    assert "age" in current_tab.current_df.columns
    assert "name" in current_tab.current_df.columns

    # Try to rename "age" to "name" (which already exists) - should fail
    window.rename_column("age", "name")

    # The column should still be named "age" (rename should have failed)
    assert "age" in current_tab.current_df.columns
    assert current_tab.current_df.columns.tolist().count("name") == 1  # Only one "name" column


@requires_gui
def test_rename_column_via_double_click(qapp, sample_df, monkeypatch):
    """Double-clicking a column header should allow renaming."""
    from PyQt6.QtWidgets import QInputDialog
    window = create_sqlshell_for_tests(monkeypatch)

    # Populate the table with a known DataFrame
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Sanity checks
    assert current_tab is not None
    assert current_tab.current_df is not None
    assert "age" in current_tab.current_df.columns

    # Find the index of the "age" column
    age_idx = list(current_tab.current_df.columns).index("age")

    # Mock QInputDialog to return a new name
    def mock_get_text(*args, **kwargs):
        return "age_renamed", True

    monkeypatch.setattr(QInputDialog, "getText", mock_get_text)

    # Simulate double-click on the header
    current_tab.handle_header_double_click(age_idx)

    # Verify the rename occurred
    assert "age" not in current_tab.current_df.columns
    assert "age_renamed" in current_tab.current_df.columns

    # Verify the table header was updated
    header_text = current_tab.results_table.horizontalHeaderItem(age_idx).text()
    assert header_text == "age_renamed"


@requires_gui
def test_query_friendly_names_for_table_trims_whitespace(qapp, monkeypatch):
    """
    The table-level query-friendly name conversion should also properly trim whitespace.
    """
    import pandas as pd
    window = create_sqlshell_for_tests(monkeypatch)

    # Create a DataFrame with column names that have whitespace issues
    df_with_whitespace = pd.DataFrame({
        " artist ": [1, 2, 3],  # Leading and trailing spaces
        "artist ": [4, 5, 6],   # Trailing space
        " Artist Name ": [7, 8, 9],  # Leading/trailing spaces + multiple words
    })

    table_name = "test_table"

    class DummyDBManager:
        def __init__(self, df):
            self._df = df
            self.loaded_tables = {table_name: "file.csv"}
            self.table_columns = {table_name: list(df.columns)}
            self._registered_tables = {}

        def get_table_preview(self, name):
            return self._df.head()

        def get_full_table(self, name):
            return self._df

        def register_dataframe(self, df, new_table_name, source="query_result"):
            """Register a new DataFrame as a table."""
            self._registered_tables[new_table_name] = df
            self.loaded_tables[new_table_name] = source
            self.table_columns[new_table_name] = list(df.columns)
            return new_table_name

    window.db_manager = DummyDBManager(df_with_whitespace.copy())

    # Simulate previewing the table
    current_tab = window.get_current_tab()
    current_tab.is_preview_mode = True
    current_tab.preview_table_name = table_name
    preview_df = window.db_manager.get_table_preview(table_name)
    window.populate_table(preview_df)

    # Apply transform via table-level helper
    window.convert_to_query_friendly_names(table_name)

    # Check that a new table was created with trimmed names (pattern: {table_name}_transformed_{hash})
    new_tables = [name for name in window.db_manager.loaded_tables.keys() if name.startswith(f"{table_name}_transformed_")]
    assert len(new_tables) > 0, f"Should create a table with prefix '{table_name}_transformed_'"
    expected_new_table = new_tables[-1]
    transformed_df = window.db_manager._registered_tables[expected_new_table]
    expected_columns = ["artist", "artist", "artist_name"]
    assert list(transformed_df.columns) == expected_columns

    # Original table should still have original column names
    original_df = window.db_manager.get_full_table(table_name)
    assert list(original_df.columns) == [" artist ", "artist ", " Artist Name "]

    # Current tab should show the transformed data with trimmed names
    current_tab = window.get_current_tab()
    assert current_tab is not None
    assert current_tab.current_df is not None
    assert current_tab.is_preview_mode == False  # Should be reset
    actual_columns = list(current_tab.current_df.columns)
    assert actual_columns == expected_columns, (
        f"Expected columns {expected_columns} but got {actual_columns}. "
        f"Preview mode: {current_tab.is_preview_mode}, "
        f"Preview table name: {current_tab.preview_table_name}"
    )


@requires_gui
def test_query_friendly_names_handles_special_characters(qapp, monkeypatch):
    """
    The query-friendly name conversion should handle special characters like @, [, {, etc.
    Only a-z, 0-9, and underscores should be allowed, and consecutive underscores should be collapsed.
    """
    import pandas as pd
    window = create_sqlshell_for_tests(monkeypatch)

    # Test the helper method directly with various special characters
    assert window._make_query_friendly_name("column@name") == "column_name"
    assert window._make_query_friendly_name("column[name]") == "column_name"
    assert window._make_query_friendly_name("column{name}") == "column_name"
    assert window._make_query_friendly_name("column#name") == "column_name"
    assert window._make_query_friendly_name("column$name") == "column_name"
    assert window._make_query_friendly_name("column%name") == "column_name"
    assert window._make_query_friendly_name("column&name") == "column_name"
    assert window._make_query_friendly_name("column*name") == "column_name"
    assert window._make_query_friendly_name("column+name") == "column_name"
    assert window._make_query_friendly_name("column-name") == "column_name"
    assert window._make_query_friendly_name("column=name") == "column_name"
    assert window._make_query_friendly_name("column!name") == "column_name"
    assert window._make_query_friendly_name("column@[name]") == "column_name"
    assert window._make_query_friendly_name("@column") == "column"
    assert window._make_query_friendly_name("column@") == "column"
    assert window._make_query_friendly_name("@@@") == "column"  # All special chars -> default
    assert window._make_query_friendly_name("column__name") == "column_name"  # Collapse underscores
    assert window._make_query_friendly_name("column___name") == "column_name"  # Collapse multiple underscores
    assert window._make_query_friendly_name("_column_name_") == "column_name"  # Trim leading/trailing underscores
    assert window._make_query_friendly_name("column123") == "column123"  # Numbers allowed
    assert window._make_query_friendly_name("Column_Name") == "column_name"  # Uppercase converted

    # Test on actual DataFrame with special characters
    df_with_special = pd.DataFrame({
        "column@name": [1, 2, 3],
        "[bracketed]": [4, 5, 6],
        "{braced}": [7, 8, 9],
        "normal_column": [10, 11, 12],
        "column__with__underscores": [13, 14, 15],
        "@leading": [16, 17, 18],
        "trailing@": [19, 20, 21],
    })

    window.populate_table(df_with_special)
    current_tab = window.get_current_tab()

    # Apply transform
    window.convert_current_results_to_query_friendly_names()

    # Verify all columns are properly transformed
    expected_columns = [
        "column_name",
        "bracketed",
        "braced",
        "normal_column",
        "column_with_underscores",
        "leading",
        "trailing",
    ]

    assert list(current_tab.current_df.columns) == expected_columns

    # Verify visible table headers also match
    headers = [
        current_tab.results_table.horizontalHeaderItem(i).text()
        for i in range(current_tab.results_table.columnCount())
    ]
    assert headers == expected_columns


@requires_gui
def test_rename_column_updates_results(qapp, sample_df, monkeypatch):
    """Renaming a column via the rename helper should update current_df and the table."""
    window = create_sqlshell_for_tests(monkeypatch)

    # Populate the table with a known DataFrame
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Sanity checks before rename
    assert current_tab is not None
    assert current_tab.current_df is not None
    assert "age" in current_tab.current_df.columns
    assert "age_renamed" not in current_tab.current_df.columns

    original_col_count = len(current_tab.current_df.columns)

    # Perform the rename
    window.rename_column("age", "age_renamed")

    # current_df should be updated
    assert current_tab.current_df is not None
    assert "age" not in current_tab.current_df.columns
    assert "age_renamed" in current_tab.current_df.columns
    assert len(current_tab.current_df.columns) == original_col_count  # Same number of columns

    # The visible table should also reflect the change
    assert window.current_df is not None
    assert "age" not in window.current_df.columns
    assert "age_renamed" in window.current_df.columns
    assert window.get_current_tab().results_table.columnCount() == original_col_count

    # Verify visible table headers also match
    headers = [
        current_tab.results_table.horizontalHeaderItem(i).text()
        for i in range(current_tab.results_table.columnCount())
    ]
    assert "age" not in headers
    assert "age_renamed" in headers


@requires_gui
def test_preview_mode_rename_uses_full_table_and_persists_across_navigation(qapp, sample_df, monkeypatch):
    """
    In preview mode, renaming a column should:
    - operate on the full table (not just the 5-row preview),
    - cache a transformed full DataFrame for that table,
    - and be reflected again when previewing the same table later in the session.
    """
    window = create_sqlshell_for_tests(monkeypatch)

    # Fake a loaded table in the DatabaseManager
    table_name = "users"

    class DummyDBManager:
        def __init__(self, df):
            self._df = df
            self.loaded_tables = {table_name: "file.csv"}
            self.table_columns = {table_name: list(df.columns)}

        def get_table_preview(self, name):
            assert name == table_name
            # Return a small preview
            return self._df.head()

        def get_full_table(self, name):
            assert name == table_name
            # Return the full DataFrame
            return self._df
        
        def overwrite_table_with_dataframe(self, name, df, source="query_result"):
            self._df = df

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

    # Rename the column in preview mode
    window.rename_column("age", "age_renamed")

    # The cached transformed full table should have the renamed column
    assert table_name in window._preview_transforms
    full_transformed = window._preview_transforms[table_name]
    assert "age" not in full_transformed.columns
    assert "age_renamed" in full_transformed.columns

    # The current preview shown in the UI should also have the renamed column
    current_tab = window.get_current_tab()
    assert current_tab.current_df is not None
    assert "age" not in current_tab.current_df.columns
    assert "age_renamed" in current_tab.current_df.columns

    # Simulate reopening the table - should use the cached transformed version
    # This mimics what happens when you click the table again in the sidebar
    preview_df_after_reopen = window._preview_transforms[table_name].head()
    window.populate_table(preview_df_after_reopen)

    # Verify the rename persists after reopening
    current_tab = window.get_current_tab()
    assert current_tab.current_df is not None
    assert "age" not in current_tab.current_df.columns
    assert "age_renamed" in current_tab.current_df.columns

    # Verify the full table also has the rename
    full_table_after_reopen = window._preview_transforms[table_name]
    assert "age" not in full_table_after_reopen.columns
    assert "age_renamed" in full_table_after_reopen.columns
    assert len(full_table_after_reopen) == len(sample_df)  # Full table should have all rows


@requires_gui
def test_rename_column_prevents_duplicate_names(qapp, sample_df, monkeypatch):
    """Renaming a column to an existing name should fail."""
    window = create_sqlshell_for_tests(monkeypatch)

    # Populate the table with a known DataFrame
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Sanity checks
    assert current_tab is not None
    assert current_tab.current_df is not None
    assert "age" in current_tab.current_df.columns
    assert "name" in current_tab.current_df.columns

    # Try to rename "age" to "name" (which already exists) - should fail
    window.rename_column("age", "name")

    # The column should still be named "age" (rename should have failed)
    assert "age" in current_tab.current_df.columns
    assert current_tab.current_df.columns.tolist().count("name") == 1  # Only one "name" column


@requires_gui
def test_rename_column_via_double_click(qapp, sample_df, monkeypatch):
    """Double-clicking a column header should allow renaming."""
    from PyQt6.QtWidgets import QInputDialog
    window = create_sqlshell_for_tests(monkeypatch)

    # Populate the table with a known DataFrame
    window.populate_table(sample_df)
    current_tab = window.get_current_tab()

    # Sanity checks
    assert current_tab is not None
    assert current_tab.current_df is not None
    assert "age" in current_tab.current_df.columns

    # Find the index of the "age" column
    age_idx = list(current_tab.current_df.columns).index("age")

    # Mock QInputDialog to return a new name
    def mock_get_text(*args, **kwargs):
        return "age_renamed", True

    monkeypatch.setattr(QInputDialog, "getText", mock_get_text)

    # Simulate double-click on the header
    current_tab.handle_header_double_click(age_idx)

    # Verify the rename occurred
    assert "age" not in current_tab.current_df.columns
    assert "age_renamed" in current_tab.current_df.columns

    # Verify the table header was updated
    header_text = current_tab.results_table.horizontalHeaderItem(age_idx).text()
    assert header_text == "age_renamed"



@requires_gui
def test_rename_column_analysis_uses_new_name(qapp, sample_df, monkeypatch):
    """After renaming a column, analysis functions should use the new column name."""
    from PyQt6.QtWidgets import QInputDialog
    window = create_sqlshell_for_tests(monkeypatch)

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

    # Get the column name using the helper method (simulating what the UI does)
    column_name = window.get_column_name_by_index(age_idx)
    assert column_name == "age_renamed", f"Expected 'age_renamed', got '{column_name}'"


@requires_gui
def test_rename_column_cell_double_click_uses_new_name(qapp, sample_df, monkeypatch):
    """Double-clicking a cell after renaming should use the new column name."""
    from PyQt6.QtWidgets import QInputDialog
    window = create_sqlshell_for_tests(monkeypatch)

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


@requires_gui
def test_rename_column_preview_mode_analysis_uses_new_name(qapp, sample_df, monkeypatch):
    """In preview mode, after renaming, analysis should use the new column name."""
    window = create_sqlshell_for_tests(monkeypatch)

    table_name = "users"

    class DummyDBManager:
        def __init__(self, df):
            self._df = df
            self.loaded_tables = {table_name: "file.csv"}
            self.table_columns = {table_name: list(df.columns)}

        def get_table_preview(self, name):
            return self._df.head()

        def get_full_table(self, name):
            return self._df
        
        def overwrite_table_with_dataframe(self, name, df, source="query_result"):
            self._df = df

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
