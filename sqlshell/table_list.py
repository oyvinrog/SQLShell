import os
import sys
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QListWidget, QListWidgetItem, 
                            QMessageBox, QMainWindow, QVBoxLayout, QLabel, 
                            QWidget, QHBoxLayout, QFrame)
from PyQt6.QtCore import Qt, QPoint, QMimeData, QTimer
from PyQt6.QtGui import QIcon, QDrag, QPainter, QColor, QBrush, QPixmap, QFont

class DraggableTablesList(QListWidget):
    """Custom QListWidget that provides better drag functionality for table names."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        
        # Apply custom styling
        self.setStyleSheet(self.get_stylesheet())
        
        # Store tables that need reloading
        self.tables_needing_reload = set()
        
        # Connect double-click signal to handle reloading
        self.itemDoubleClicked.connect(self.handle_item_double_click)
        
    def get_stylesheet(self):
        """Get the stylesheet for the draggable tables list"""
        return """
            QListWidget {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 4px;
                color: white;
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QListWidget::item:hover:!selected {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """
        
    def handle_item_double_click(self, item):
        """Handle double-clicking on a table item"""
        if not item:
            return
            
        table_name = item.text().split(' (')[0]
        
        # Check if this table needs reloading
        if table_name in self.tables_needing_reload:
            # Prompt user to reload the table
            reply = QMessageBox.question(
                self,
                "Reload Table",
                f"The table '{table_name}' needs to be loaded. Load it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes and self.parent:
                # Call the parent's reload_selected_table method
                if hasattr(self.parent, 'reload_selected_table'):
                    self.parent.reload_selected_table(table_name)
                return
                
    def startDrag(self, supportedActions):
        """Override startDrag to customize the drag data."""
        item = self.currentItem()
        if not item:
            return
            
        # Extract the table name without the file info in parentheses
        table_name = item.text().split(' (')[0]
        
        # Create mime data with the table name
        mime_data = QMimeData()
        mime_data.setText(table_name)
        
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
            orig_bg = item.background()
            item.setBackground(QBrush(QColor(26, 188, 156, 100)))  # Light green highlight
            
            # Reset after a short delay
            QTimer.singleShot(300, lambda: item.setBackground(orig_bg))
            
    def add_table_item(self, table_name, source, needs_reload=False):
        """Add a table item with optional reload icon"""
        item_text = f"{table_name} ({source})"
        item = QListWidgetItem(item_text)
        
        if needs_reload:
            # Add to set of tables needing reload
            self.tables_needing_reload.add(table_name)
            # Set an icon for tables that need reloading
            item.setIcon(QIcon.fromTheme("view-refresh"))
            # Add tooltip to indicate the table needs to be reloaded
            item.setToolTip(f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
        
        self.addItem(item)
        return item
        
    def mark_table_reloaded(self, table_name):
        """Mark a table as reloaded by removing its icon"""
        if table_name in self.tables_needing_reload:
            self.tables_needing_reload.remove(table_name)
            
        # Find and update the item
        for i in range(self.count()):
            item = self.item(i)
            item_table_name = item.text().split(' (')[0]
            if item_table_name == table_name:
                item.setIcon(QIcon())  # Remove icon
                item.setToolTip("")  # Clear tooltip
                break
                
    def mark_table_needs_reload(self, table_name):
        """Mark a table as needing reload by adding an icon"""
        self.tables_needing_reload.add(table_name)
        
        # Find and update the item
        for i in range(self.count()):
            item = self.item(i)
            item_table_name = item.text().split(' (')[0]
            if item_table_name == table_name:
                item.setIcon(QIcon.fromTheme("view-refresh"))
                item.setToolTip(f"Table '{table_name}' needs to be loaded (double-click or use context menu)")
                break
                
    def is_table_loaded(self, table_name):
        """Check if a table is loaded (not needing reload)"""
        return table_name not in self.tables_needing_reload


class TestTableListParent(QMainWindow):
    """Test class to serve as parent for the DraggableTablesList during testing"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table List Test")
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
        
        self.status_label = QLabel("Double-click a table to see reload behavior")
        self.status_label.setStyleSheet("color: white;")
        status_layout.addWidget(self.status_label)
        
        main_layout.addWidget(self.status_frame)
        
        # Create info section
        info_label = QLabel(
            "Drag items to test drag behavior\n"
            "Double-click items marked with reload icon\n"
            "This is a test UI for the DraggableTablesList component"
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
        
    def add_sample_data(self):
        """Add sample data to the table list"""
        # Add some sample tables
        self.tables_list.add_table_item("customers", "sample.xlsx")
        self.tables_list.add_table_item("orders", "orders.csv")
        self.tables_list.add_table_item("products", "database")
        self.tables_list.add_table_item("sales_2023", "sales.parquet", needs_reload=True)
        self.tables_list.add_table_item("analytics_data", "analytics.csv", needs_reload=True)
        self.tables_list.add_table_item("inventory", "query_result")
        
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


def main():
    """Run the test application"""
    app = QApplication(sys.argv)
    
    # Create and show the test window
    test_window = TestTableListParent()
    test_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 