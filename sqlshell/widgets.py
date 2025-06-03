from PyQt6.QtWidgets import QTableWidget, QApplication, QMenu
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent, QAction
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
        """Handle key press events, specifically Ctrl+C for copying"""
        if event.key() == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.copy_selection_to_clipboard()
            return
        
        # For other keys, use the default behavior
        super().keyPressEvent(event)
    
    def show_context_menu(self, position):
        """Show context menu with copy options"""
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
        
        # Only show menu if we have actions
        if menu.actions():
            menu.exec(self.mapToGlobal(position))
    
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