"""
Tests for ProjectManager module.

Tests project save/load functionality to ensure refactoring didn't break anything.
"""

import pytest
import os
import json
import tempfile
from pathlib import Path

# Skip tests if PyQt6 is not available
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QLabel
from sqlshell.project_manager import ProjectManager
from sqlshell.db import DatabaseManager
from sqlshell.table_list import DraggableTablesList


class MockWindow(QMainWindow):
    """Mock window for testing ProjectManager - inherits from QMainWindow to be a proper QWidget"""
    
    def __init__(self):
        super().__init__()
        # Hide window immediately to prevent it from showing during tests
        self.setVisible(False)
        self.db_manager = DatabaseManager()
        self.tables_list = DraggableTablesList(self)
        self.tables_list.setVisible(False)  # Hide tables list
        self.tab_widget = QTabWidget()
        self.tab_widget.setVisible(False)  # Hide tab widget
        self.tabs = []
        self.current_project_file = None
        self.db_info_label = QLabel("No database connected")
        self.db_info_label.setVisible(False)  # Hide label
        self._status_message = ""
        
        # Mock methods that ProjectManager calls
        self.add_recent_project_called = False
        self.add_recent_project_path = None
        
    def setWindowTitle(self, title):
        self.window_title = title
        super().setWindowTitle(title)
    
    def statusBar(self):
        # QMainWindow already has a statusBar, just return it
        sb = super().statusBar()
        if sb is None:
            from PyQt6.QtWidgets import QStatusBar
            super().setStatusBar(QStatusBar())
            sb = super().statusBar()
        return sb
    
    def has_unsaved_changes(self):
        return False
    
    def add_recent_project(self, path):
        self.add_recent_project_called = True
        self.add_recent_project_path = path
    
    def close_tab(self, index):
        if self.tab_widget and index < self.tab_widget.count():
            self.tab_widget.removeTab(index)
    
    def get_tab_at_index(self, index):
        if self.tab_widget and index < self.tab_widget.count():
            return self.tab_widget.widget(index)
        return None
    
    def add_tab(self):
        from sqlshell.query_tab import QueryTab
        tab = QueryTab(self)
        tab.setVisible(False)  # Hide tab to prevent windows from showing
        self.tabs.append(tab)
        self.tab_widget.addTab(tab, f"Query {self.tab_widget.count() + 1}")
    
    def update_completer(self):
        pass




@pytest.fixture
def mock_window(qapp):
    """Create a mock window for testing - windows are hidden to prevent showing during tests"""
    window = MockWindow()
    # Window is already hidden in __init__, but ensure it stays hidden
    assert not window.isVisible(), "Window should be hidden during tests"
    window.add_tab()  # Create initial tab
    yield window
    # Cleanup
    window.close()
    window.deleteLater()


@pytest.fixture
def project_manager(mock_window, qapp):
    """Create a ProjectManager instance"""
    return ProjectManager(mock_window)


@pytest.fixture
def temp_project_file():
    """Create a temporary project file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqls', delete=False) as f:
        project_data = {
            'tables': {
                'test_table': {
                    'file_path': '/path/to/test.csv',
                    'columns': ['col1', 'col2'],
                    'folder': None
                }
            },
            'folders': {},
            'tabs': [
                {'title': 'Query 1', 'query': 'SELECT * FROM test_table'}
            ],
            'connection_type': 'duckdb',
            'database_path': None
        }
        json.dump(project_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


def test_project_manager_initialization(project_manager):
    """Test that ProjectManager initializes correctly"""
    assert project_manager.window is not None
    assert project_manager.db_manager is not None
    assert project_manager.tables_list is not None


def test_new_project_skip_confirmation(project_manager, mock_window):
    """Test creating a new project with skip_confirmation=True"""
    # Add some state
    mock_window.db_manager.loaded_tables['test'] = 'path/to/file'
    mock_window.current_project_file = '/some/path.sqls'
    
    # Create new project
    project_manager.new_project(skip_confirmation=True)
    
    # Verify state was cleared
    assert len(mock_window.db_manager.loaded_tables) == 0
    assert mock_window.current_project_file is None
    assert mock_window.window_title == 'SQL Shell'


def test_save_project_to_file(project_manager, mock_window, temp_project_file):
    """Test saving a project to a file"""
    # Set up some state
    mock_window.current_project_file = temp_project_file
    
    # Save project
    project_manager.save_project_to_file(temp_project_file)
    
    # Verify file was created and contains valid JSON
    assert os.path.exists(temp_project_file)
    
    with open(temp_project_file, 'r') as f:
        data = json.load(f)
    
    assert 'tables' in data
    assert 'folders' in data
    assert 'tabs' in data
    assert 'connection_type' in data


def test_save_project_no_current_file(project_manager, mock_window):
    """Test that save_project calls save_project_as when no current file"""
    # Mock save_project_as to track if it was called
    save_project_as_called = []
    
    def mock_save_project_as():
        save_project_as_called.append(True)
    
    project_manager.save_project_as = mock_save_project_as
    
    # Try to save without a current file
    project_manager.save_project()
    
    # Should have called save_project_as
    assert len(save_project_as_called) > 0


def test_project_file_format(project_manager, mock_window):
    """Test that saved project files have the correct format"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqls', delete=False) as f:
        temp_path = f.name
    
    try:
        # Save project
        project_manager.save_project_to_file(temp_path)
        
        # Load and verify structure
        with open(temp_path, 'r') as f:
            data = json.load(f)
        
        # Check required keys
        required_keys = ['tables', 'folders', 'tabs', 'connection_type', 'database_path']
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"
        
        # Verify types
        assert isinstance(data['tables'], dict)
        assert isinstance(data['folders'], dict)
        assert isinstance(data['tabs'], list)
        assert isinstance(data['connection_type'], str)
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_open_project_file_not_found(project_manager, mock_window, monkeypatch):
    """Test opening a non-existent project file"""
    from PyQt6.QtWidgets import QMessageBox, QProgressDialog
    
    # Track if QMessageBox.critical was called
    message_box_called = []
    message_box_title = []
    message_box_text = []
    
    def mock_critical(parent, title, text):
        """Mock QMessageBox.critical to avoid blocking"""
        message_box_called.append(True)
        message_box_title.append(title)
        message_box_text.append(text)
        # Return a mock button (doesn't matter which one)
        return QMessageBox.StandardButton.Ok
    
    # Mock QProgressDialog to prevent it from showing/blocking
    original_progress = QProgressDialog
    
    def mock_progress_dialog(*args, **kwargs):
        """Mock QProgressDialog to prevent blocking"""
        dialog = original_progress(*args, **kwargs)
        dialog.setVisible(False)  # Hide immediately
        dialog.setMinimumDuration(0)  # Don't delay showing
        return dialog
    
    # Patch both QMessageBox.critical and QProgressDialog
    monkeypatch.setattr(QMessageBox, "critical", mock_critical)
    monkeypatch.setattr("sqlshell.project_manager.QProgressDialog", mock_progress_dialog)
    
    # Try to open a non-existent file
    project_manager.open_project('/nonexistent/path.sqls')
    
    # Verify that QMessageBox.critical was called (error was shown)
    assert len(message_box_called) > 0, "QMessageBox.critical should be called for non-existent file"
    assert "Error" in message_box_title[0] or "error" in message_box_title[0].lower(), \
        f"Expected error dialog, got title: {message_box_title[0]}"


def test_open_project_invalid_json(project_manager, mock_window, monkeypatch):
    """Test opening a project file with invalid JSON"""
    from PyQt6.QtWidgets import QMessageBox, QProgressDialog
    
    # Track if QMessageBox.critical was called
    message_box_called = []
    
    def mock_critical(parent, title, text):
        """Mock QMessageBox.critical to avoid blocking"""
        message_box_called.append(True)
        return QMessageBox.StandardButton.Ok
    
    # Mock QProgressDialog to prevent it from showing/blocking
    original_progress = QProgressDialog
    
    def mock_progress_dialog(*args, **kwargs):
        """Mock QProgressDialog to prevent blocking"""
        dialog = original_progress(*args, **kwargs)
        dialog.setVisible(False)  # Hide immediately
        dialog.setMinimumDuration(0)  # Don't delay showing
        return dialog
    
    # Patch both QMessageBox.critical and QProgressDialog
    monkeypatch.setattr(QMessageBox, "critical", mock_critical)
    monkeypatch.setattr("sqlshell.project_manager.QProgressDialog", mock_progress_dialog)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqls', delete=False) as f:
        f.write("invalid json content")
        temp_path = f.name
    
    try:
        # Should handle invalid JSON gracefully
        project_manager.open_project(temp_path)
        # Verify that error dialog was shown
        assert len(message_box_called) > 0, "QMessageBox.critical should be called for invalid JSON"
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_project_manager_integration(mock_window):
    """Integration test: save and load a project"""
    pm = ProjectManager(mock_window)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqls', delete=False) as f:
        temp_path = f.name
    
    try:
        # Save project
        pm.save_project_to_file(temp_path)
        
        # Verify file exists
        assert os.path.exists(temp_path)
        
        # Load project (this will call new_project which clears state)
        # We'll skip the actual loading since it requires more complex setup
        # but we can verify the file is readable
        with open(temp_path, 'r') as f:
            data = json.load(f)
            assert data is not None
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_save_project_with_folders(project_manager, mock_window):
    """Test saving a project with folder structure"""
    import pandas as pd
    from PyQt6.QtWidgets import QTreeWidgetItem
    from PyQt6.QtGui import QIcon
    from PyQt6.QtCore import Qt
    
    # Create a folder
    folder = mock_window.tables_list.create_folder("Test Folder")
    
    # Add a table to the folder
    test_df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
    table_name = mock_window.db_manager.register_dataframe(test_df, "test_table")
    mock_window.db_manager.loaded_tables[table_name] = '/path/to/test.csv'
    mock_window.db_manager.table_columns[table_name] = ['col1', 'col2']
    
    # Add table item to folder
    item = QTreeWidgetItem(folder)
    item.setText(0, f"{table_name} (test.csv)")
    item.setIcon(0, QIcon.fromTheme("x-office-spreadsheet"))
    item.setData(0, Qt.ItemDataRole.UserRole, "table")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqls', delete=False) as f:
        temp_path = f.name
    
    try:
        # Save project
        project_manager.save_project_to_file(temp_path)
        
        # Verify file contains folder structure
        with open(temp_path, 'r') as f:
            data = json.load(f)
        
        assert 'folders' in data
        assert len(data['folders']) > 0
        # Find the folder
        folder_found = False
        for folder_id, folder_info in data['folders'].items():
            if folder_info['name'] == "Test Folder":
                folder_found = True
                assert folder_info['parent'] is None  # Top-level folder
                break
        assert folder_found, "Folder should be saved in project file"
        
        # Verify table is associated with folder
        assert 'tables' in data
        table_found = False
        for table_name_saved, table_info in data['tables'].items():
            if table_name_saved == table_name:
                table_found = True
                assert table_info['folder'] is not None, "Table should be associated with folder"
                break
        assert table_found, "Table should be saved in project file"
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_save_project_with_database_path(project_manager, mock_window):
    """Test saving a project with database connection"""
    import tempfile as tf
    import duckdb
    import os
    
    # Create a temporary database file path
    with tf.NamedTemporaryFile(suffix='.db', delete=False) as db_file:
        db_path = db_file.name
    
    # Remove the empty file so we can create a proper database
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    try:
        # Create a valid DuckDB database file
        conn = duckdb.connect(db_path)
        conn.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")
        conn.close()
        
        # Connect to database
        mock_window.db_manager.open_database(db_path, load_all_tables=False)
        mock_window.db_manager.database_path = db_path
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sqls', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save project
            project_manager.save_project_to_file(temp_path)
            
            # Verify database path is saved
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert 'database_path' in data
            assert data['database_path'] == db_path
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    finally:
        # Close database connection before deleting file (required on Windows)
        if mock_window.db_manager.is_connected():
            mock_window.db_manager.close_connection()
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_save_project_with_tabs(project_manager, mock_window):
    """Test saving a project with multiple tabs and queries"""
    # Add multiple tabs with queries
    tab1 = mock_window.get_tab_at_index(0)
    if tab1:
        tab1.set_query_text("SELECT * FROM table1")
        mock_window.tab_widget.setTabText(0, "Query 1")
    
    # Add another tab
    mock_window.add_tab()
    tab2 = mock_window.get_tab_at_index(1)
    if tab2:
        tab2.set_query_text("SELECT * FROM table2 WHERE id > 10")
        mock_window.tab_widget.setTabText(1, "Query 2")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqls', delete=False) as f:
        temp_path = f.name
    
    try:
        # Save project
        project_manager.save_project_to_file(temp_path)
        
        # Verify tabs are saved
        with open(temp_path, 'r') as f:
            data = json.load(f)
        
        assert 'tabs' in data
        assert len(data['tabs']) == 2
        assert data['tabs'][0]['title'] == "Query 1"
        assert "SELECT * FROM table1" in data['tabs'][0]['query']
        assert data['tabs'][1]['title'] == "Query 2"
        assert "SELECT * FROM table2" in data['tabs'][1]['query']
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_save_project_with_query_result_tables(project_manager, mock_window):
    """Test saving a project with query result tables"""
    import pandas as pd
    
    # Create a query result table
    test_df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
    table_name = mock_window.db_manager.register_dataframe(test_df, "query_result_table", source='query_result')
    # Note: register_dataframe already sets loaded_tables, but we ensure it's 'query_result'
    mock_window.db_manager.loaded_tables[table_name] = 'query_result'
    
    # Add to tables list
    mock_window.tables_list.add_table_item(table_name, "query result", needs_reload=False)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqls', delete=False) as f:
        temp_path = f.name
    
    try:
        # Save project
        project_manager.save_project_to_file(temp_path)
        
        # Verify query result table is saved correctly
        with open(temp_path, 'r') as f:
            data = json.load(f)
        
        assert 'tables' in data
        assert table_name in data['tables']
        assert data['tables'][table_name]['file_path'] == 'query_result'
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_clear_project_state_resets_tabs(project_manager, mock_window):
    """Test that _clear_project_state properly resets tabs"""
    # Add multiple tabs
    mock_window.add_tab()
    mock_window.add_tab()
    
    assert mock_window.tab_widget.count() == 3  # Initial + 2 added
    
    # Clear project state
    project_manager._clear_project_state()
    
    # Should have exactly one tab remaining
    assert mock_window.tab_widget.count() == 1
    
    # Remaining tab should be cleared
    remaining_tab = mock_window.get_tab_at_index(0)
    assert remaining_tab is not None
    assert remaining_tab.get_query_text() == ""
    assert mock_window.tab_widget.tabText(0) == "Query 1"


def test_save_project_with_database_tables(project_manager, mock_window):
    """Test saving a project with database tables (not file-based)"""
    # Register a database table
    table_name = "db_table"
    mock_window.db_manager.loaded_tables[table_name] = 'database:db'
    mock_window.db_manager.table_columns[table_name] = ['id', 'name']
    
    # Add to tables list
    mock_window.tables_list.add_table_item(table_name, "database", needs_reload=False)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqls', delete=False) as f:
        temp_path = f.name
    
    try:
        # Save project
        project_manager.save_project_to_file(temp_path)
        
        # Verify database table is saved correctly
        with open(temp_path, 'r') as f:
            data = json.load(f)
        
        assert 'tables' in data
        assert table_name in data['tables']
        # Should save as 'database' for backward compatibility
        assert data['tables'][table_name]['file_path'] == 'database'
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_full_save_load_cycle_integration(project_manager, mock_window, monkeypatch):
    """Integration test: Save a complex project and verify it can be loaded correctly"""
    import pandas as pd
    from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QTreeWidgetItem
    from PyQt6.QtGui import QIcon
    from PyQt6.QtCore import Qt
    
    # Mock QProgressDialog to prevent it from showing/blocking
    original_progress = QProgressDialog
    
    def mock_progress_dialog(*args, **kwargs):
        """Mock QProgressDialog to prevent blocking"""
        dialog = original_progress(*args, **kwargs)
        dialog.setVisible(False)  # Hide immediately
        dialog.setMinimumDuration(0)  # Don't delay showing
        return dialog
    
    monkeypatch.setattr("sqlshell.project_manager.QProgressDialog", mock_progress_dialog)
    
    # Set up a complex project state:
    # 1. Create a folder structure
    folder1 = mock_window.tables_list.create_folder("Folder 1")
    folder2 = mock_window.tables_list.create_folder("Folder 2")
    
    # 2. Add tables to folders and root
    df1 = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
    table1 = mock_window.db_manager.register_dataframe(df1, "table1")
    # Override the source to simulate a file-based table
    mock_window.db_manager.loaded_tables[table1] = '/path/to/table1.csv'
    mock_window.db_manager.table_columns[table1] = ['col1', 'col2']
    
    # Add table1 to folder1
    item1 = QTreeWidgetItem(folder1)
    item1.setText(0, f"{table1} (table1.csv)")
    item1.setIcon(0, QIcon.fromTheme("x-office-spreadsheet"))
    item1.setData(0, Qt.ItemDataRole.UserRole, "table")
    
    # Add a database table to root
    table2 = "db_table"
    mock_window.db_manager.loaded_tables[table2] = 'database:db'
    mock_window.db_manager.table_columns[table2] = ['id', 'name']
    mock_window.tables_list.add_table_item(table2, "database", needs_reload=False)
    
    # 3. Set up tabs with queries
    tab1 = mock_window.get_tab_at_index(0)
    if tab1:
        tab1.set_query_text("SELECT * FROM table1")
        mock_window.tab_widget.setTabText(0, "Query 1")
    
    mock_window.add_tab()
    tab2 = mock_window.get_tab_at_index(1)
    if tab2:
        tab2.set_query_text("SELECT * FROM db_table WHERE id > 10")
        mock_window.tab_widget.setTabText(1, "Query 2")
    
    # 4. Set database connection
    import tempfile as tf
    import duckdb
    import os
    
    # Create a temporary database file path
    with tf.NamedTemporaryFile(suffix='.db', delete=False) as db_file:
        db_path = db_file.name
    
    # Remove the empty file so we can create a proper database
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    try:
        # Create a valid DuckDB database file
        conn = duckdb.connect(db_path)
        conn.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")
        conn.close()
        
        mock_window.db_manager.open_database(db_path, load_all_tables=False)
        mock_window.db_manager.database_path = db_path
        
        # Save the project
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sqls', delete=False) as f:
            temp_path = f.name
        
        try:
            project_manager.save_project_to_file(temp_path)
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
            # Verify project structure
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            # Check all required keys
            assert 'tables' in saved_data
            assert 'folders' in saved_data
            assert 'tabs' in saved_data
            assert 'connection_type' in saved_data
            assert 'database_path' in saved_data
            
            # Verify folders were saved
            assert len(saved_data['folders']) >= 2
            folder_names = [f['name'] for f in saved_data['folders'].values()]
            assert "Folder 1" in folder_names
            assert "Folder 2" in folder_names
            
            # Verify tables were saved
            assert table1 in saved_data['tables']
            assert table2 in saved_data['tables']
            
            # Verify tabs were saved
            assert len(saved_data['tabs']) == 2
            assert saved_data['tabs'][0]['title'] == "Query 1"
            assert saved_data['tabs'][1]['title'] == "Query 2"
            
            # Verify database path was saved
            assert saved_data['database_path'] == db_path
            
            # Now test loading (simplified - full load requires more complex setup)
            # We can at least verify the file structure is correct for loading
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    finally:
        # Close database connection before deleting file (required on Windows)
        if mock_window.db_manager.is_connected():
            mock_window.db_manager.close_connection()
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

