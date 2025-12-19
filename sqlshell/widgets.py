from PyQt6.QtWidgets import QTableWidget, QApplication, QMenu, QMessageBox
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent, QAction, QIcon
import pandas as pd
import numpy as np


class CopyableTableWidget(QTableWidget):
    """Custom QTableWidget that supports copying data to clipboard with Ctrl+C"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events, specifically Ctrl+C for copying and Del for column delete."""
        # Copy selection with Ctrl+C
        if event.key() == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.copy_selection_to_clipboard()
            return

        # Delete selected columns with Del key (no modifiers)
        if event.key() == Qt.Key.Key_Delete and not event.modifiers():
            parent_tab = getattr(self, "_parent_tab", None)
            main_window = self._get_main_window()
            header = self.horizontalHeader()

            if parent_tab and main_window and hasattr(main_window, "delete_column") and header is not None:
                # Determine which columns are selected via header selection model
                selected_sections = header.selectionModel().selectedColumns()
                if selected_sections:
                    # Delete columns from right to left to keep indices stable
                    # Get column names from the DataFrame that will be used by the tool
                    if hasattr(main_window, "get_column_name_by_index"):
                        col_indices = sorted({s.column() for s in selected_sections}, reverse=True)
                        for col_idx in col_indices:
                            col_name = main_window.get_column_name_by_index(col_idx)
                            if col_name:
                                main_window.delete_column(col_name)
                    return

        # For other keys, use the default behavior
        super().keyPressEvent(event)
    
    def _get_current_table_name(self):
        """Get the current table name from the results context"""
        try:
            parent_tab = getattr(self, '_parent_tab', None)
            if parent_tab is None:
                return None
            
            # First check if we're in preview mode with a known table name
            if hasattr(parent_tab, 'preview_table_name') and parent_tab.preview_table_name:
                return parent_tab.preview_table_name
            
            # Otherwise try to get from the DataFrame's _query_source attribute
            if hasattr(parent_tab, 'current_df') and parent_tab.current_df is not None:
                if hasattr(parent_tab.current_df, '_query_source'):
                    return getattr(parent_tab.current_df, '_query_source')
            
            # As a fallback, try to extract table name from the query text
            if hasattr(parent_tab, 'query_edit'):
                query_text = parent_tab.query_edit.toPlainText().strip()
                if query_text:
                    # Try to extract table name from simple SELECT queries
                    import re
                    # Look for FROM or JOIN clauses
                    pattern = r'(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)'
                    matches = re.findall(pattern, query_text, re.IGNORECASE)
                    if matches:
                        # Return the first table found
                        table_name = matches[0]
                        # Verify this table exists in the main window's loaded tables
                        main_window = self._get_main_window()
                        if main_window and hasattr(main_window, 'db_manager'):
                            if table_name in main_window.db_manager.loaded_tables:
                                return table_name
            
            return None
        except Exception:
            return None
    
    def _get_main_window(self):
        """Get a reference to the main window"""
        try:
            parent_tab = getattr(self, '_parent_tab', None)
            if parent_tab and hasattr(parent_tab, 'parent'):
                return parent_tab.parent
            return None
        except Exception:
            return None
    
    def show_context_menu(self, position):
        """Show context menu with copy options and table analysis actions"""
        menu = QMenu(self)
        
        # Check if there's a selection
        has_selection = bool(self.selectionModel().selection())
        
        if has_selection:
            copy_selection_action = QAction("Copy Selection (Ctrl+C)", self)
            copy_selection_action.triggered.connect(self.copy_selection_to_clipboard)
            menu.addAction(copy_selection_action)
            
            menu.addSeparator()
        
        copy_all_action = QAction("Copy All Data", self)
        copy_all_action.triggered.connect(self.copy_all_to_clipboard)
        menu.addAction(copy_all_action)
        
        # Add count rows action if we have data
        parent_tab = getattr(self, '_parent_tab', None)
        if parent_tab and hasattr(parent_tab, 'current_df') and parent_tab.current_df is not None:
            menu.addSeparator()
            count_rows_action = QAction("Count Rows", self)
            count_rows_action.triggered.connect(self._show_row_count)
            menu.addAction(count_rows_action)
            
            # Add "Save as Table" action
            save_as_table_action = QAction("Save as Table...", self)
            save_as_table_action.setIcon(QIcon.fromTheme("document-save"))
            save_as_table_action.triggered.connect(self._save_results_as_table)
            menu.addAction(save_as_table_action)
            
            # Add transform submenu for result-set level operations
            transform_menu = menu.addMenu("Transform")
            convert_query_names_action = transform_menu.addAction(
                "Convert Column Names to Query-Friendly (lowercase_with_underscores, trimmed)"
            )
        
        # Add table analysis options if we have data
        table_name = self._get_current_table_name()
        main_window = self._get_main_window()
        
        # Show analysis menu if we have either a table name OR current data
        has_data = (parent_tab and hasattr(parent_tab, 'current_df') and 
                    parent_tab.current_df is not None and not parent_tab.current_df.empty)
        
        if main_window and (table_name or has_data):
            menu.addSeparator()
            
            # Add a submenu for table analysis
            analysis_menu = menu.addMenu("Table Analysis")
            analysis_menu.setIcon(QIcon.fromTheme("system-search"))
            
            # If we have a table name, use table-based analysis
            # Otherwise, use DataFrame-based analysis
            if table_name:
                # Analyze Column Importance (entropy)
                analyze_entropy_action = analysis_menu.addAction("Analyze Column Importance")
                analyze_entropy_action.setIcon(QIcon.fromTheme("system-search"))
                analyze_entropy_action.triggered.connect(
                    lambda: self._call_main_window_method('analyze_table_entropy', table_name)
                )
                
                # Find Keys
                profile_table_action = analysis_menu.addAction("Find Keys")
                profile_table_action.setIcon(QIcon.fromTheme("edit-find"))
                profile_table_action.triggered.connect(
                    lambda: self._call_main_window_method('profile_table_structure', table_name)
                )
                
                # Analyze Column Distributions
                profile_distributions_action = analysis_menu.addAction("Analyze Column Distributions")
                profile_distributions_action.setIcon(QIcon.fromTheme("accessories-calculator"))
                profile_distributions_action.triggered.connect(
                    lambda: self._call_main_window_method('profile_distributions', table_name)
                )
                
                # Analyze Row Similarity
                profile_similarity_action = analysis_menu.addAction("Analyze Row Similarity")
                profile_similarity_action.setIcon(QIcon.fromTheme("applications-utilities"))
                profile_similarity_action.triggered.connect(
                    lambda: self._call_main_window_method('profile_similarity', table_name)
                )
            else:
                # Use DataFrame-based analysis for query results without a clear table source
                # Analyze Column Importance (entropy)
                analyze_entropy_action = analysis_menu.addAction("Analyze Column Importance")
                analyze_entropy_action.setIcon(QIcon.fromTheme("system-search"))
                analyze_entropy_action.triggered.connect(
                    lambda: self._call_main_window_method('analyze_current_data_entropy')
                )
                
                # Find Keys
                profile_table_action = analysis_menu.addAction("Find Keys")
                profile_table_action.setIcon(QIcon.fromTheme("edit-find"))
                profile_table_action.triggered.connect(
                    lambda: self._call_main_window_method('profile_current_data_structure')
                )
                
                # Analyze Column Distributions
                profile_distributions_action = analysis_menu.addAction("Analyze Column Distributions")
                profile_distributions_action.setIcon(QIcon.fromTheme("accessories-calculator"))
                profile_distributions_action.triggered.connect(
                    lambda: self._call_main_window_method('profile_current_data_distributions')
                )
                
                # Analyze Row Similarity
                profile_similarity_action = analysis_menu.addAction("Analyze Row Similarity")
                profile_similarity_action.setIcon(QIcon.fromTheme("applications-utilities"))
                profile_similarity_action.triggered.connect(
                    lambda: self._call_main_window_method('profile_current_data_similarity')
                )
        
        # Only show menu if we have actions
        if menu.actions():
            action = menu.exec(self.mapToGlobal(position))
            
            # Handle transform actions that need to call back into the main window
            if parent_tab and hasattr(parent_tab, 'current_df') and parent_tab.current_df is not None:
                if 'convert_query_names_action' in locals() and action == convert_query_names_action:
                    main_window = self._get_main_window()
                    if main_window and hasattr(main_window, 'convert_current_results_to_query_friendly_names'):
                        main_window.convert_current_results_to_query_friendly_names()
    
    def _call_main_window_method(self, method_name, table_name=None):
        """Call a method on the main window with optional table name"""
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, method_name):
            method = getattr(main_window, method_name)
            if table_name is not None:
                method(table_name)
            else:
                method()
    
    def _show_row_count(self):
        """Show the row count in a message box"""
        parent_tab = getattr(self, '_parent_tab', None)
        if not parent_tab:
            return
        
        # Check if we're in preview mode - if so, get the full table count
        if (hasattr(parent_tab, 'is_preview_mode') and parent_tab.is_preview_mode and 
            hasattr(parent_tab, 'preview_table_name') and parent_tab.preview_table_name):
            # Get the main window to access the database manager
            main_window = self._get_main_window()
            if main_window and hasattr(main_window, 'db_manager'):
                try:
                    # Get the full table to count all rows
                    full_df = main_window.db_manager.get_full_table(parent_tab.preview_table_name)
                    row_count = len(full_df)
                    QMessageBox.information(self, "Row Count", f"Total rows: {row_count:,}")
                except Exception as e:
                    # Fall back to preview count if we can't get full table
                    if hasattr(parent_tab, 'current_df') and parent_tab.current_df is not None:
                        row_count = len(parent_tab.current_df)
                        QMessageBox.information(self, "Row Count", f"Preview rows: {row_count:,}\n(Error getting full count: {str(e)})")
        elif hasattr(parent_tab, 'current_df') and parent_tab.current_df is not None:
            # Not in preview mode, just show the current dataframe count
            row_count = len(parent_tab.current_df)
            QMessageBox.information(self, "Row Count", f"Total rows: {row_count:,}")
    
    def _save_results_as_table(self):
        """Save the current query results as a new table in the database"""
        parent_tab = getattr(self, '_parent_tab', None)
        if not parent_tab:
            return
        
        if not hasattr(parent_tab, 'current_df') or parent_tab.current_df is None:
            QMessageBox.warning(self, "No Data", "No results to save as table.")
            return
        
        df = parent_tab.current_df
        if df.empty:
            QMessageBox.warning(self, "No Data", "Results are empty. Nothing to save.")
            return
        
        main_window = self._get_main_window()
        if not main_window or not hasattr(main_window, 'save_results_as_table'):
            QMessageBox.warning(self, "Error", "Could not access main window.")
            return
        
        # Call the main window method to handle the save
        main_window.save_results_as_table(df)
    
    def _get_unformatted_value(self, row, col):
        """Get the unformatted value from the original DataFrame if available"""
        try:
            # Try to get the original DataFrame from the parent tab
            parent_tab = None
            
            # First try the direct reference we set
            if hasattr(self, '_parent_tab') and self._parent_tab is not None:
                parent_tab = self._parent_tab
            else:
                # Fallback to parent() method
                parent_tab = self.parent()
            
            if parent_tab and hasattr(parent_tab, 'current_df') and parent_tab.current_df is not None:
                original_df = parent_tab.current_df
                
                # Calculate the actual DataFrame row index, accounting for pagination
                actual_row_idx = row
                
                # If pagination is active, adjust the row index
                if hasattr(parent_tab, 'pagination_state') and parent_tab.pagination_state:
                    state = parent_tab.pagination_state
                    page_offset = state['current_page'] * state['page_size']
                    actual_row_idx = page_offset + row
                
                # Check if we have valid indices
                if actual_row_idx < len(original_df) and col < len(original_df.columns):
                    # Get the raw value from the original DataFrame
                    raw_value = original_df.iloc[actual_row_idx, col]
                    
                    # Handle NaN/NULL values
                    if pd.isna(raw_value):
                        return "NULL"
                    
                    # For numeric types, return the raw value as string without formatting
                    if isinstance(raw_value, (int, float, np.integer, np.floating)):
                        return str(raw_value)
                    
                    # For other types, return as string
                    return str(raw_value)
            
            # Try alternative ways to access the dataframe
            # Check if the parent has a parent (main window) that might have current_df
            if parent_tab and hasattr(parent_tab, 'parent') and hasattr(parent_tab.parent(), 'current_df') and parent_tab.parent().current_df is not None:
                original_df = parent_tab.parent().current_df
                
                # Calculate the actual DataFrame row index, accounting for pagination
                actual_row_idx = row
                
                # Check if we have valid indices
                if actual_row_idx < len(original_df) and col < len(original_df.columns):
                    # Get the raw value from the original DataFrame
                    raw_value = original_df.iloc[actual_row_idx, col]
                    
                    # Handle NaN/NULL values
                    if pd.isna(raw_value):
                        return "NULL"
                    
                    # For numeric types, return the raw value as string without formatting
                    if isinstance(raw_value, (int, float, np.integer, np.floating)):
                        return str(raw_value)
                    
                    # For other types, return as string
                    return str(raw_value)
                    
        except Exception as e:
            # If anything fails, fall back to formatted text
            pass
        
        # Fallback: use the formatted text from the table item
        item = self.item(row, col)
        return item.text() if item else ""
    
    def copy_selection_to_clipboard(self):
        """Copy selected cells to clipboard in tab-separated format"""
        selection = self.selectionModel().selection()
        
        if not selection:
            # If no selection, copy all visible data
            self.copy_all_to_clipboard()
            return
        
        # Get selected ranges
        selected_ranges = selection
        if not selected_ranges:
            return
        
        # Find the bounds of the selection
        min_row = float('inf')
        max_row = -1
        min_col = float('inf')
        max_col = -1
        
        for range_ in selected_ranges:
            min_row = min(min_row, range_.top())
            max_row = max(max_row, range_.bottom())
            min_col = min(min_col, range_.left())
            max_col = max(max_col, range_.right())
        
        # Build the data to copy
        copied_data = []
        
        # Add headers if copying from the first row or if entire columns are selected
        if min_row == 0 or self.are_entire_columns_selected():
            header_row = []
            for col in range(min_col, max_col + 1):
                header_item = self.horizontalHeaderItem(col)
                header_text = header_item.text() if header_item else f"Column_{col}"
                header_row.append(header_text)
            copied_data.append('\t'.join(header_row))
        
        # Add data rows
        for row in range(min_row, max_row + 1):
            if row >= self.rowCount():
                break
                
            row_data = []
            for col in range(min_col, max_col + 1):
                if col >= self.columnCount():
                    break
                    
                # Use unformatted value when possible
                cell_text = self._get_unformatted_value(row, col)
                row_data.append(cell_text)
            
            copied_data.append('\t'.join(row_data))
        
        # Join all rows with newlines and copy to clipboard
        clipboard_text = '\n'.join(copied_data)
        QApplication.clipboard().setText(clipboard_text)
        
        # Show status message if parent has statusBar
        if hasattr(self.parent(), 'statusBar'):
            row_count = max_row - min_row + 1
            col_count = max_col - min_col + 1
            self.parent().statusBar().showMessage(f"Copied {row_count} rows × {col_count} columns to clipboard")
        elif hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'statusBar'):
            row_count = max_row - min_row + 1
            col_count = max_col - min_col + 1
            self.parent().parent().statusBar().showMessage(f"Copied {row_count} rows × {col_count} columns to clipboard")
    
    def copy_all_to_clipboard(self):
        """Copy all table data to clipboard"""
        if self.rowCount() == 0 or self.columnCount() == 0:
            return
        
        copied_data = []
        
        # Add headers
        header_row = []
        for col in range(self.columnCount()):
            header_item = self.horizontalHeaderItem(col)
            header_text = header_item.text() if header_item else f"Column_{col}"
            header_row.append(header_text)
        copied_data.append('\t'.join(header_row))
        
        # Add all data rows
        for row in range(self.rowCount()):
            row_data = []
            for col in range(self.columnCount()):
                # Use unformatted value when possible
                cell_text = self._get_unformatted_value(row, col)
                row_data.append(cell_text)
            copied_data.append('\t'.join(row_data))
        
        # Join all rows with newlines and copy to clipboard
        clipboard_text = '\n'.join(copied_data)
        QApplication.clipboard().setText(clipboard_text)
        
        # Show status message if parent has statusBar
        if hasattr(self.parent(), 'statusBar'):
            self.parent().statusBar().showMessage(f"Copied all {self.rowCount()} rows × {self.columnCount()} columns to clipboard")
        elif hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'statusBar'):
            self.parent().parent().statusBar().showMessage(f"Copied all {self.rowCount()} rows × {self.columnCount()} columns to clipboard")
    
    def are_entire_columns_selected(self):
        """Check if entire columns are selected"""
        selection = self.selectionModel().selection()
        if not selection:
            return False
        
        for range_ in selection:
            if range_.top() == 0 and range_.bottom() == self.rowCount() - 1:
                return True
        return False 