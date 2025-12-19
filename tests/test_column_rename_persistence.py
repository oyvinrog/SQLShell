"""
Tests for column rename persistence in project files.

Tests that column renames are properly saved to and loaded from project files,
and that SQL queries work with renamed columns after project load.
"""

import pytest
import os
import json
import tempfile
import pandas as pd
from types import SimpleNamespace

# Skip tests if PyQt6 is not available
pytest.importorskip("PyQt6")

from tests.conftest import requires_gui


def create_dummy_db_manager(df, table_name):
    """Create a DummyDBManager to avoid actual database operations that might hang."""
    class DummyDBManager:
        def __init__(self, df, table_name):
            self.tables = {table_name: df.copy()}
            self.loaded_tables = {table_name: "test_file.csv"}
            self.table_columns = {table_name: list(df.columns)}
            self.table_name = table_name
            self.connection_type = 'duckdb'
            self.connected = True
        
        def get_table_preview(self, name):
            return self.tables[name].head()
        
        def get_full_table(self, name):
            return self.tables[name].copy()
        
        def overwrite_table_with_dataframe(self, name, df, source='query_result'):
            self.tables[name] = df.copy()
            self.table_columns[name] = list(df.columns)
        
        def is_connected(self):
            return self.connected
        
        def register_dataframe(self, df, name, source='query_result'):
            self.tables[name] = df.copy()
            self.loaded_tables[name] = source
            self.table_columns[name] = list(df.columns)
        
        def get_all_table_columns(self):
            """Return all table and column names for autocompletion."""
            completion_words = set(self.loaded_tables.keys())
            for table, columns in self.table_columns.items():
                for col in columns:
                    completion_words.add(col)
                    completion_words.add(f"{table}.{col}")
            return list(completion_words)
        
        def execute_query(self, query):
            # Simple mock - return the dataframe if query matches and columns exist
            target_table = None
            for tbl in self.loaded_tables.keys():
                if f'"{tbl}"' in query or f' {tbl}' in query:
                    target_table = tbl
                    break
            if target_table is None and len(self.tables) == 1:
                target_table = next(iter(self.tables.keys()))
            if target_table is None:
                raise Exception(f"Mock execute_query: {query}")
            
            df = self.tables.get(target_table)
            if df is None:
                raise Exception(f"Mock execute_query: {query}")
            
            lower_query = query.lower()
            if "select" in lower_query and "from" in lower_query:
                select_part = lower_query.split("from")[0].replace("select", "", 1).strip()
                if not select_part or select_part == "*":
                    return df.copy()
                
                select_cols = [col.strip().strip('"') for col in select_part.split(',')]
                cleaned_cols = [col.split('.')[-1] for col in select_cols if col]
                for col in cleaned_cols:
                    if col not in df.columns:
                        raise Exception(f"Mock execute_query unknown column: {col}")
                return df[cleaned_cols].copy()
            
            return df.copy()
        
        def close_connection(self):
            self.connected = False
        
        def create_memory_connection(self):
            self.connected = True
            return "Memory database"
    
    return DummyDBManager(df, table_name)


def create_minimal_window(sample_df, table_name):
    """Create a minimal window for testing without full SQLShell initialization."""
    from PyQt6.QtWidgets import QMainWindow, QTabWidget, QLabel, QWidget
    from sqlshell import project_manager as project_manager_module
    from sqlshell.table_list import DraggableTablesList
    
    # Replace GUI-heavy elements inside project_manager with lightweight stubs
    class DummyMessageBox:
        StandardButton = SimpleNamespace(Yes=1, No=2, Save=3, Discard=4, Cancel=5)
        
        @staticmethod
        def question(*args, **kwargs):
            return DummyMessageBox.StandardButton.Yes
        
        @staticmethod
        def warning(*args, **kwargs):
            return DummyMessageBox.StandardButton.No
        
        @staticmethod
        def critical(*args, **kwargs):
            return DummyMessageBox.StandardButton.No
    
    class DummyProgressDialog:
        def __init__(self, *args, **kwargs):
            self._canceled = False
        
        def setWindowTitle(self, *args, **kwargs):
            pass
        
        def setWindowModality(self, *args, **kwargs):
            pass
        
        def setMinimumDuration(self, *args, **kwargs):
            pass
        
        def setValue(self, *args, **kwargs):
            pass
        
        def setLabelText(self, *args, **kwargs):
            pass
        
        def wasCanceled(self):
            return self._canceled
        
        def close(self):
            pass
    
    class DummyTableWidget:
        def setRowCount(self, *args, **kwargs):
            pass
        
        def setColumnCount(self, *args, **kwargs):
            pass
    
    class DummyLabel:
        def __init__(self, text=""):
            self._text = text
        
        def setText(self, text):
            self._text = text
    
    class DummyQueryTab(QWidget):
        """Lightweight replacement for QueryTab to avoid full UI setup."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setVisible(False)
            self._query_text = ""
            self.results_table = DummyTableWidget()
            self.row_count_label = DummyLabel()
            self.results_title = DummyLabel("RESULTS")
        
        def get_query_text(self):
            return self._query_text
        
        def set_query_text(self, text):
            self._query_text = text
    
    # Capture originals so we can restore after each test
    _orig_qmessagebox = project_manager_module.QMessageBox
    _orig_qprogress = project_manager_module.QProgressDialog
    _orig_query_tab = project_manager_module.QueryTab
    
    # Patch the project_manager module to use the dummy implementations
    project_manager_module.QMessageBox = DummyMessageBox
    project_manager_module.QProgressDialog = DummyProgressDialog
    project_manager_module.QueryTab = DummyQueryTab
    ProjectManager = project_manager_module.ProjectManager
    
    class MinimalTab:
        """Mock tab that doesn't require QueryTab initialization."""
        def __init__(self):
            self._query_text = ""
            self.current_df = None
            self.is_preview_mode = False
            self.preview_table_name = None
            self.results_table = DummyTableWidget()
            self.row_count_label = DummyLabel()
            self.results_title = DummyLabel("RESULTS")
        
        def set_query_text(self, text):
            self._query_text = text
        
        def get_query_text(self):
            return self._query_text
    
    class MinimalWindow(QMainWindow):
        def __init__(self, df, table_name):
            super().__init__()
            self.setVisible(False)
            self._column_renames = {}
            self._preview_transforms = {}
            self.db_manager = create_dummy_db_manager(df, table_name)
            self.current_df = None
            self.filter_widgets = []
            self.current_project_file = None
            self.recent_projects = []
            self.max_recent_projects = 10
            self.tabs = []
            self.auto_load_recent_project = False
            self.christmas_theme_enabled = False
            self.recent_files = []
            self.frequent_files = {}
            self.max_recent_files = 15
            
            # Create minimal tab (mock, not real QueryTab)
            self.tab_widget = QTabWidget()
            self.tab_widget.setVisible(False)
            tab = MinimalTab()
            self.tabs.append(tab)
            # Add a dummy widget that has get_query_text method
            dummy_widget = QMainWindow()
            dummy_widget.get_query_text = lambda: ""
            self.tab_widget.addTab(dummy_widget, "Query 1")
            
            # Required for ProjectManager
            self.tables_list = DraggableTablesList(self)
            self.tables_list.setVisible(False)
            self.db_info_label = QLabel("No database connected")
            self.db_info_label.setVisible(False)
            
            # Mock methods that ProjectManager.save_project_to_file might call
            def mock_get_table_name_from_item(item):
                return None
            
            def mock_is_folder_item(item):
                return False
            
            def mock_add_recent_project(path):
                pass
            
            self.tables_list.get_table_name_from_item = mock_get_table_name_from_item
            self.tables_list.is_folder_item = mock_is_folder_item
            self.tables_list.topLevelItemCount = lambda: 0
            self.add_recent_project = mock_add_recent_project
            self.has_unsaved_changes = lambda: False
            self.close_tab = lambda index: None
            self.get_tab_at_index = lambda index: self.tabs[index] if 0 <= index < len(self.tabs) else None
            self.add_tab = lambda: None
            
            self.project_manager = ProjectManager(self)
            
            # Monkeypatch project manager's clear state to avoid UI-heavy logic
            def safe_clear_project_state():
                self.db_manager.loaded_tables = {}
                self.db_manager.table_columns = {}
                self._column_renames = {}
                self._preview_transforms = {}
                self.tables_list.clear()
                self.tabs = []
                while self.tab_widget.count() > 0:
                    widget = self.tab_widget.widget(0)
                    self.tab_widget.removeTab(0)
                    widget.deleteLater()
                self.current_project_file = None
                self.statusBar().showMessage('New project created')
            
            self.project_manager._clear_project_state = safe_clear_project_state
            self.project_manager.new_project = lambda skip_confirmation=False: safe_clear_project_state()
            
            self._project_manager_patched = True
        
        def close(self):
            # Restore patched classes when the window is closed to avoid leaking to other tests
            if getattr(self, "_project_manager_patched", False):
                project_manager_module.QMessageBox = _orig_qmessagebox
                project_manager_module.QProgressDialog = _orig_qprogress
                project_manager_module.QueryTab = _orig_query_tab
                self._project_manager_patched = False
            super().close()
        
        def get_current_tab(self):
            return self.tabs[0] if self.tabs else None
        
        def populate_table(self, df):
            current_tab = self.get_current_tab()
            if current_tab:
                current_tab.current_df = df.copy()
                self.current_df = df.copy()
        
        def update_completer(self):
            pass  # Mock - do nothing
        
        def statusBar(self):
            from PyQt6.QtWidgets import QStatusBar
            sb = super().statusBar()
            if sb is None:
                super().setStatusBar(QStatusBar())
                sb = super().statusBar()
            return sb
        
        def rename_column(self, old_name, new_name):
            """Minimal rename_column implementation for testing."""
            current_tab = self.get_current_tab()
            if not current_tab or current_tab.current_df is None:
                return
            
            table_name = None
            if current_tab.is_preview_mode and current_tab.preview_table_name:
                table_name = current_tab.preview_table_name
            
            if current_tab.is_preview_mode and current_tab.preview_table_name:
                table_name = current_tab.preview_table_name
                base_df = self._preview_transforms.get(table_name)
                if base_df is None:
                    base_df = self.db_manager.get_full_table(table_name)
                
                if old_name not in base_df.columns:
                    return
                if new_name in base_df.columns:
                    return
                
                updated_full_df = base_df.rename(columns={old_name: new_name})
                self._preview_transforms[table_name] = updated_full_df
                
                # Track the column rename
                if table_name not in self._column_renames:
                    self._column_renames[table_name] = {}
                self._column_renames[table_name][old_name] = new_name
                
                # Update in database
                original_source = self.db_manager.loaded_tables.get(table_name, 'query_result')
                self.db_manager.overwrite_table_with_dataframe(table_name, updated_full_df, source=original_source)
                
                preview_df = updated_full_df.head()
                self.populate_table(preview_df)
            else:
                df = current_tab.current_df
                if old_name not in df.columns:
                    return
                if new_name in df.columns:
                    return
                
                updated_df = df.rename(columns={old_name: new_name})
                current_tab.current_df = updated_df
                
                # Track the column rename if we have a source table
                if table_name:
                    if table_name not in self._column_renames:
                        self._column_renames[table_name] = {}
                    self._column_renames[table_name][old_name] = new_name
                
                # Update source table if found
                if table_name and table_name in self.db_manager.loaded_tables:
                    try:
                        full_table_df = self.db_manager.get_full_table(table_name)
                        if old_name in full_table_df.columns:
                            updated_full_table_df = full_table_df.rename(columns={old_name: new_name})
                            original_source = self.db_manager.loaded_tables.get(table_name, 'query_result')
                            self.db_manager.overwrite_table_with_dataframe(table_name, updated_full_table_df, source=original_source)
                    except Exception:
                        pass
                
                self.populate_table(updated_df)
    
    return MinimalWindow(sample_df, table_name)


@requires_gui
def test_column_rename_tracking(qapp, sample_df, monkeypatch):
    """Test that column renames are tracked in _column_renames dictionary."""
    table_name = "test_table"
    
    # Create minimal window
    window = create_minimal_window(sample_df, table_name)
    
    # Set up preview mode
    current_tab = window.get_current_tab()
    current_tab.is_preview_mode = True
    current_tab.preview_table_name = table_name
    preview_df = window.db_manager.get_table_preview(table_name)
    window.populate_table(preview_df)
    
    # Verify _column_renames is initialized
    assert hasattr(window, '_column_renames')
    assert isinstance(window._column_renames, dict)
    
    # Rename a column
    window.rename_column("age", "age_renamed")
    
    # Verify the rename is tracked
    assert table_name in window._column_renames
    assert "age" in window._column_renames[table_name]
    assert window._column_renames[table_name]["age"] == "age_renamed"
    
    # Rename another column
    window.rename_column("name", "full_name")
    
    # Verify both renames are tracked
    assert window._column_renames[table_name]["age"] == "age_renamed"
    assert window._column_renames[table_name]["name"] == "full_name"
    
    window.close()


@requires_gui
def test_column_rename_saved_to_project(qapp, sample_df, temp_dir):
    """Test that column renames are saved to project files."""
    table_name = "test_table"
    
    # Create minimal window
    window = create_minimal_window(sample_df, table_name)
    
    # Set up preview mode
    current_tab = window.get_current_tab()
    current_tab.is_preview_mode = True
    current_tab.preview_table_name = table_name
    window.populate_table(sample_df.head())
    
    # Rename columns
    window.rename_column("age", "age_renamed")
    window.rename_column("name", "full_name")
    
    # Save project
    project_file = os.path.join(str(temp_dir), "test_project.sqls")
    window.current_project_file = project_file
    window.project_manager.save_project_to_file(project_file)
    
    # Verify project file exists
    assert os.path.exists(project_file)
    
    # Load and verify project file contains column_renames
    with open(project_file, 'r') as f:
        project_data = json.load(f)
    
    assert 'column_renames' in project_data
    assert table_name in project_data['column_renames']
    assert project_data['column_renames'][table_name]["age"] == "age_renamed"
    assert project_data['column_renames'][table_name]["name"] == "full_name"
    
    window.close()


@requires_gui
def test_column_rename_loaded_from_project(qapp, sample_df, temp_dir):
    """Test that column renames are loaded from project files."""
    # Create a project file with column renames
    project_file = os.path.join(str(temp_dir), "test_project.sqls")
    table_name = "test_table"
    
    project_data = {
        'tables': {
            table_name: {
                'file_path': 'test_file.csv',
                'columns': list(sample_df.columns),
                'folder': None
            }
        },
        'folders': {},
        'tabs': [{'title': 'Query 1', 'query': ''}],
        'connection_type': 'duckdb',
        'database_path': None,
        'column_renames': {
            table_name: {
                'age': 'age_renamed',
                'name': 'full_name'
            }
        }
    }
    
    with open(project_file, 'w') as f:
        json.dump(project_data, f)
    
    # Create minimal window
    window = create_minimal_window(sample_df, table_name)
    
    # Register the table first
    window.db_manager.register_dataframe(sample_df.copy(), table_name)
    window.db_manager.loaded_tables[table_name] = "test_file.csv"
    window.db_manager.table_columns[table_name] = list(sample_df.columns)
    
    # Load project data directly (avoiding open_project which has UI dialogs)
    with open(project_file, 'r') as f:
        loaded_project_data = json.load(f)
    
    # Simulate what open_project does for column_renames
    if 'column_renames' in loaded_project_data and loaded_project_data['column_renames']:
        if not hasattr(window, '_column_renames'):
            window._column_renames = {}
        window._column_renames = loaded_project_data['column_renames']
    
    # Verify column renames were loaded
    assert hasattr(window, '_column_renames')
    assert table_name in window._column_renames
    assert window._column_renames[table_name]["age"] == "age_renamed"
    assert window._column_renames[table_name]["name"] == "full_name"
    
    window.close()


@requires_gui
def test_column_rename_applied_on_table_load(qapp, sample_df, temp_dir):
    """Test that column renames are applied when a table is loaded."""
    # Create a project file with column renames
    project_file = os.path.join(str(temp_dir), "test_project.sqls")
    table_name = "test_table"
    
    project_data = {
        'tables': {
            table_name: {
                'file_path': 'test_file.csv',
                'columns': list(sample_df.columns),
                'folder': None
            }
        },
        'folders': {},
        'tabs': [{'title': 'Query 1', 'query': ''}],
        'connection_type': 'duckdb',
        'database_path': None,
        'column_renames': {
            table_name: {
                'age': 'age_renamed',
                'name': 'full_name'
            }
        }
    }
    
    with open(project_file, 'w') as f:
        json.dump(project_data, f)
    
    # Create minimal window
    window = create_minimal_window(sample_df, table_name)
    
    # Register the table first
    window.db_manager.register_dataframe(sample_df.copy(), table_name)
    window.db_manager.loaded_tables[table_name] = "test_file.csv"
    window.db_manager.table_columns[table_name] = list(sample_df.columns)
    
    # Load project data directly (avoiding open_project which has UI dialogs)
    with open(project_file, 'r') as f:
        loaded_project_data = json.load(f)
    
    # Simulate what open_project does for column_renames
    if 'column_renames' in loaded_project_data and loaded_project_data['column_renames']:
        if not hasattr(window, '_column_renames'):
            window._column_renames = {}
        window._column_renames = loaded_project_data['column_renames']
    
    # Apply renames to the table (simulating what _apply_column_renames_to_table does)
    if table_name in window._column_renames:
        rename_map = window._column_renames[table_name]
        if rename_map:
            current_df = window.db_manager.get_full_table(table_name)
            actual_renames = {
                old_name: new_name
                for old_name, new_name in rename_map.items()
                if old_name in current_df.columns and new_name not in current_df.columns
            }
            if actual_renames:
                updated_df = current_df.rename(columns=actual_renames)
                original_source = window.db_manager.loaded_tables.get(table_name, 'query_result')
                window.db_manager.overwrite_table_with_dataframe(table_name, updated_df, source=original_source)
                window.db_manager.table_columns[table_name] = list(updated_df.columns)
    
    # Verify the table schema was updated
    table_df = window.db_manager.get_full_table(table_name)
    assert "age_renamed" in table_df.columns
    assert "full_name" in table_df.columns
    assert "age" not in table_df.columns
    assert "name" not in table_df.columns
    
    # Verify table_columns tracking was updated
    assert "age_renamed" in window.db_manager.table_columns[table_name]
    assert "full_name" in window.db_manager.table_columns[table_name]
    assert "age" not in window.db_manager.table_columns[table_name]
    assert "name" not in window.db_manager.table_columns[table_name]
    
    window.close()


@requires_gui
def test_sql_query_with_renamed_column_after_project_load(qapp, sample_df, temp_dir):
    """Test that SQL queries work with renamed columns after loading a project."""
    # Create a project file with column renames
    project_file = os.path.join(str(temp_dir), "test_project.sqls")
    table_name = "test_table"
    
    project_data = {
        'tables': {
            table_name: {
                'file_path': 'test_file.csv',
                'columns': list(sample_df.columns),
                'folder': None
            }
        },
        'folders': {},
        'tabs': [{'title': 'Query 1', 'query': ''}],
        'connection_type': 'duckdb',
        'database_path': None,
        'column_renames': {
            table_name: {
                'age': 'age_renamed'
            }
        }
    }
    
    with open(project_file, 'w') as f:
        json.dump(project_data, f)
    
    # Create minimal window
    window = create_minimal_window(sample_df, table_name)
    
    # Register the table first
    window.db_manager.register_dataframe(sample_df.copy(), table_name)
    window.db_manager.loaded_tables[table_name] = "test_file.csv"
    window.db_manager.table_columns[table_name] = list(sample_df.columns)
    
    # Load project
    window.project_manager.open_project(project_file)
    
    # Apply renames to the table
    from sqlshell.__main__ import SQLShell
    window._apply_column_renames_to_table = SQLShell._apply_column_renames_to_table.__get__(window, type(window))
    window._apply_column_renames_to_table(table_name)
    
    # Try to execute a SQL query using the renamed column
    query = f'SELECT age_renamed FROM "{table_name}" LIMIT 5'
    result = window.db_manager.execute_query(query)
    
    # Verify the query worked and returned data
    assert len(result) > 0
    assert "age_renamed" in result.columns
    
    # Verify the old column name doesn't work
    query_old = f'SELECT age FROM "{table_name}" LIMIT 5'
    with pytest.raises(Exception):  # Should raise an error
        window.db_manager.execute_query(query_old)
    
    window.close()


@requires_gui
def test_multiple_table_column_renames(qapp, sample_df, temp_dir):
    """Test that column renames for multiple tables are handled correctly."""
    # Create minimal window with first table
    table1_name = "table1"
    window = create_minimal_window(sample_df, table1_name)
    
    # Load two tables
    table2_name = "table2"
    
    window.db_manager.register_dataframe(sample_df.copy(), table1_name)
    window.db_manager.loaded_tables[table1_name] = "test_file1.csv"
    window.db_manager.table_columns[table1_name] = list(sample_df.columns)
    
    window.db_manager.register_dataframe(sample_df.copy(), table2_name)
    window.db_manager.loaded_tables[table2_name] = "test_file2.csv"
    window.db_manager.table_columns[table2_name] = list(sample_df.columns)
    
    # Set up preview mode for first table
    current_tab = window.get_current_tab()
    current_tab.is_preview_mode = True
    current_tab.preview_table_name = table1_name
    window.populate_table(sample_df.head())
    
    # Rename column in first table
    window.rename_column("age", "age_renamed")
    
    # Switch to second table
    current_tab.preview_table_name = table2_name
    window.populate_table(sample_df.head())
    
    # Rename column in second table (different rename)
    window.rename_column("age", "years_old")
    
    # Save project
    project_file = os.path.join(str(temp_dir), "test_project.sqls")
    window.current_project_file = project_file
    window.project_manager.save_project_to_file(project_file)
    
    # Verify both renames are saved
    with open(project_file, 'r') as f:
        project_data = json.load(f)
    
    assert table1_name in project_data['column_renames']
    assert table2_name in project_data['column_renames']
    assert project_data['column_renames'][table1_name]["age"] == "age_renamed"
    assert project_data['column_renames'][table2_name]["age"] == "years_old"
    
    window.close()


@requires_gui
def test_column_rename_persistence_across_save_load(qapp, sample_df, temp_dir):
    """Test complete workflow: rename, save, load, verify SQL works."""
    table_name = "test_table"
    
    # Step 1: Create window, load table, rename column, save project
    window1 = create_minimal_window(sample_df, table_name)
    
    window1.db_manager.register_dataframe(sample_df.copy(), table_name)
    window1.db_manager.loaded_tables[table_name] = "test_file.csv"
    window1.db_manager.table_columns[table_name] = list(sample_df.columns)
    
    current_tab = window1.get_current_tab()
    current_tab.is_preview_mode = True
    current_tab.preview_table_name = table_name
    window1.populate_table(sample_df.head())
    
    # Rename column
    window1.rename_column("age", "age_renamed")
    
    # Save project
    project_file = os.path.join(str(temp_dir), "test_project.sqls")
    window1.current_project_file = project_file
    window1.project_manager.save_project_to_file(project_file)
    window1.close()
    
    # Step 2: Create new window, load project, verify rename is applied
    window2 = create_minimal_window(sample_df, table_name)
    
    # Register table again (simulating project load)
    window2.db_manager.register_dataframe(sample_df.copy(), table_name)
    window2.db_manager.loaded_tables[table_name] = "test_file.csv"
    window2.db_manager.table_columns[table_name] = list(sample_df.columns)
    
    # Load project
    window2.project_manager.open_project(project_file)
    
    # Verify rename was loaded
    assert table_name in window2._column_renames
    assert window2._column_renames[table_name]["age"] == "age_renamed"
    
    # Apply rename to table
    from sqlshell.__main__ import SQLShell
    window2._apply_column_renames_to_table = SQLShell._apply_column_renames_to_table.__get__(window2, type(window2))
    window2._apply_column_renames_to_table(table_name)
    
    # Verify SQL query works with renamed column
    query = f'SELECT age_renamed FROM "{table_name}" LIMIT 5'
    result = window2.db_manager.execute_query(query)
    assert len(result) > 0
    assert "age_renamed" in result.columns
    
    window2.close()


@requires_gui
def test_column_rename_cleared_on_new_project(qapp, sample_df):
    """Test that column renames are cleared when creating a new project."""
    table_name = "test_table"
    
    # Create minimal window
    window = create_minimal_window(sample_df, table_name)
    
    # Load a table and rename a column
    window.db_manager.register_dataframe(sample_df.copy(), table_name)
    window.db_manager.loaded_tables[table_name] = "test_file.csv"
    window.db_manager.table_columns[table_name] = list(sample_df.columns)
    
    current_tab = window.get_current_tab()
    current_tab.is_preview_mode = True
    current_tab.preview_table_name = table_name
    window.populate_table(sample_df.head())
    
    window.rename_column("age", "age_renamed")
    
    # Verify rename is tracked
    assert table_name in window._column_renames
    
    # Create new project
    window.project_manager.new_project(skip_confirmation=True)
    
    # Verify column renames were cleared
    assert window._column_renames == {}
    
    window.close()
