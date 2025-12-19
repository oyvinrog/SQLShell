"""
Project Management Module

Handles saving and loading SQLShell projects, including:
- Project file serialization/deserialization
- Table and folder structure management
- Tab state management
- Database connection state
"""

import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (QFileDialog, QMessageBox, QProgressDialog, 
                             QTreeWidgetItem, QApplication)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon

from sqlshell.query_tab import QueryTab


class ProjectManager:
    """
    Manages project save/load operations for SQLShell.
    
    This class handles the serialization and deserialization of project state,
    including tables, folders, tabs, and database connections.
    """
    
    def __init__(self, window):
        """
        Initialize the ProjectManager.
        
        Args:
            window: The SQLShell main window instance
        """
        self.window = window
        self.db_manager = window.db_manager
        self.tables_list = window.tables_list
        self.tab_widget = window.tab_widget
        self.tabs = window.tabs
    
    def new_project(self, skip_confirmation=False):
        """Create a new project by clearing current state"""
        if self.db_manager.is_connected() and not skip_confirmation:
            reply = QMessageBox.question(self.window, 'New Project',
                                      'Are you sure you want to start a new project? All unsaved changes will be lost.',
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._clear_project_state()
        elif skip_confirmation:
            # Skip confirmation and just clear everything
            self._clear_project_state()
    
    def _clear_project_state(self):
        """Internal method to clear all project state"""
        if self.db_manager.is_connected():
            self.db_manager.close_connection()
        
        # Clear all database tracking
        self.db_manager.loaded_tables = {}
        self.db_manager.table_columns = {}
        
        # Clear column renames and preview transforms
        if hasattr(self.window, '_column_renames'):
            self.window._column_renames = {}
        if hasattr(self.window, '_preview_transforms'):
            self.window._preview_transforms = {}
        
        # Reset state
        self.tables_list.clear()
        
        # Clear all tabs except one
        while self.tab_widget.count() > 1:
            self.window.close_tab(1)  # Always close tab at index 1 to keep at least one tab
        
        # Clear the remaining tab
        first_tab = self.window.get_tab_at_index(0)
        if first_tab:
            first_tab.set_query_text("")
            first_tab.results_table.setRowCount(0)
            first_tab.results_table.setColumnCount(0)
            first_tab.row_count_label.setText("")
            first_tab.results_title.setText("RESULTS")
            # Reset tab title to default
            self.tab_widget.setTabText(0, "Query 1")
        
        self.window.current_project_file = None
        self.window.setWindowTitle('SQL Shell')
        self.window.db_info_label.setText("No database connected")
        self.window.statusBar().showMessage('New project created')
    
    def save_project(self):
        """Save the current project"""
        if not self.window.current_project_file:
            self.save_project_as()
            return
            
        self.save_project_to_file(self.window.current_project_file)
    
    def save_project_as(self):
        """Save the current project to a new file"""
        file_name, _ = QFileDialog.getSaveFileName(
            self.window,
            "Save Project",
            "",
            "SQL Shell Project (*.sqls);;All Files (*)"
        )
        
        if file_name:
            if not file_name.endswith('.sqls'):
                file_name += '.sqls'
            self.save_project_to_file(file_name)
            self.window.current_project_file = file_name
            self.window.setWindowTitle(f'SQL Shell - {os.path.basename(file_name)}')
    
    def save_project_to_file(self, file_name):
        """Save project data to a file"""
        try:
            # Save tab information
            tabs_data = []
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                tab_data = {
                    'title': self.tab_widget.tabText(i),
                    'query': tab.get_query_text()
                }
                tabs_data.append(tab_data)
            
            project_data = {
                'tables': {},
                'folders': {},
                'tabs': tabs_data,
                'connection_type': self.db_manager.connection_type,
                'database_path': None,  # Initialize to None
                'column_renames': getattr(self.window, '_column_renames', {})  # Save column rename mappings
            }
            
            # If we have a database connection, save the path
            if self.db_manager.is_connected() and hasattr(self.db_manager, 'database_path'):
                project_data['database_path'] = self.db_manager.database_path
            
            # Helper function to recursively save folder structure
            def save_folder_structure(parent_item, parent_path=""):
                if parent_item is None:
                    # Handle top-level items
                    for i in range(self.tables_list.topLevelItemCount()):
                        item = self.tables_list.topLevelItem(i)
                        if self.tables_list.is_folder_item(item):
                            # It's a folder - add to folders and process its children
                            folder_name = item.text(0)
                            folder_id = f"folder_{i}"
                            project_data['folders'][folder_id] = {
                                'name': folder_name,
                                'parent': None,
                                'expanded': item.isExpanded()
                            }
                            save_folder_structure(item, folder_id)
                        else:
                            # It's a table - add to tables at root level
                            save_table_item(item)
                else:
                    # Process children of this folder
                    for i in range(parent_item.childCount()):
                        child = parent_item.child(i)
                        if self.tables_list.is_folder_item(child):
                            # It's a subfolder
                            folder_name = child.text(0)
                            folder_id = f"{parent_path}_sub_{i}"
                            project_data['folders'][folder_id] = {
                                'name': folder_name,
                                'parent': parent_path,
                                'expanded': child.isExpanded()
                            }
                            save_folder_structure(child, folder_id)
                        else:
                            # It's a table in this folder
                            save_table_item(child, parent_path)
            
            # Helper function to save table item
            def save_table_item(item, folder_id=None):
                table_name = self.tables_list.get_table_name_from_item(item)
                if not table_name or table_name not in self.db_manager.loaded_tables:
                    return
                    
                file_path = self.db_manager.loaded_tables[table_name]
                
                # For database tables (including new format 'database:alias'), query results, store the identifier
                if file_path == 'query_result' or file_path.startswith('database'):
                    # Save as 'database' for backward compatibility with project files
                    source_path = 'database' if file_path.startswith('database') else file_path
                else:
                    # For file-based tables, store the absolute path
                    source_path = os.path.abspath(file_path)
                
                project_data['tables'][table_name] = {
                    'file_path': source_path,
                    'columns': self.db_manager.table_columns.get(table_name, []),
                    'folder': folder_id
                }
            
            # Save the folder structure
            save_folder_structure(None)
            
            with open(file_name, 'w') as f:
                json.dump(project_data, f, indent=4)
                
            # Add to recent projects
            self.window.add_recent_project(os.path.abspath(file_name))
                
            self.window.statusBar().showMessage(f'Project saved to {file_name}')
            
        except Exception as e:
            QMessageBox.critical(self.window, "Error",
                f"Failed to save project:\n\n{str(e)}")
    
    def open_project(self, file_name=None):
        """Open a project file"""
        if not file_name:
            # Check for unsaved changes before showing file dialog
            if self.window.has_unsaved_changes():
                reply = QMessageBox.question(self.window, 'Save Changes',
                    'Do you want to save your changes before opening another project?',
                    QMessageBox.StandardButton.Save | 
                    QMessageBox.StandardButton.Discard | 
                    QMessageBox.StandardButton.Cancel)
                
                if reply == QMessageBox.StandardButton.Save:
                    self.save_project()
                elif reply == QMessageBox.StandardButton.Cancel:
                    return
            
            # Show file dialog after handling save prompt
            file_name, _ = QFileDialog.getOpenFileName(
                self.window,
                "Open Project",
                "",
                "SQL Shell Project (*.sqls);;All Files (*)"
            )
        
        if file_name:
            try:
                # Create a progress dialog to keep UI responsive
                progress = QProgressDialog("Loading project...", "Cancel", 0, 100, self.window)
                progress.setWindowTitle("Opening Project")
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(500)  # Show after 500ms delay
                progress.setValue(0)
                
                # Load project data
                with open(file_name, 'r') as f:
                    project_data = json.load(f)
                
                # Update progress
                progress.setValue(10)
                QApplication.processEvents()
                
                # Start fresh
                self.new_project(skip_confirmation=True)
                progress.setValue(15)
                QApplication.processEvents()
                
                # Make sure all database tables are cleared from tracking
                self.db_manager.loaded_tables = {}
                self.db_manager.table_columns = {}
                
                # Check if there's a database path in the project
                has_database_path = 'database_path' in project_data and project_data['database_path']
                has_database_tables = any(
                    table_info.get('file_path') == 'database' or 
                    (table_info.get('file_path') or '').startswith('database:')
                    for table_info in project_data.get('tables', {}).values()
                )
                
                # Connect to database if needed
                progress.setLabelText("Connecting to database...")
                database_tables_loaded = False
                database_connection_message = None
                
                if has_database_path and has_database_tables:
                    database_path = project_data['database_path']
                    try:
                        if os.path.exists(database_path):
                            # Connect to the database
                            self.db_manager.open_database(database_path, load_all_tables=False)
                            self.window.db_info_label.setText(self.db_manager.get_connection_info())
                            self.window.statusBar().showMessage(f"Connected to database: {database_path}")
                            
                            # Mark database tables as loaded
                            database_tables_loaded = True
                        else:
                            database_tables_loaded = False
                            # Store the message instead of showing immediately
                            database_connection_message = (
                                "Database Not Found", 
                                f"The project's database file was not found at:\n{database_path}\n\n"
                                "Database tables will be shown but not accessible until you reconnect to the database.\n\n"
                                "Use the 'Open Database' button to connect to your database file."
                            )
                    except Exception as e:
                        database_tables_loaded = False
                        # Store the message instead of showing immediately
                        database_connection_message = (
                            "Database Connection Error",
                            f"Failed to connect to the project's database:\n{str(e)}\n\n"
                            "Database tables will be shown but not accessible until you reconnect to the database.\n\n"
                            "Use the 'Open Database' button to connect to your database file."
                        )
                else:
                    # Create connection if needed (we don't have a specific database to connect to)
                    database_tables_loaded = False
                    if not self.db_manager.is_connected():
                        connection_info = self.db_manager.create_memory_connection()
                        self.window.db_info_label.setText(connection_info)
                    elif 'connection_type' in project_data and project_data['connection_type'] != self.db_manager.connection_type:
                        # If connected but with a different database type than what was saved in the project
                        # Store the message instead of showing immediately
                        database_connection_message = (
                            "Database Type Mismatch",
                            f"The project was saved with a {project_data['connection_type']} database, but you're currently using {self.db_manager.connection_type}.\n\n"
                            "Some database-specific features may not work correctly. Consider reconnecting to the correct database type."
                        )
                
                progress.setValue(20)
                QApplication.processEvents()
                
                # First, recreate the folder structure
                folder_items = {}  # Store folder items by ID
                
                # Create folders first
                if 'folders' in project_data:
                    progress.setLabelText("Creating folders...")
                    # First pass: create top-level folders
                    for folder_id, folder_info in project_data['folders'].items():
                        if folder_info.get('parent') is None:
                            # Create top-level folder
                            folder = self.tables_list.create_folder(folder_info['name'])
                            folder_items[folder_id] = folder
                            # Set expanded state
                            folder.setExpanded(folder_info.get('expanded', True))
                    
                    # Second pass: create subfolders
                    for folder_id, folder_info in project_data['folders'].items():
                        parent_id = folder_info.get('parent')
                        if parent_id is not None and parent_id in folder_items:
                            # Create subfolder under parent
                            parent_folder = folder_items[parent_id]
                            subfolder = QTreeWidgetItem(parent_folder)
                            subfolder.setText(0, folder_info['name'])
                            subfolder.setIcon(0, QIcon.fromTheme("folder"))
                            subfolder.setData(0, Qt.ItemDataRole.UserRole, "folder")
                            # Make folder text bold
                            font = subfolder.font(0)
                            font.setBold(True)
                            subfolder.setFont(0, font)
                            # Set folder flags
                            subfolder.setFlags(subfolder.flags() | Qt.ItemFlag.ItemIsDropEnabled)
                            # Set expanded state
                            subfolder.setExpanded(folder_info.get('expanded', True))
                            folder_items[folder_id] = subfolder
                            
                progress.setValue(25)
                QApplication.processEvents()
                
                # Calculate progress steps for loading tables
                table_count = len(project_data.get('tables', {}))
                table_progress_start = 30
                table_progress_end = 70
                table_progress_step = (table_progress_end - table_progress_start) / max(1, table_count)
                current_progress = table_progress_start
                
                # Load tables
                for table_name, table_info in project_data.get('tables', {}).items():
                    if progress.wasCanceled():
                        break
                        
                    progress.setLabelText(f"Processing table: {table_name}")
                    file_path = table_info['file_path']
                    self.window.statusBar().showMessage(f"Processing table: {table_name} from {file_path}")
                    
                    try:
                        # Determine folder placement
                        folder_id = table_info.get('folder')
                        parent_folder = folder_items.get(folder_id) if folder_id else None
                        
                        if file_path == 'database' or file_path.startswith('database:'):
                            # Different handling based on whether database connection is active
                            if database_tables_loaded:
                                # Store table info without loading data
                                # Use the new format 'database:db' for attached databases
                                self.db_manager.loaded_tables[table_name] = 'database:db'
                                if 'columns' in table_info:
                                    self.db_manager.table_columns[table_name] = table_info['columns']
                                    
                                # Create item without reload icon
                                if parent_folder:
                                    # Add to folder
                                    item = QTreeWidgetItem(parent_folder)
                                    item.setText(0, f"{table_name} (database)")
                                    item.setIcon(0, QIcon.fromTheme("x-office-spreadsheet"))
                                    item.setData(0, Qt.ItemDataRole.UserRole, "table")
                                else:
                                    # Add to root
                                    self.tables_list.add_table_item(table_name, "database", needs_reload=False)
                            else:
                                # No active database connection, just register the table name
                                self.db_manager.loaded_tables[table_name] = 'database:db'
                                if 'columns' in table_info:
                                    self.db_manager.table_columns[table_name] = table_info['columns']
                                
                                # Create item with reload icon
                                if parent_folder:
                                    # Add to folder
                                    item = QTreeWidgetItem(parent_folder)
                                    item.setText(0, f"{table_name} (database)")
                                    item.setIcon(0, QIcon.fromTheme("view-refresh"))
                                    item.setData(0, Qt.ItemDataRole.UserRole, "table")
                                    item.setToolTip(0, f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
                                    self.tables_list.tables_needing_reload.add(table_name)
                                else:
                                    # Add to root
                                    self.tables_list.add_table_item(table_name, "database", needs_reload=True)
                        elif file_path == 'query_result':
                            # For tables from query results, just note it as a query result table
                            self.db_manager.loaded_tables[table_name] = 'query_result'
                            
                            # Create item with reload icon
                            if parent_folder:
                                # Add to folder
                                item = QTreeWidgetItem(parent_folder)
                                item.setText(0, f"{table_name} (query result)")
                                item.setIcon(0, QIcon.fromTheme("view-refresh"))
                                item.setData(0, Qt.ItemDataRole.UserRole, "table")
                                item.setToolTip(0, f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
                                self.tables_list.tables_needing_reload.add(table_name)
                            else:
                                # Add to root
                                self.tables_list.add_table_item(table_name, "query result", needs_reload=True)
                        elif os.path.exists(file_path):
                            # Register the file as a table source but don't load data yet
                            self.db_manager.loaded_tables[table_name] = file_path
                            if 'columns' in table_info:
                                self.db_manager.table_columns[table_name] = table_info['columns']
                                
                            # Create item with reload icon
                            if parent_folder:
                                # Add to folder
                                item = QTreeWidgetItem(parent_folder)
                                item.setText(0, f"{table_name} ({os.path.basename(file_path)})")
                                item.setIcon(0, QIcon.fromTheme("view-refresh"))
                                item.setData(0, Qt.ItemDataRole.UserRole, "table")
                                item.setToolTip(0, f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
                                self.tables_list.tables_needing_reload.add(table_name)
                            else:
                                # Add to root
                                self.tables_list.add_table_item(table_name, os.path.basename(file_path), needs_reload=True)
                        else:
                            # File doesn't exist, but add to list with warning
                            self.db_manager.loaded_tables[table_name] = file_path
                            if 'columns' in table_info:
                                self.db_manager.table_columns[table_name] = table_info['columns']
                                
                            # Create item with reload icon and missing warning
                            if parent_folder:
                                # Add to folder
                                item = QTreeWidgetItem(parent_folder)
                                item.setText(0, f"{table_name} ({os.path.basename(file_path)} (missing))")
                                item.setIcon(0, QIcon.fromTheme("view-refresh"))
                                item.setData(0, Qt.ItemDataRole.UserRole, "table")
                                item.setToolTip(0, f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
                                self.tables_list.tables_needing_reload.add(table_name)
                            else:
                                # Add to root
                                self.tables_list.add_table_item(table_name, f"{os.path.basename(file_path)} (missing)", needs_reload=True)
                            
                    except Exception as e:
                        QMessageBox.warning(self.window, "Warning",
                            f"Failed to process table {table_name}:\n{str(e)}")
                
                    # Update progress for this table
                    current_progress += table_progress_step
                    progress.setValue(int(current_progress))
                    QApplication.processEvents()  # Keep UI responsive
                
                # Check if the operation was canceled
                if progress.wasCanceled():
                    self.window.statusBar().showMessage("Project loading was canceled")
                    progress.close()
                    return
                
                # Apply column renames if they exist in the project
                progress.setValue(72)
                progress.setLabelText("Applying column renames...")
                QApplication.processEvents()
                
                if 'column_renames' in project_data and project_data['column_renames']:
                    # Initialize column_renames if it doesn't exist
                    if not hasattr(self.window, '_column_renames'):
                        self.window._column_renames = {}
                    
                    # Restore the column rename mappings
                    self.window._column_renames = project_data['column_renames']
                    
                    # Apply renames to tables that are already loaded
                    for table_name, rename_map in project_data['column_renames'].items():
                        if table_name in self.db_manager.loaded_tables:
                            try:
                                # Get the current table data
                                if table_name in self.db_manager.loaded_tables:
                                    # Try to get the table - it might need to be loaded first
                                    try:
                                        table_df = self.db_manager.get_full_table(table_name)
                                        
                                        # Apply all renames for this table
                                        rename_dict = {}
                                        for old_name, new_name in rename_map.items():
                                            if old_name in table_df.columns and new_name not in table_df.columns:
                                                rename_dict[old_name] = new_name
                                        
                                        if rename_dict:
                                            # Apply the renames
                                            renamed_df = table_df.rename(columns=rename_dict)
                                            
                                            # Update the table in DuckDB
                                            # Use 'transformed' source instead of preserving 'database:' source
                                            # This ensures _qualify_table_names won't rewrite queries to db.<table>
                                            self.db_manager.overwrite_table_with_dataframe(table_name, renamed_df, source='transformed')
                                            
                                            # Update table_columns tracking
                                            if table_name in self.db_manager.table_columns:
                                                columns = self.db_manager.table_columns[table_name]
                                                updated_columns = []
                                                for col in columns:
                                                    if col in rename_dict:
                                                        updated_columns.append(rename_dict[col])
                                                    else:
                                                        updated_columns.append(col)
                                                self.db_manager.table_columns[table_name] = updated_columns
                                            
                                            # Update preview transforms if it exists
                                            if hasattr(self.window, '_preview_transforms'):
                                                if table_name in self.window._preview_transforms:
                                                    self.window._preview_transforms[table_name] = renamed_df
                                    except Exception as e:
                                        # Table might not be loaded yet - that's okay, renames will be applied when it's loaded
                                        print(f"Note: Could not apply renames to table '{table_name}' yet (may need to be loaded): {e}")
                            except Exception as e:
                                print(f"Warning: Could not apply column renames for table '{table_name}': {e}")
                
                progress.setValue(75)
                progress.setLabelText("Setting up tabs...")
                QApplication.processEvents()
                
                # Load tabs in a more efficient way
                if 'tabs' in project_data and project_data['tabs']:
                    try:
                        # Temporarily disable signals
                        self.tab_widget.blockSignals(True)
                        
                        # First, pre-remove any existing tabs
                        while self.tab_widget.count() > 0:
                            widget = self.tab_widget.widget(0)
                            self.tab_widget.removeTab(0)
                            if widget in self.tabs:
                                self.tabs.remove(widget)
                            widget.deleteLater()
                        
                        # Then create all tab widgets at once (empty)
                        tab_count = len(project_data['tabs'])
                        tab_progress_step = 15 / max(1, tab_count)
                        progress.setValue(80)
                        QApplication.processEvents()
                        
                        # Create all tab widgets first without setting content
                        for i, tab_data in enumerate(project_data['tabs']):
                            # Create a new tab
                            tab = QueryTab(self.window)
                            self.tabs.append(tab)
                            
                            # Add to tab widget
                            title = tab_data.get('title', f'Query {i+1}')
                            self.tab_widget.addTab(tab, title)
                            
                            progress.setValue(int(80 + i * tab_progress_step/2))
                            QApplication.processEvents()
                        
                        # Now set the content for each tab
                        for i, tab_data in enumerate(project_data['tabs']):
                            # Get the tab and set its query text
                            tab = self.tab_widget.widget(i)
                            if tab and 'query' in tab_data:
                                tab.set_query_text(tab_data['query'])
                            
                            progress.setValue(int(87 + i * tab_progress_step/2))
                            QApplication.processEvents()
                        
                        # Re-enable signals
                        self.tab_widget.blockSignals(False)
                        
                        # Set current tab
                        if self.tab_widget.count() > 0:
                            self.tab_widget.setCurrentIndex(0)
                            
                    except Exception as e:
                        # If there's an error, ensure we restore signals
                        self.tab_widget.blockSignals(False)
                        self.window.statusBar().showMessage(f"Error loading tabs: {str(e)}")
                        # Create a single default tab if all fails
                        if self.tab_widget.count() == 0:
                            self.window.add_tab()
                else:
                    # Create default tab if no tabs in project
                    self.window.add_tab()
                
                progress.setValue(90)
                progress.setLabelText("Finishing up...")
                QApplication.processEvents()
                
                # Update UI
                self.window.current_project_file = file_name
                self.window.setWindowTitle(f'SQL Shell - {os.path.basename(file_name)}')
                
                # Add to recent projects
                self.window.add_recent_project(os.path.abspath(file_name))
                
                # Defer the auto-completer update to after loading is complete
                # This helps prevent UI freezing during project loading
                progress.setValue(95)
                QApplication.processEvents()
                
                # Use a timer to update the completer after the UI is responsive
                complete_timer = QTimer()
                complete_timer.setSingleShot(True)
                complete_timer.timeout.connect(self.window.update_completer)
                complete_timer.start(100)  # Short delay before updating completer
                
                # Queue another update for reliability - sometimes the first update might not fully complete
                failsafe_timer = QTimer()
                failsafe_timer.setSingleShot(True)
                failsafe_timer.timeout.connect(self.window.update_completer)
                failsafe_timer.start(2000)  # Try again after 2 seconds to ensure completion is loaded
                
                progress.setValue(100)
                QApplication.processEvents()
                
                # Show message about tables needing reload
                reload_count = len(self.tables_list.tables_needing_reload)
                if reload_count > 0:
                    self.window.statusBar().showMessage(
                        f'Project loaded from {file_name} with {table_count} tables. {reload_count} tables need to be reloaded (click reload icon).'
                    )
                else:
                    self.window.statusBar().showMessage(
                        f'Project loaded from {file_name} with {table_count} tables.'
                    )
                
                # Close progress dialog before showing message boxes
                progress.close()
                
                # Now show any database connection message we stored earlier
                if database_connection_message and not database_tables_loaded and has_database_tables:
                    title, message = database_connection_message
                    QMessageBox.warning(self.window, title, message)
                
            except Exception as e:
                QMessageBox.critical(self.window, "Error",
                    f"Failed to open project:\n\n{str(e)}")

