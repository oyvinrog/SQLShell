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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

