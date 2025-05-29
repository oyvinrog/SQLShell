import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QHeaderView, QTableWidget, QSplitter, QApplication, 
                             QToolButton, QMenu)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
import re
import pandas as pd
import numpy as np

from sqlshell.editor import SQLEditor
from sqlshell.syntax_highlighter import SQLSyntaxHighlighter
from sqlshell.ui import FilterHeader
from sqlshell.styles import get_row_count_label_stylesheet
from sqlshell.editor_integration import integrate_execution_functionality

class QueryTab(QWidget):
    def __init__(self, parent, results_title="RESULTS"):
        super().__init__()
        self.parent = parent
        self.current_df = None
        self.filter_widgets = []
        self.results_title_text = results_title
        self.init_ui()
        
    def init_ui(self):
        """Initialize the tab's UI components"""
        # Set main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for query and results
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(8)
        self.splitter.setChildrenCollapsible(False)
        
        # Top part - Query section
        query_widget = QFrame()
        query_widget.setObjectName("content_panel")
        query_layout = QVBoxLayout(query_widget)
        query_layout.setContentsMargins(16, 16, 16, 16)
        query_layout.setSpacing(12)
        
        # Query input
        self.query_edit = SQLEditor()
        # Apply syntax highlighting to the query editor
        self.sql_highlighter = SQLSyntaxHighlighter(self.query_edit.document())
        
        # Integrate F5/F9 execution functionality
        self.execution_integration = integrate_execution_functionality(
            self.query_edit, 
            self._execute_query_callback
        )
        
        # Ensure a default completer is available
        if not self.query_edit.completer:
            from PyQt6.QtCore import QStringListModel
            from PyQt6.QtWidgets import QCompleter
            
            # Create a basic completer with SQL keywords if one doesn't exist
            if hasattr(self.query_edit, 'all_sql_keywords'):
                model = QStringListModel(self.query_edit.all_sql_keywords)
                completer = QCompleter()
                completer.setModel(model)
                self.query_edit.set_completer(completer)
        
        # Connect keyboard events for direct handling of Ctrl+Enter
        self.query_edit.installEventFilter(self)
        
        query_layout.addWidget(self.query_edit)
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.execute_btn = QPushButton('Execute Query')
        self.execute_btn.setObjectName("primary_button")
        self.execute_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.execute_btn.clicked.connect(self.execute_query)
        
        # Add F5/F9 buttons for clarity
        self.execute_all_btn = QPushButton('F5 - Execute All')
        self.execute_all_btn.setToolTip('Execute all statements (F5)')
        self.execute_all_btn.clicked.connect(self.execute_all_statements)
        
        self.execute_current_btn = QPushButton('F9 - Execute Current')
        self.execute_current_btn.setToolTip('Execute current statement (F9)')
        self.execute_current_btn.clicked.connect(self.execute_current_statement)
        
        self.clear_btn = QPushButton('Clear')
        self.clear_btn.clicked.connect(self.clear_query)
        
        button_layout.addWidget(self.execute_btn)
        button_layout.addWidget(self.execute_all_btn)
        button_layout.addWidget(self.execute_current_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        self.export_excel_btn = QPushButton('Export to Excel')
        self.export_excel_btn.setIcon(QIcon.fromTheme("x-office-spreadsheet"))
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        
        self.export_parquet_btn = QPushButton('Export to Parquet')
        self.export_parquet_btn.setIcon(QIcon.fromTheme("application-octet-stream"))
        self.export_parquet_btn.clicked.connect(self.export_to_parquet)
        
        button_layout.addWidget(self.export_excel_btn)
        button_layout.addWidget(self.export_parquet_btn)
        
        query_layout.addLayout(button_layout)
        
        # Bottom part - Results section
        results_widget = QWidget()
        self.results_layout = QVBoxLayout(results_widget)
        self.results_layout.setContentsMargins(16, 16, 16, 16)
        self.results_layout.setSpacing(12)
        
        # Results header with row count
        header_layout = QHBoxLayout()
        self.results_title = QLabel(self.results_title_text)
        self.results_title.setObjectName("header_label")
        header_layout.addWidget(self.results_title)
        
        header_layout.addStretch()
        
        self.row_count_label = QLabel("")
        self.row_count_label.setStyleSheet(get_row_count_label_stylesheet())
        header_layout.addWidget(self.row_count_label)
        
        self.results_layout.addLayout(header_layout)
        
        # Add descriptive text about table interactions and new F5/F9 functionality
        help_text = QLabel("📊 <b>Table Interactions:</b> Double-click on a column header to add it to your query. Right-click for analytical capabilities. <b>🚀 Execution:</b> F5 executes all statements, F9 executes current statement (at cursor), Ctrl+Enter executes entire query.")
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #7FB3D5; font-size: 11px; margin: 5px 0; padding: 8px; background-color: #F8F9FA; border-radius: 4px;")
        self.results_layout.addWidget(help_text)
        
        # Results table with customized header
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        
        # Use custom FilterHeader for filtering
        header = FilterHeader(self.results_table)
        header.set_main_window(self.parent)  # Set reference to main window
        self.results_table.setHorizontalHeader(header)
        
        # Set table properties for better performance with large datasets
        self.results_table.setShowGrid(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.verticalHeader().setVisible(True)
        
        # Connect double-click signal to handle column selection
        self.results_table.cellDoubleClicked.connect(self.handle_cell_double_click)
        
        # Connect header click signal to handle column header selection
        self.results_table.horizontalHeader().sectionClicked.connect(self.handle_header_click)
        
        # Connect header double-click signal to add column to query
        self.results_table.horizontalHeader().sectionDoubleClicked.connect(self.handle_header_double_click)
        
        self.results_layout.addWidget(self.results_table)
        
        # Add widgets to splitter
        self.splitter.addWidget(query_widget)
        self.splitter.addWidget(results_widget)
        
        # Set initial sizes - default 40% query, 60% results
        # This will be better for most uses of the app
        screen = QApplication.primaryScreen()
        if screen:
            # Get available screen height
            available_height = screen.availableGeometry().height()
            # Calculate reasonable query pane size (25-35% depending on screen size)
            if available_height >= 1080:  # Large screens
                query_height = int(available_height * 0.3)  # 30% for query area
                self.splitter.setSizes([query_height, available_height - query_height])
            else:  # Smaller screens
                self.splitter.setSizes([300, 500])  # Default values for smaller screens
        else:
            # Fallback to fixed values if screen detection fails
            self.splitter.setSizes([300, 500])
        
        main_layout.addWidget(self.splitter)
        
    def get_query_text(self):
        """Get the current query text"""
        return self.query_edit.toPlainText()
        
    def set_query_text(self, text):
        """Set the query text"""
        self.query_edit.setPlainText(text)
        
    def execute_query(self):
        """Execute the current query"""
        if hasattr(self.parent, 'execute_query'):
            self.parent.execute_query()
        
    def clear_query(self):
        """Clear the query editor"""
        if hasattr(self.parent, 'clear_query'):
            self.parent.clear_query()
        
    def export_to_excel(self):
        """Export results to Excel"""
        if hasattr(self.parent, 'export_to_excel'):
            self.parent.export_to_excel()
        
    def export_to_parquet(self):
        """Export results to Parquet"""
        if hasattr(self.parent, 'export_to_parquet'):
            self.parent.export_to_parquet()
            
    def eventFilter(self, obj, event):
        """Event filter to intercept Ctrl+Enter and send it to the main window"""
        from PyQt6.QtCore import QEvent, Qt
        
        # Check if it's a key press event
        if event.type() == QEvent.Type.KeyPress:
            # Check for Ctrl+Enter specifically
            if (event.key() == Qt.Key.Key_Return and 
                event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                
                # Hide any autocomplete popup if it's visible
                if hasattr(obj, 'completer') and obj.completer and obj.completer.popup().isVisible():
                    obj.completer.popup().hide()
                
                # Execute the query via the parent (main window)
                if hasattr(self.parent, 'execute_query'):
                    self.parent.execute_query()
                    # Mark event as handled
                    return True
                    
        # Default - let the event propagate normally
        return super().eventFilter(obj, event)

    def format_sql(self):
        """Format the SQL query for better readability"""
        from sqlshell.utils.sql_formatter import format_sql
        
        # Get current text
        current_text = self.query_edit.toPlainText()
        if not current_text.strip():
            return
            
        try:
            # Format the SQL
            formatted_sql = format_sql(current_text)
            
            # Replace the text
            self.query_edit.setPlainText(formatted_sql)
            self.parent.statusBar().showMessage('SQL formatted successfully')
        except Exception as e:
            self.parent.statusBar().showMessage(f'Error formatting SQL: {str(e)}')
    
    def show_header_context_menu(self, position):
        """Show context menu for header columns"""
        # Get the column index
        idx = self.results_table.horizontalHeader().logicalIndexAt(position)
        if idx < 0:
            return
            
        # Create context menu
        menu = QMenu(self)
        header = self.results_table.horizontalHeader()
        
        # Get column name
        col_name = self.results_table.horizontalHeaderItem(idx).text()
        
        # Check if the column name needs quoting (contains spaces or special characters)
        quoted_col_name = col_name
        if re.search(r'[\s\W]', col_name) and not col_name.startswith('"') and not col_name.endswith('"'):
            quoted_col_name = f'"{col_name}"'
        
        # Add actions
        copy_col_name_action = menu.addAction(f"Copy '{col_name}'")
        menu.addSeparator()
        
        # Check if we have a FilterHeader
        if isinstance(header, FilterHeader):
            # Check if this column has a bar chart
            has_bar = idx in header.columns_with_bars
            
            # Add toggle bar chart action
            if not has_bar:
                bar_action = menu.addAction("Add Bar Chart")
            else:
                bar_action = menu.addAction("Remove Bar Chart")
        
            # Sort options
            menu.addSeparator()
        
        sort_asc_action = menu.addAction("Sort Ascending")
        sort_desc_action = menu.addAction("Sort Descending")
        
        # Filter options if we have data
        if self.results_table.rowCount() > 0:
            menu.addSeparator()
            sel_distinct_action = menu.addAction(f"SELECT DISTINCT {quoted_col_name}")
            count_distinct_action = menu.addAction(f"COUNT DISTINCT {quoted_col_name}")
            group_by_action = menu.addAction(f"GROUP BY {quoted_col_name}")
            
        # SQL generation submenu
        menu.addSeparator()
        sql_menu = menu.addMenu("Generate SQL")
        select_col_action = sql_menu.addAction(f"SELECT {quoted_col_name}")
        filter_col_action = sql_menu.addAction(f"WHERE {quoted_col_name} = ?")
        explain_action = menu.addAction(f"Explain Column")
        encode_action = menu.addAction(f"One-Hot Encode")
        
        # Execute the menu
        action = menu.exec(header.mapToGlobal(position))
        
        # Handle actions
        if action == copy_col_name_action:
            QApplication.clipboard().setText(col_name)
            self.parent.statusBar().showMessage(f"Copied '{col_name}' to clipboard")
        
        elif action == explain_action:
            # Call the explain column method on the parent
            if hasattr(self.parent, 'explain_column'):
                self.parent.explain_column(col_name)
                
        elif action == encode_action:
            # Call the encode text method on the parent
            if hasattr(self.parent, 'encode_text'):
                self.parent.encode_text(col_name)
        
        elif action == sort_asc_action:
            self.results_table.sortItems(idx, Qt.SortOrder.AscendingOrder)
            self.parent.statusBar().showMessage(f"Sorted by '{col_name}' (ascending)")
            
        elif action == sort_desc_action:
            self.results_table.sortItems(idx, Qt.SortOrder.DescendingOrder)
            self.parent.statusBar().showMessage(f"Sorted by '{col_name}' (descending)")
            
        elif isinstance(header, FilterHeader) and action == bar_action:
            # Toggle bar chart
            header.toggle_bar_chart(idx)
            if idx in header.columns_with_bars:
                self.parent.statusBar().showMessage(f"Added bar chart for '{col_name}'")
            else:
                self.parent.statusBar().showMessage(f"Removed bar chart for '{col_name}'")
                
        elif 'sel_distinct_action' in locals() and action == sel_distinct_action:
            new_query = f"SELECT DISTINCT {quoted_col_name}\nFROM "
            if self.current_df is not None and hasattr(self.current_df, '_query_source'):
                table_name = getattr(self.current_df, '_query_source')
                new_query += f"{table_name}\n"
            else:
                new_query += "[table_name]\n"
            new_query += "ORDER BY 1"
            self.set_query_text(new_query)
            self.parent.statusBar().showMessage(f"Created SELECT DISTINCT query for '{col_name}'")
            
        elif 'count_distinct_action' in locals() and action == count_distinct_action:
            new_query = f"SELECT COUNT(DISTINCT {quoted_col_name}) AS distinct_{col_name.replace(' ', '_')}\nFROM "
            if self.current_df is not None and hasattr(self.current_df, '_query_source'):
                table_name = getattr(self.current_df, '_query_source')
                new_query += f"{table_name}"
            else:
                new_query += "[table_name]"
            self.set_query_text(new_query)
            self.parent.statusBar().showMessage(f"Created COUNT DISTINCT query for '{col_name}'")
            
        elif 'group_by_action' in locals() and action == group_by_action:
            new_query = f"SELECT {quoted_col_name}, COUNT(*) AS count\nFROM "
            if self.current_df is not None and hasattr(self.current_df, '_query_source'):
                table_name = getattr(self.current_df, '_query_source')
                new_query += f"{table_name}"
            else:
                new_query += "[table_name]"
            new_query += f"\nGROUP BY {quoted_col_name}\nORDER BY count DESC"
            self.set_query_text(new_query)
            self.parent.statusBar().showMessage(f"Created GROUP BY query for '{col_name}'")
            
        elif action == select_col_action:
            new_query = f"SELECT {quoted_col_name}\nFROM "
            if self.current_df is not None and hasattr(self.current_df, '_query_source'):
                table_name = getattr(self.current_df, '_query_source')
                new_query += f"{table_name}"
            else:
                new_query += "[table_name]"
            self.set_query_text(new_query)
            self.parent.statusBar().showMessage(f"Created SELECT query for '{col_name}'")
            
        elif action == filter_col_action:
            current_text = self.get_query_text()
            if current_text and "WHERE" in current_text.upper():
                # Add as AND condition
                lines = current_text.splitlines()
                for i, line in enumerate(lines):
                    if "WHERE" in line.upper() and "ORDER BY" not in line.upper() and "GROUP BY" not in line.upper():
                        lines[i] = f"{line} AND {quoted_col_name} = ?"
                        break
                self.set_query_text("\n".join(lines))
            else:
                # Create new query with WHERE clause
                new_query = f"SELECT *\nFROM "
                if self.current_df is not None and hasattr(self.current_df, '_query_source'):
                    table_name = getattr(self.current_df, '_query_source')
                    new_query += f"{table_name}"
                else:
                    new_query += "[table_name]"
                new_query += f"\nWHERE {quoted_col_name} = ?"
                self.set_query_text(new_query)
            self.parent.statusBar().showMessage(f"Added filter condition for '{col_name}'")

    def handle_cell_double_click(self, row, column):
        """Handle double-click on a cell to add column to query editor"""
        # Get column name
        col_name = self.results_table.horizontalHeaderItem(column).text()
        
        # Check if the column name needs quoting (contains spaces or special characters)
        quoted_col_name = col_name
        if re.search(r'[\s\W]', col_name) and not col_name.startswith('"') and not col_name.endswith('"'):
            quoted_col_name = f'"{col_name}"'
        
        # Get current query text
        current_text = self.get_query_text().strip()
        
        # Get cursor position
        cursor = self.query_edit.textCursor()
        cursor_position = cursor.position()
        
        # Check if we already have an existing query
        if current_text:
            # If there's existing text, try to insert at cursor position
            if cursor_position > 0:
                # Check if we need to add a comma before the column name
                text_before_cursor = self.query_edit.toPlainText()[:cursor_position]
                text_after_cursor = self.query_edit.toPlainText()[cursor_position:]
                
                # Add comma if needed (we're in a list of columns)
                needs_comma = (not text_before_cursor.strip().endswith(',') and 
                              not text_before_cursor.strip().endswith('(') and
                              not text_before_cursor.strip().endswith('SELECT') and
                              not re.search(r'\bFROM\s*$', text_before_cursor) and
                              not re.search(r'\bWHERE\s*$', text_before_cursor) and
                              not re.search(r'\bGROUP\s+BY\s*$', text_before_cursor) and
                              not re.search(r'\bORDER\s+BY\s*$', text_before_cursor) and
                              not re.search(r'\bHAVING\s*$', text_before_cursor) and
                              not text_after_cursor.strip().startswith(','))
                
                # Insert with comma if needed
                if needs_comma:
                    cursor.insertText(f", {quoted_col_name}")
                else:
                    cursor.insertText(quoted_col_name)
                    
                self.query_edit.setTextCursor(cursor)
                self.query_edit.setFocus()
                self.parent.statusBar().showMessage(f"Inserted '{col_name}' at cursor position")
                return
                
            # If cursor is at start, check if we have a SELECT query to modify
            if current_text.upper().startswith("SELECT"):
                # Try to find the SELECT clause
                select_match = re.match(r'(?i)SELECT\s+(.*?)(?:\sFROM\s|$)', current_text)
                if select_match:
                    select_clause = select_match.group(1).strip()
                    
                    # If it's "SELECT *", replace it with the column name
                    if select_clause == "*":
                        modified_text = current_text.replace("SELECT *", f"SELECT {quoted_col_name}")
                        self.set_query_text(modified_text)
                    # Otherwise append the column if it's not already there
                    elif quoted_col_name not in select_clause:
                        modified_text = current_text.replace(select_clause, f"{select_clause}, {quoted_col_name}")
                        self.set_query_text(modified_text)
                    
                    self.query_edit.setFocus()
                    self.parent.statusBar().showMessage(f"Added '{col_name}' to SELECT clause")
                    return
            
            # If we can't modify an existing SELECT clause, append to the end
            # Go to the end of the document
            cursor.movePosition(cursor.MoveOperation.End)
            # Insert a new line if needed
            if not current_text.endswith('\n'):
                cursor.insertText('\n')
            # Insert a simple column reference
            cursor.insertText(quoted_col_name)
            self.query_edit.setTextCursor(cursor)
            self.query_edit.setFocus()
            self.parent.statusBar().showMessage(f"Appended '{col_name}' to query")
            return
        
        # If we don't have an existing query or couldn't modify it, create a new one
        table_name = self._get_table_name(current_text)
        new_query = f"SELECT {quoted_col_name}\nFROM {table_name}"
        self.set_query_text(new_query)
        self.query_edit.setFocus()
        self.parent.statusBar().showMessage(f"Created new SELECT query for '{col_name}'")

    def handle_header_click(self, idx):
        """Handle a click on a column header"""
        # Store the column index and delay showing the context menu to allow for double-clicks
        
        # Store the current index and time for processing
        self._last_header_click_idx = idx
        
        # Create a timer to show the context menu after a short delay
        # This ensures we don't interfere with double-click detection
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._show_header_context_menu(idx))
        timer.start(200)  # 200ms delay

    def _show_header_context_menu(self, idx):
        """Show context menu for column header after delay"""
        # Get the header
        header = self.results_table.horizontalHeader()
        if not header:
            return
        
        # Get the column name
        if not hasattr(self, 'current_df') or self.current_df is None:
            return
        
        if idx >= len(self.current_df.columns):
            return
        
        # Get column name
        col_name = self.current_df.columns[idx]
        
        # Check if column name needs quoting (contains spaces or special chars)
        quoted_col_name = col_name
        if re.search(r'[\s\W]', col_name) and not col_name.startswith('"') and not col_name.endswith('"'):
            quoted_col_name = f'"{col_name}"'
        
        # Get the position for the context menu (at the header cell)
        position = header.mapToGlobal(header.rect().bottomLeft())
        
        # Create the context menu
        menu = QMenu()
        col_header_action = menu.addAction(f"Column: {col_name}")
        col_header_action.setEnabled(False)
        menu.addSeparator()
        
        # Add copy action
        copy_col_name_action = menu.addAction("Copy Column Name")
        
        # Add sorting actions
        sort_menu = menu.addMenu("Sort")
        sort_asc_action = sort_menu.addAction("Sort Ascending")
        sort_desc_action = sort_menu.addAction("Sort Descending")
        
        # Add bar chart toggle if numeric column
        bar_action = None
        if isinstance(header, FilterHeader):
            is_numeric = False
            try:
                # Check if first non-null value is numeric
                for i in range(min(100, len(self.current_df))):
                    if pd.notna(self.current_df.iloc[i, idx]):
                        val = self.current_df.iloc[i, idx]
                        if isinstance(val, (int, float, np.number)):
                            is_numeric = True
                        break
            except:
                pass
                
            if is_numeric:
                menu.addSeparator()
                if idx in header.columns_with_bars:
                    bar_action = menu.addAction("Remove Bar Chart")
                else:
                    bar_action = menu.addAction("Add Bar Chart")
        
        sql_menu = menu.addMenu("Generate SQL")
        select_col_action = sql_menu.addAction(f"SELECT {quoted_col_name}")
        filter_col_action = sql_menu.addAction(f"WHERE {quoted_col_name} = ?")
        explain_action = menu.addAction(f"Explain Column")
        encode_action = menu.addAction(f"One-Hot Encode")
        
        # Execute the menu
        action = menu.exec(position)
        
        # Handle actions
        if action == copy_col_name_action:
            QApplication.clipboard().setText(col_name)
            self.parent.statusBar().showMessage(f"Copied '{col_name}' to clipboard")
        
        elif action == explain_action:
            # Call the explain column method on the parent
            if hasattr(self.parent, 'explain_column'):
                self.parent.explain_column(col_name)
                
        elif action == encode_action:
            # Call the encode text method on the parent
            if hasattr(self.parent, 'encode_text'):
                self.parent.encode_text(col_name)
        
        elif action == sort_asc_action:
            self.results_table.sortItems(idx, Qt.SortOrder.AscendingOrder)
            self.parent.statusBar().showMessage(f"Sorted by '{col_name}' (ascending)")
            
        elif action == sort_desc_action:
            self.results_table.sortItems(idx, Qt.SortOrder.DescendingOrder)
            self.parent.statusBar().showMessage(f"Sorted by '{col_name}' (descending)")
            
        elif isinstance(header, FilterHeader) and action == bar_action:
            # Toggle bar chart
            header.toggle_bar_chart(idx)
            if idx in header.columns_with_bars:
                self.parent.statusBar().showMessage(f"Added bar chart for '{col_name}'")
            else:
                self.parent.statusBar().showMessage(f"Removed bar chart for '{col_name}'")
                
        elif action == select_col_action:
            # Insert SQL snippet at cursor position in query editor
            if hasattr(self, 'query_edit'):
                cursor = self.query_edit.textCursor()
                cursor.insertText(f"SELECT {quoted_col_name}")
                self.query_edit.setFocus()
                
        elif action == filter_col_action:
            # Insert SQL snippet at cursor position in query editor
            if hasattr(self, 'query_edit'):
                cursor = self.query_edit.textCursor()
                cursor.insertText(f"WHERE {quoted_col_name} = ")
                self.query_edit.setFocus()

    def handle_header_double_click(self, idx):
        """Handle double-click on a column header to add it to the query editor"""
        # Get column name
        if not hasattr(self, 'current_df') or self.current_df is None:
            return
        
        if idx >= len(self.current_df.columns):
            return
        
        # Get column name
        col_name = self.current_df.columns[idx]
        
        # Check if column name needs quoting (contains spaces or special chars)
        quoted_col_name = col_name
        if re.search(r'[\s\W]', col_name) and not col_name.startswith('"') and not col_name.endswith('"'):
            quoted_col_name = f'"{col_name}"'
        
        # Get current query text
        current_text = self.get_query_text().strip()
        
        # Get cursor position
        cursor = self.query_edit.textCursor()
        cursor_position = cursor.position()
        
        # Check if we already have an existing query
        if current_text:
            # If there's existing text, try to insert at cursor position
            if cursor_position > 0:
                # Check if we need to add a comma before the column name
                text_before_cursor = self.query_edit.toPlainText()[:cursor_position]
                text_after_cursor = self.query_edit.toPlainText()[cursor_position:]
                
                # Add comma if needed (we're in a list of columns)
                needs_comma = (not text_before_cursor.strip().endswith(',') and 
                              not text_before_cursor.strip().endswith('(') and
                              not text_before_cursor.strip().endswith('SELECT') and
                              not re.search(r'\bFROM\s*$', text_before_cursor) and
                              not re.search(r'\bWHERE\s*$', text_before_cursor) and
                              not re.search(r'\bGROUP\s+BY\s*$', text_before_cursor) and
                              not re.search(r'\bORDER\s+BY\s*$', text_before_cursor) and
                              not re.search(r'\bHAVING\s*$', text_before_cursor) and
                              not text_after_cursor.strip().startswith(','))
                
                # Insert with comma if needed
                if needs_comma:
                    cursor.insertText(f", {quoted_col_name}")
                else:
                    cursor.insertText(quoted_col_name)
                    
                self.query_edit.setTextCursor(cursor)
                self.query_edit.setFocus()
                self.parent.statusBar().showMessage(f"Inserted '{col_name}' at cursor position")
                return
                
            # If cursor is at start, check if we have a SELECT query to modify
            if current_text.upper().startswith("SELECT"):
                # Try to find the SELECT clause
                select_match = re.match(r'(?i)SELECT\s+(.*?)(?:\sFROM\s|$)', current_text)
                if select_match:
                    select_clause = select_match.group(1).strip()
                    
                    # If it's "SELECT *", replace it with the column name
                    if select_clause == "*":
                        modified_text = current_text.replace("SELECT *", f"SELECT {quoted_col_name}")
                        self.set_query_text(modified_text)
                    # Otherwise append the column if it's not already there
                    elif quoted_col_name not in select_clause:
                        modified_text = current_text.replace(select_clause, f"{select_clause}, {quoted_col_name}")
                        self.set_query_text(modified_text)
                    
                    self.query_edit.setFocus()
                    self.parent.statusBar().showMessage(f"Added '{col_name}' to SELECT clause")
                    return
            
            # If we can't modify an existing SELECT clause, append to the end
            # Go to the end of the document
            cursor.movePosition(cursor.MoveOperation.End)
            # Insert a new line if needed
            if not current_text.endswith('\n'):
                cursor.insertText('\n')
            # Insert a simple column reference
            cursor.insertText(quoted_col_name)
            self.query_edit.setTextCursor(cursor)
            self.query_edit.setFocus()
            self.parent.statusBar().showMessage(f"Appended '{col_name}' to query")
            return
        
        # If we don't have an existing query or couldn't modify it, create a new one
        table_name = self._get_table_name(current_text)
        new_query = f"SELECT {quoted_col_name}\nFROM {table_name}"
        self.set_query_text(new_query)
        self.query_edit.setFocus()
        self.parent.statusBar().showMessage(f"Created new SELECT query for '{col_name}'")

    def _get_table_name(self, current_text):
        """Extract table name from current query or DataFrame, with fallbacks"""
        # First, try to get the currently selected table in the UI
        if self.parent and hasattr(self.parent, 'get_selected_table'):
            selected_table = self.parent.get_selected_table()
            if selected_table:
                return selected_table
        
        # Try to extract table name from the current DataFrame
        if self.current_df is not None and hasattr(self.current_df, '_query_source'):
            table_name = getattr(self.current_df, '_query_source')
            if table_name:
                return table_name
        
        # Try to extract the table name from the current query
        if current_text:
            # Look for FROM clause
            from_match = re.search(r'(?i)FROM\s+([a-zA-Z0-9_."]+(?:\s*,\s*[a-zA-Z0-9_."]+)*)', current_text)
            if from_match:
                # Get the last table in the FROM clause (could be multiple tables joined)
                tables = from_match.group(1).split(',')
                last_table = tables[-1].strip()
                
                # Remove any alias
                last_table = re.sub(r'(?i)\s+as\s+\w+$', '', last_table)
                last_table = re.sub(r'\s+\w+$', '', last_table)
                
                # Remove any quotes
                last_table = last_table.strip('"\'`[]')
                
                return last_table
        
        # If all else fails, return placeholder
        return "[table_name]" 

    def _execute_query_callback(self, query_text):
        """Callback function for the execution handler to execute a single query."""
        # This is called by the execution handler when F5/F9 is pressed
        if hasattr(self.parent, 'execute_specific_query'):
            self.parent.execute_specific_query(query_text)
        else:
            # Fallback: execute using the standard method
            original_text = self.query_edit.toPlainText()
            cursor_pos = self.query_edit.textCursor().position()  # Save current cursor position
            self.query_edit.setPlainText(query_text)
            if hasattr(self.parent, 'execute_query'):
                self.parent.execute_query()
            self.query_edit.setPlainText(original_text)
            # Restore cursor position (as close as possible)
            doc_length = len(self.query_edit.toPlainText())
            restored_pos = min(cursor_pos, doc_length)
            cursor = self.query_edit.textCursor()
            cursor.setPosition(restored_pos)
            self.query_edit.setTextCursor(cursor)
    
    def execute_all_statements(self):
        """Execute all statements in the editor (F5 functionality)."""
        if self.execution_integration:
            return self.execution_integration.execute_all_statements()
        return None
    
    def execute_current_statement(self):
        """Execute the current statement (F9 functionality)."""
        if self.execution_integration:
            return self.execution_integration.execute_current_statement()
        return None 