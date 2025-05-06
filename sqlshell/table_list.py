import os
import sys
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QListWidget, QListWidgetItem, 
                            QMessageBox, QMainWindow, QVBoxLayout, QLabel, 
                            QWidget, QHBoxLayout, QFrame, QTreeWidget, QTreeWidgetItem,
                            QMenu, QInputDialog, QLineEdit)
from PyQt6.QtCore import Qt, QPoint, QMimeData, QTimer, QSize
from PyQt6.QtGui import QIcon, QDrag, QPainter, QColor, QBrush, QPixmap, QFont, QCursor, QAction
from PyQt6.QtCore import pyqtSignal

class DraggableTablesList(QTreeWidget):
    """Custom QTreeWidget that provides folders and drag-and-drop functionality for table names.
    
    Features:
    - Hierarchical display of tables in folders
    - Drag and drop tables between folders
    - Visual feedback when dragging tables over folders
    - Double-click to expand/collapse folders
    - Tables can be dragged into query editor for SQL generation
    - Context menu for folder management and table operations
    - Tables needing reload are marked with special icons
    - Tables can be dragged from root to folders and vice versa
    """
    
    # Define signals
    itemDropped = pyqtSignal(str, str, bool)  # source_item, target_folder, success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        
        # Configure tree widget
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        self.setIndentation(15)  # Smaller indentation for a cleaner look
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.setExpandsOnDoubleClick(False)  # Handle double-clicks manually
        
        # Apply custom styling
        self.setStyleSheet(self.get_stylesheet())
        
        # Store tables that need reloading
        self.tables_needing_reload = set()
        
        # Connect signals
        self.itemDoubleClicked.connect(self.handle_item_double_click)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def get_stylesheet(self):
        """Get the stylesheet for the draggable tables list"""
        return """
            QTreeWidget {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 4px;
                color: white;
            }
            QTreeWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QTreeWidget::item:hover:!selected {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                border-image: none;
                image: url(:/images/branch-closed);
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                border-image: none;
                image: url(:/images/branch-open);
            }
        """
        
    def handle_item_double_click(self, item, column):
        """Handle double-clicking on a tree item"""
        if not item:
            return
        
        # Check if it's a folder - toggle expand/collapse
        if self.is_folder_item(item):
            if item.isExpanded():
                item.setExpanded(False)
            else:
                item.setExpanded(True)
            return
            
        # For table items, get the table name
        table_name = self.get_table_name_from_item(item)
        
        # Check if this table needs reloading
        if table_name in self.tables_needing_reload:
            # Reload the table immediately without prompting
            if self.parent and hasattr(self.parent, 'reload_selected_table'):
                self.parent.reload_selected_table(table_name)
        
        # For non-folder items, handle showing the table preview
        if self.parent and hasattr(self.parent, 'show_table_preview'):
            self.parent.show_table_preview(item)
    
    def is_folder_item(self, item):
        """Check if an item is a folder"""
        return item.data(0, Qt.ItemDataRole.UserRole) == "folder"
    
    def get_table_name_from_item(self, item):
        """Extract the table name from an item (without the source info)"""
        if self.is_folder_item(item):
            return None
        
        return item.text(0).split(' (')[0]
    
    def startDrag(self, supportedActions):
        """Override startDrag to customize the drag data."""
        # Check for multiple selected items
        selected_items = self.selectedItems()
        if len(selected_items) > 1:
            # Only support dragging multiple items to the editor (not for folder management)
            # Filter out folder items
            table_items = [item for item in selected_items if not self.is_folder_item(item)]
            
            if not table_items:
                return
            
            # Extract table names
            table_names = [self.get_table_name_from_item(item) for item in table_items]
            table_names = [name for name in table_names if name]  # Remove None values
            
            if not table_names:
                return
                
            # Create mime data with comma-separated table names
            mime_data = QMimeData()
            mime_data.setText(", ".join(table_names))
            
            # Create drag object
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            
            # Create a visually appealing drag pixmap
            font = self.font()
            font.setBold(True)
            metrics = self.fontMetrics()
            
            # Build a preview label with limited number of tables
            display_names = table_names[:3]
            if len(table_names) > 3:
                display_text = f"{', '.join(display_names)} (+{len(table_names) - 3} more)"
            else:
                display_text = ", ".join(display_names)
                
            text_width = metrics.horizontalAdvance(display_text)
            text_height = metrics.height()
            
            # Make the pixmap large enough for the text plus padding and a small icon
            padding = 10
            pixmap = QPixmap(text_width + padding * 2 + 16, text_height + padding)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            # Begin painting
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw a nice rounded rectangle background
            bg_color = QColor(44, 62, 80, 220)  # Dark blue with transparency
            painter.setBrush(QBrush(bg_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, pixmap.width(), pixmap.height(), 5, 5)
            
            # Draw text
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(font)
            painter.drawText(int(padding + 16), int(text_height + (padding / 2) - 2), display_text)
            
            # Draw a small database icon (simulated)
            icon_x = padding / 2
            icon_y = (pixmap.height() - 12) / 2
            
            # Draw a simple database icon as a blue circle with lines
            table_icon_color = QColor("#3498DB")
            painter.setBrush(QBrush(table_icon_color))
            painter.setPen(Qt.GlobalColor.white)
            painter.drawEllipse(int(icon_x), int(icon_y), 12, 12)
            
            # Draw "table" lines inside the circle
            painter.setPen(Qt.GlobalColor.white)
            painter.drawLine(int(icon_x + 3), int(icon_y + 4), int(icon_x + 9), int(icon_y + 4))
            painter.drawLine(int(icon_x + 3), int(icon_y + 6), int(icon_x + 9), int(icon_y + 6))
            painter.drawLine(int(icon_x + 3), int(icon_y + 8), int(icon_x + 9), int(icon_y + 8))
            
            painter.end()
            
            # Set the drag pixmap
            drag.setPixmap(pixmap)
            
            # Set hotspot to be at the top-left corner of the text
            drag.setHotSpot(QPoint(padding, pixmap.height() // 2))
            
            # Execute drag operation - only allow copy action for multiple tables
            drag.exec(Qt.DropAction.CopyAction)
            return
            
        # Single item drag (original functionality)
        item = self.currentItem()
        if not item:
            return
        
        # Don't start drag if it's a folder and we're in internal move mode
        if self.is_folder_item(item) and self.dragDropMode() == QTreeWidget.DragDropMode.InternalMove:
            super().startDrag(supportedActions)
            return
            
        # Extract the table name without the file info in parentheses
        table_name = self.get_table_name_from_item(item)
        if not table_name:
            return
        
        # Create mime data with the table name
        mime_data = QMimeData()
        mime_data.setText(table_name)
        
        # Add additional information about the item for internal drags
        full_text = item.text(0)
        if ' (' in full_text:
            source = full_text.split(' (')[1][:-1]  # Get the source part
            needs_reload = table_name in self.tables_needing_reload
            
            # Store additional metadata in mime data
            mime_data.setData('application/x-sqlshell-tablename', table_name.encode())
            mime_data.setData('application/x-sqlshell-source', source.encode())
            mime_data.setData('application/x-sqlshell-needs-reload', str(needs_reload).encode())
        
        # Create drag object
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        # Create a visually appealing drag pixmap
        font = self.font()
        font.setBold(True)
        metrics = self.fontMetrics()
        text_width = metrics.horizontalAdvance(table_name)
        text_height = metrics.height()
        
        # Make the pixmap large enough for the text plus padding and a small icon
        padding = 10
        pixmap = QPixmap(text_width + padding * 2 + 16, text_height + padding)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Begin painting
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw a nice rounded rectangle background
        bg_color = QColor(44, 62, 80, 220)  # Dark blue with transparency
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, pixmap.width(), pixmap.height(), 5, 5)
        
        # Draw text
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(font)
        painter.drawText(int(padding + 16), int(text_height + (padding / 2) - 2), table_name)
        
        # Draw a small database icon (simulated)
        icon_x = padding / 2
        icon_y = (pixmap.height() - 12) / 2
        
        # Draw a simple database icon as a blue circle with lines
        table_icon_color = QColor("#3498DB")
        painter.setBrush(QBrush(table_icon_color))
        painter.setPen(Qt.GlobalColor.white)
        painter.drawEllipse(int(icon_x), int(icon_y), 12, 12)
        
        # Draw "table" lines inside the circle
        painter.setPen(Qt.GlobalColor.white)
        painter.drawLine(int(icon_x + 3), int(icon_y + 4), int(icon_x + 9), int(icon_y + 4))
        painter.drawLine(int(icon_x + 3), int(icon_y + 6), int(icon_x + 9), int(icon_y + 6))
        painter.drawLine(int(icon_x + 3), int(icon_y + 8), int(icon_x + 9), int(icon_y + 8))
        
        painter.end()
        
        # Set the drag pixmap
        drag.setPixmap(pixmap)
        
        # Set hotspot to be at the top-left corner of the text
        drag.setHotSpot(QPoint(padding, pixmap.height() // 2))
        
        # Execute drag operation
        result = drag.exec(supportedActions)
        
        # Optional: add a highlight effect after dragging
        if result == Qt.DropAction.CopyAction and item:
            # Briefly highlight the dragged item
            orig_bg = item.background(0)
            item.setBackground(0, QBrush(QColor(26, 188, 156, 100)))  # Light green highlight
            
            # Reset after a short delay
            QTimer.singleShot(300, lambda: item.setBackground(0, orig_bg))
    
    def dropEvent(self, event):
        """Override drop event to handle dropping items into folders"""
        if event.source() == self:  # Internal drop
            drop_pos = event.position().toPoint()
            target_item = self.itemAt(drop_pos)
            current_item = self.currentItem()
            
            # Only proceed if we have both a current item and a target
            if current_item and not self.is_folder_item(current_item):
                # If dropping onto a folder, move the item to that folder
                if target_item and self.is_folder_item(target_item):
                    # Move the item to the target folder
                    self.move_item_to_folder(current_item, target_item)
                    
                    # Get table name for status message
                    table_name = self.get_table_name_from_item(current_item)
                    folder_name = target_item.text(0)
                    
                    # Emit signal for successful drop
                    self.itemDropped.emit(table_name, folder_name, True)
                    
                    # Show status message
                    if self.parent:
                        self.parent.statusBar().showMessage(f'Moved table "{table_name}" to folder "{folder_name}"')
                    
                    # Expand the folder
                    target_item.setExpanded(True)
                    
                    # Prevent standard drop behavior as we've handled it
                    event.accept()
                    return
                elif not target_item:
                    # Dropping onto empty space - move to root
                    parent = current_item.parent()
                    if parent and self.is_folder_item(parent):
                        # Get table name for status message
                        table_name = self.get_table_name_from_item(current_item)
                        
                        # Get additional information from the item
                        full_text = current_item.text(0)
                        source = full_text.split(' (')[1][:-1] if ' (' in full_text else ""
                        needs_reload = table_name in self.tables_needing_reload
                        
                        # Remove from current folder
                        parent.removeChild(current_item)
                        
                        # Add to root
                        self.add_table_item(table_name, source, needs_reload)
                        
                        # Emit signal for successful drop to root
                        self.itemDropped.emit(table_name, "", True)
                        
                        # Show status message
                        if self.parent:
                            self.parent.statusBar().showMessage(f'Moved table "{table_name}" to root')
                        
                        # Prevent standard drop behavior
                        event.accept()
                        return
            # For folders, let the default behavior handle it
            elif current_item and self.is_folder_item(current_item):
                # Use standard behavior for folders
                super().dropEvent(event)
                
                # Show feedback
                if target_item and self.is_folder_item(target_item):
                    # Expand the folder
                    target_item.setExpanded(True)
                    
                return
                
        # Try to extract table information from mime data for external drags
        elif event.mimeData().hasText() and target_item and self.is_folder_item(target_item):
            # This handles drops from other widgets
            mime_data = event.mimeData()
            
            # Try to get additional information from custom mime types
            if mime_data.hasFormat('application/x-sqlshell-tablename'):
                # This is a drag from another part of the application with our custom data
                table_name = bytes(mime_data.data('application/x-sqlshell-tablename')).decode()
                source = bytes(mime_data.data('application/x-sqlshell-source')).decode()
                needs_reload_str = bytes(mime_data.data('application/x-sqlshell-needs-reload')).decode()
                needs_reload = needs_reload_str.lower() == 'true'
                
                # Create a new item in the target folder
                item = QTreeWidgetItem(target_item)
                item.setText(0, f"{table_name} ({source})")
                item.setData(0, Qt.ItemDataRole.UserRole, "table")
                
                # Set appropriate icon based on reload status
                if needs_reload:
                    self.tables_needing_reload.add(table_name)
                    item.setIcon(0, QIcon.fromTheme("view-refresh"))
                    item.setToolTip(0, f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
                else:
                    item.setIcon(0, QIcon.fromTheme("x-office-spreadsheet"))
                
                # Set item flags
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
                
                # Expand the folder
                target_item.setExpanded(True)
                
                # Emit signal for successful drop
                self.itemDropped.emit(table_name, target_item.text(0), True)
                
                # Show status message
                if self.parent:
                    self.parent.statusBar().showMessage(f'Added table "{table_name}" to folder "{target_item.text(0)}"')
                
                event.accept()
                return
            else:
                # Just a plain text drop - try to use it as a table name
                table_name = mime_data.text()
                
                # Find if this table exists in our list
                existing_item = self.find_table_item(table_name)
                if existing_item:
                    # Move existing item to the target folder
                    self.move_item_to_folder(existing_item, target_item)
                    
                    # Emit signal for successful drop
                    self.itemDropped.emit(table_name, target_item.text(0), True)
                    
                    # Show status message
                    if self.parent:
                        self.parent.statusBar().showMessage(f'Moved table "{table_name}" to folder "{target_item.text(0)}"')
                    
                    event.accept()
                    return
        
        # Reset folder highlights before default handling
        self._reset_folder_highlights()
        
        # For other cases, use the standard behavior
        super().dropEvent(event)
    
    def dragEnterEvent(self, event):
        """Handle drag enter events with visual feedback"""
        # Accept the event to allow internal drags
        if event.source() == self:
            event.acceptProposedAction()
        else:
            # Let parent class handle external drags
            super().dragEnterEvent(event)
    
    def dragMoveEvent(self, event):
        """Handle drag move with visual feedback for potential drop targets"""
        if event.source() == self:
            # Show visual feedback when hovering over folders
            drop_pos = event.position().toPoint()
            target_item = self.itemAt(drop_pos)
            
            # Reset all folder backgrounds
            self._reset_folder_highlights()
            
            # Highlight the current target folder if any
            if target_item and self.is_folder_item(target_item):
                target_item.setBackground(0, QBrush(QColor(52, 152, 219, 50)))  # Light blue highlight
            
            event.acceptProposedAction()
        else:
            # Let parent class handle external drags
            super().dragMoveEvent(event)
    
    def _reset_folder_highlights(self):
        """Reset highlights on all folder items"""
        def reset_item(item):
            if not item:
                return
                
            if self.is_folder_item(item):
                item.setBackground(0, QBrush())  # Clear background
                
            # Process children if this is a folder
            for i in range(item.childCount()):
                reset_item(item.child(i))
        
        # Reset all top-level items
        for i in range(self.topLevelItemCount()):
            reset_item(self.topLevelItem(i))
    
    def dragLeaveEvent(self, event):
        """Handle drag leave events by resetting visual feedback"""
        self._reset_folder_highlights()
        super().dragLeaveEvent(event)
    
    def get_folder_by_name(self, folder_name):
        """Find a folder by name or create it if it doesn't exist"""
        # Look for existing folder
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if self.is_folder_item(item) and item.text(0) == folder_name:
                return item
        
        # Create new folder if not found
        return self.create_folder(folder_name)
    
    def create_folder(self, folder_name):
        """Create a new folder in the tree"""
        folder = QTreeWidgetItem(self)
        folder.setText(0, folder_name)
        folder.setIcon(0, QIcon.fromTheme("folder"))
        # Store item type as folder
        folder.setData(0, Qt.ItemDataRole.UserRole, "folder")
        # Make folder text bold
        font = folder.font(0)
        font.setBold(True)
        folder.setFont(0, font)
        # Set folder flags (can drop onto)
        folder.setFlags(folder.flags() | Qt.ItemFlag.ItemIsDropEnabled)
        # Start expanded
        folder.setExpanded(True)
        return folder
    
    def add_table_item(self, table_name, source, needs_reload=False, folder_name=None):
        """Add a table item with optional reload icon, optionally in a folder"""
        item_text = f"{table_name} ({source})"
        
        # Determine parent (folder or root)
        parent = self
        if folder_name:
            parent = self.get_folder_by_name(folder_name)
        
        # Create the item
        item = QTreeWidgetItem(parent)
        item.setText(0, item_text)
        item.setData(0, Qt.ItemDataRole.UserRole, "table")
        
        # Set appropriate icon
        if needs_reload:
            # Add to set of tables needing reload
            self.tables_needing_reload.add(table_name)
            # Set an icon for tables that need reloading
            item.setIcon(0, QIcon.fromTheme("view-refresh"))
            # Add tooltip to indicate the table needs to be reloaded
            item.setToolTip(0, f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
        else:
            # Regular table icon
            item.setIcon(0, QIcon.fromTheme("x-office-spreadsheet"))
        
        # Make item draggable but not a drop target
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
        
        # If we added to a folder, make sure it's expanded
        if folder_name:
            parent.setExpanded(True)
            
        return item
    
    def show_context_menu(self, position):
        """Show context menu for the tree widget"""
        item = self.itemAt(position)
        
        # Create the menu
        menu = QMenu(self)
        
        if not item:
            # Clicked on empty space - show menu for creating a folder
            new_folder_action = menu.addAction(QIcon.fromTheme("folder-new"), "New Folder")
            expand_all_action = menu.addAction(QIcon.fromTheme("view-fullscreen"), "Expand All")
            collapse_all_action = menu.addAction(QIcon.fromTheme("view-restore"), "Collapse All")
            
            action = menu.exec(QCursor.pos())
            
            if action == new_folder_action:
                self.create_new_folder()
            elif action == expand_all_action:
                self.expandAll()
            elif action == collapse_all_action:
                self.collapseAll()
                
            return
        
        if self.is_folder_item(item):
            # Folder context menu
            new_subfolder_action = menu.addAction(QIcon.fromTheme("folder-new"), "New Subfolder")
            menu.addSeparator()
            rename_folder_action = menu.addAction("Rename Folder")
            expand_action = None
            collapse_action = None
            
            if item.childCount() > 0:
                menu.addSeparator()
                expand_action = menu.addAction("Expand")
                collapse_action = menu.addAction("Collapse")
            
            menu.addSeparator()
            delete_folder_action = menu.addAction(QIcon.fromTheme("edit-delete"), "Delete Folder")
            
            action = menu.exec(QCursor.pos())
            
            if action == new_subfolder_action:
                self.create_new_folder(item)
            elif action == rename_folder_action:
                self.rename_folder(item)
            elif action == delete_folder_action:
                self.delete_folder(item)
            elif expand_action and action == expand_action:
                item.setExpanded(True)
            elif collapse_action and action == collapse_action:
                item.setExpanded(False)
                
        else:
            # Table item context menu - defer to parent's context menu handling
            if self.parent and hasattr(self.parent, 'show_tables_context_menu'):
                # Call the main application's context menu handler
                self.parent.show_tables_context_menu(position)
    
    def create_new_folder(self, parent_item=None):
        """Create a new folder, optionally as a subfolder"""
        folder_name, ok = QInputDialog.getText(
            self, 
            "New Folder", 
            "Enter folder name:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and folder_name:
            if parent_item and self.is_folder_item(parent_item):
                # Create subfolder
                subfolder = QTreeWidgetItem(parent_item)
                subfolder.setText(0, folder_name)
                subfolder.setIcon(0, QIcon.fromTheme("folder"))
                subfolder.setData(0, Qt.ItemDataRole.UserRole, "folder")
                # Make folder text bold
                font = subfolder.font(0)
                font.setBold(True)
                subfolder.setFont(0, font)
                # Set folder flags
                subfolder.setFlags(subfolder.flags() | Qt.ItemFlag.ItemIsDropEnabled)
                # Expand parent
                parent_item.setExpanded(True)
                return subfolder
            else:
                # Create top-level folder
                return self.create_folder(folder_name)
    
    def rename_folder(self, folder_item):
        """Rename a folder"""
        if not self.is_folder_item(folder_item):
            return
            
        current_name = folder_item.text(0)
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Folder",
            "Enter new folder name:",
            QLineEdit.EchoMode.Normal,
            current_name
        )
        
        if ok and new_name:
            folder_item.setText(0, new_name)
    
    def delete_folder(self, folder_item):
        """Delete a folder and its contents"""
        if not self.is_folder_item(folder_item):
            return
            
        # Confirmation dialog
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Delete Folder")
        folder_name = folder_item.text(0)
        msg_box.setText(f"Are you sure you want to delete folder '{folder_name}'?")
        
        if folder_item.childCount() > 0:
            msg_box.setInformativeText("The folder contains items that will also be deleted.")
        
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            # Get the parent (could be the tree widget or another folder)
            parent = folder_item.parent()
            if parent:
                parent.removeChild(folder_item)
            else:
                # Top-level item
                index = self.indexOfTopLevelItem(folder_item)
                if index >= 0:
                    self.takeTopLevelItem(index)
    
    def move_item_to_folder(self, item, target_folder):
        """Move an item to a different folder"""
        if not item or not target_folder:
            return
        
        # Get table name before moving
        table_name = self.get_table_name_from_item(item)
        folder_name = target_folder.text(0)
            
        # Clone the item
        clone = item.clone()
        
        # Add to new parent
        target_folder.addChild(clone)
        
        # Remove original
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            # Top-level item
            index = self.indexOfTopLevelItem(item)
            if index >= 0:
                self.takeTopLevelItem(index)
        
        # Expand target folder
        target_folder.setExpanded(True)
        
        # Select the moved item
        self.setCurrentItem(clone)
        
        # Emit signal for successful move, if we were able to get the table name
        if table_name:
            self.itemDropped.emit(table_name, folder_name, True)
    
    def clear(self):
        """Override clear to also reset the tables_needing_reload set"""
        super().clear()
        self.tables_needing_reload.clear()
        
    def mark_table_reloaded(self, table_name):
        """Mark a table as reloaded by removing its icon"""
        if table_name in self.tables_needing_reload:
            self.tables_needing_reload.remove(table_name)
            
        # Find and update the item (across all folders)
        table_item = self.find_table_item(table_name)
        if table_item:
            table_item.setIcon(0, QIcon.fromTheme("x-office-spreadsheet"))
            table_item.setToolTip(0, "")
                
    def mark_table_needs_reload(self, table_name):
        """Mark a table as needing reload by adding an icon"""
        self.tables_needing_reload.add(table_name)
        
        # Find and update the item (across all folders)
        table_item = self.find_table_item(table_name)
        if table_item:
            table_item.setIcon(0, QIcon.fromTheme("view-refresh"))
            table_item.setToolTip(0, f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
                
    def is_table_loaded(self, table_name):
        """Check if a table is loaded (not needing reload)"""
        return table_name not in self.tables_needing_reload

    def find_table_item(self, table_name):
        """Find a table item by name across all folders"""
        # Helper function to recursively search the tree
        def search_item(parent_item):
            # If parent_item is None, search top-level items
            if parent_item is None:
                for i in range(self.topLevelItemCount()):
                    top_item = self.topLevelItem(i)
                    result = search_item(top_item)
                    if result:
                        return result
                return None
                
            # Check if current item is the target table
            if not self.is_folder_item(parent_item):
                item_table_name = self.get_table_name_from_item(parent_item)
                if item_table_name == table_name:
                    return parent_item
            
            # Recursively search children if it's a folder
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                result = search_item(child)
                if result:
                    return result
                    
            return None
        
        # Start the recursive search
        return search_item(None)


class TestTableListParent(QMainWindow):
    """Test class to serve as parent for the DraggableTablesList during testing"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table List Test - Drag & Drop Tables to Folders")
        self.setGeometry(100, 100, 400, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Add header
        header = QLabel("TABLES")
        header.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        main_layout.addWidget(header)
        
        # Create and add the tables list
        self.tables_list = DraggableTablesList(self)
        main_layout.addWidget(self.tables_list)
        
        # Add status display
        self.status_frame = QFrame()
        self.status_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.status_frame.setStyleSheet("background-color: rgba(255,255,255,0.1); border-radius: 4px; padding: 8px;")
        status_layout = QVBoxLayout(self.status_frame)
        
        self.status_label = QLabel("Try dragging tables between folders!")
        self.status_label.setStyleSheet("color: white;")
        status_layout.addWidget(self.status_label)
        
        main_layout.addWidget(self.status_frame)
        
        # Create info section
        info_label = QLabel(
            "• Drag tables to folders for organization\n"
            "• Drag tables out of folders to root\n"
            "• Double-click folders to expand/collapse\n"
            "• Right-click for context menu options\n"
            "• Visual feedback shows valid drop targets"
        )
        info_label.setStyleSheet("color: #3498DB; background-color: rgba(255,255,255,0.1); padding: 10px; border-radius: 4px;")
        main_layout.addWidget(info_label)
        
        # Apply dark styling to the main window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2C3E50;
            }
            QLabel {
                color: white;
            }
        """)
        
        # Populate with sample data
        self.add_sample_data()
        
        # Connect to status updates
        self.tables_list.itemDropped.connect(self.update_drop_status)
        
    def add_sample_data(self):
        """Add sample data to the table list"""
        # Create some folders
        sales_folder = self.tables_list.create_folder("Sales Data")
        analytics_folder = self.tables_list.create_folder("Analytics")
        reports_folder = self.tables_list.create_folder("Reports")
        
        # Add some tables to root
        self.tables_list.add_table_item("customers", "sample.xlsx")
        self.tables_list.add_table_item("products", "database")
        self.tables_list.add_table_item("employees", "hr.xlsx")
        
        # Add tables to folders
        self.tables_list.add_table_item("orders", "orders.csv", folder_name="Sales Data")
        self.tables_list.add_table_item("sales_2023", "sales.parquet", needs_reload=True, folder_name="Sales Data")
        
        self.tables_list.add_table_item("analytics_data", "analytics.csv", needs_reload=True, folder_name="Analytics")
        self.tables_list.add_table_item("inventory", "query_result", folder_name="Analytics")
        
        # Message to get started
        self.statusBar().showMessage("Try dragging tables between folders and to root area", 5000)
        
    def update_drop_status(self, source_item, target_folder, success):
        """Update status label with drag and drop information"""
        if success:
            if source_item and target_folder:
                self.status_label.setText(f"Moved '{source_item}' to folder '{target_folder}'")
            elif source_item:
                self.status_label.setText(f"Moved '{source_item}' to root")
        else:
            self.status_label.setText("Drop operation failed")
    
    def reload_selected_table(self, table_name):
        """Mock implementation of reload_selected_table for testing"""
        # Update status
        self.status_label.setText(f"Reloaded table: {table_name}")
        
        # Mark the table as reloaded
        self.tables_list.mark_table_reloaded(table_name)
        
        # Show confirmation
        QMessageBox.information(
            self,
            "Table Reloaded",
            f"Table '{table_name}' has been reloaded successfully!",
            QMessageBox.StandardButton.Ok
        )
        
    def show_table_preview(self, item):
        """Mock implementation of show_table_preview for testing"""
        if not item:
            return
            
        # Get table name
        table_name = item.text(0).split(' (')[0]
        
        # Update status
        self.status_label.setText(f"Showing preview of: {table_name}")
        
    def show_tables_context_menu(self, position):
        """Mock implementation of context menu for table items"""
        item = self.tables_list.itemAt(position)
        if not item or self.tables_list.is_folder_item(item):
            return  # Let the tree widget handle folders
            
        # Get table name
        table_name = item.text(0).split(' (')[0]
        
        # Create context menu
        context_menu = QMenu(self)
        select_action = context_menu.addAction("Select (Test)")
        view_action = context_menu.addAction("View (Test)")
        
        # Check if table needs reloading and add appropriate action
        if table_name in self.tables_list.tables_needing_reload:
            reload_action = context_menu.addAction("Reload Table")
            reload_action.setIcon(QIcon.fromTheme("view-refresh"))
        else:
            reload_action = context_menu.addAction("Refresh")
            
        # Add move to folder submenu
        move_menu = context_menu.addMenu("Move to Folder")
        
        # Add folders to the move menu
        for i in range(self.tables_list.topLevelItemCount()):
            top_item = self.tables_list.topLevelItem(i)
            if self.tables_list.is_folder_item(top_item):
                folder_action = move_menu.addAction(top_item.text(0))
                folder_action.setData(top_item)
        
        context_menu.addSeparator()
        delete_action = context_menu.addAction("Delete (Test)")
        
        # Show the menu
        action = context_menu.exec(QCursor.pos())
        
        # Handle the action
        if action == reload_action:
            self.reload_selected_table(table_name)
        elif action == select_action:
            self.status_label.setText(f"Selected: {table_name}")
        elif action == view_action:
            self.status_label.setText(f"Viewing: {table_name}")
        elif action == delete_action:
            self.status_label.setText(f"Deleted: {table_name}")
            # Actually remove the item as an example
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.tables_list.indexOfTopLevelItem(item)
                if index >= 0:
                    self.tables_list.takeTopLevelItem(index)
        elif action and action.parent() == move_menu:
            # Get the target folder from action data
            target_folder = action.data()
            if target_folder:
                self.tables_list.move_item_to_folder(item, target_folder)
                self.status_label.setText(f"Moved {table_name} to {target_folder.text(0)}")
    
    def statusBar(self):
        """Override statusBar to update our status label"""
        return self
    
    def showMessage(self, message, timeout=0):
        """Implement showMessage to work with statusBar() call"""
        self.status_label.setText(message)
        
        # If timeout is specified, schedule a reset
        if timeout > 0:
            QTimer.singleShot(timeout, lambda: self.status_label.setText("Try dragging tables between folders!"))


def main():
    """Run the test application"""
    app = QApplication(sys.argv)
    
    # Create and show the test window
    test_window = TestTableListParent()
    test_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 