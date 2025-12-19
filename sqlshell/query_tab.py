import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QHeaderView, QTableWidget, QSplitter, QApplication, 
                             QToolButton, QMenu, QInputDialog, QLineEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
import re
import pandas as pd
import numpy as np

from sqlshell.editor import SQLEditor
from sqlshell.syntax_highlighter import SQLSyntaxHighlighter
from sqlshell.ui import FilterHeader
from sqlshell.styles import get_row_count_label_stylesheet
from sqlshell.editor_integration import integrate_execution_functionality
from sqlshell.widgets import CopyableTableWidget
from sqlshell.docs_panel import DocsPanel

class QueryTab(QWidget):
    def __init__(self, parent, results_title="RESULTS"):
        super().__init__()
        self.parent = parent
        self.current_df = None
        self.filter_widgets = []
        self.results_title_text = results_title
        # Track preview mode - when True, tools should use full table data
        self.is_preview_mode = False
        self.preview_table_name = None  # Name of table being previewed
        self.init_ui()
        
    def init_ui(self):
        """Initialize the tab's UI components"""
        # Set main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Track compact mode state
        self._compact_mode = False
        
        # Create splitter for query and results
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(6)
        self.splitter.setChildrenCollapsible(False)
        
        # Top part - Query section
        query_widget = QFrame()
        query_widget.setObjectName("content_panel")
        self.query_layout = QVBoxLayout(query_widget)
        self.query_layout.setContentsMargins(8, 6, 8, 6)
        self.query_layout.setSpacing(6)
        
        # Create horizontal splitter for editor and docs panel
        self.editor_docs_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor_docs_splitter.setHandleWidth(4)
        self.editor_docs_splitter.setChildrenCollapsible(True)
        
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
        
        # Create the DuckDB documentation panel
        self.docs_panel = DocsPanel()
        self._docs_panel_visible = True  # Visible by default
        
        # Connect docs panel signals
        self.docs_panel.close_requested.connect(self.toggle_docs_panel)
        
        # Connect editor text changes to docs panel (with debouncing)
        self._docs_update_timer = QTimer()
        self._docs_update_timer.setSingleShot(True)
        self._docs_update_timer.timeout.connect(self._update_docs_from_editor)
        self.query_edit.textChanged.connect(self._on_editor_text_changed)
        self.query_edit.cursorPositionChanged.connect(self._on_cursor_position_changed)
        
        # Add editor and docs panel to the horizontal splitter
        self.editor_docs_splitter.addWidget(self.query_edit)
        self.editor_docs_splitter.addWidget(self.docs_panel)
        
        # Set initial sizes (editor ~70%, docs panel ~30%)
        self.editor_docs_splitter.setSizes([700, 300])
        
        self.query_layout.addWidget(self.editor_docs_splitter)
        
        # Ultra-compact button row (22px height)
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(2)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_style = "padding: 2px 8px; font-size: 11px;"
        btn_height = 22
        
        self.execute_btn = QPushButton('▶ Run')
        self.execute_btn.setObjectName("primary_button")
        self.execute_btn.setToolTip('Execute entire query (Ctrl+Enter)')
        self.execute_btn.clicked.connect(self.execute_query)
        self.execute_btn.setFixedHeight(btn_height)
        self.execute_btn.setStyleSheet(btn_style)
        
        # Compact F5/F9 buttons
        self.execute_all_btn = QPushButton('F5')
        self.execute_all_btn.setToolTip('Execute all statements (F5)')
        self.execute_all_btn.clicked.connect(self.execute_all_statements)
        self.execute_all_btn.setFixedHeight(btn_height)
        self.execute_all_btn.setFixedWidth(32)
        self.execute_all_btn.setStyleSheet(btn_style)
        
        self.execute_current_btn = QPushButton('F9')
        self.execute_current_btn.setToolTip('Execute current statement at cursor (F9)')
        self.execute_current_btn.clicked.connect(self.execute_current_statement)
        self.execute_current_btn.setFixedHeight(btn_height)
        self.execute_current_btn.setFixedWidth(32)
        self.execute_current_btn.setStyleSheet(btn_style)
        
        self.clear_btn = QPushButton('Clear')
        self.clear_btn.setToolTip('Clear query editor')
        self.clear_btn.clicked.connect(self.clear_query)
        self.clear_btn.setFixedHeight(btn_height)
        self.clear_btn.setStyleSheet(btn_style)
        
        self.button_layout.addWidget(self.execute_btn)
        self.button_layout.addWidget(self.execute_all_btn)
        self.button_layout.addWidget(self.execute_current_btn)
        self.button_layout.addWidget(self.clear_btn)
        self.button_layout.addStretch()
        
        self.export_excel_btn = QPushButton('Excel')
        self.export_excel_btn.setToolTip('Export results to Excel')
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        self.export_excel_btn.setFixedHeight(btn_height)
        self.export_excel_btn.setStyleSheet(btn_style)
        
        self.export_parquet_btn = QPushButton('Parquet')
        self.export_parquet_btn.setToolTip('Export results to Parquet')
        self.export_parquet_btn.clicked.connect(self.export_to_parquet)
        self.export_parquet_btn.setFixedHeight(btn_height)
        self.export_parquet_btn.setStyleSheet(btn_style)
        
        self.button_layout.addWidget(self.export_excel_btn)
        self.button_layout.addWidget(self.export_parquet_btn)
        
        # Docs panel toggle button
        self.docs_btn = QPushButton('📚 Docs')
        self.docs_btn.setToolTip('Toggle DuckDB documentation panel (F1)')
        self.docs_btn.clicked.connect(self.toggle_docs_panel)
        self.docs_btn.setFixedHeight(btn_height)
        self.docs_btn.setStyleSheet(btn_style)
        self.docs_btn.setCheckable(True)
        self.docs_btn.setChecked(True)  # Checked by default since panel is open
        self.button_layout.addWidget(self.docs_btn)
        
        # F1 shortcut to toggle docs panel
        self.docs_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F1), self)
        self.docs_shortcut.activated.connect(self.toggle_docs_panel)
        
        self.query_layout.addLayout(self.button_layout)
        
        # Bottom part - Results section with reduced padding
        results_widget = QWidget()
        self.results_layout = QVBoxLayout(results_widget)
        self.results_layout.setContentsMargins(8, 4, 8, 4)
        self.results_layout.setSpacing(4)
        
        # Compact results header with row count and info button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        
        self.results_title = QLabel(self.results_title_text)
        self.results_title.setObjectName("header_label")
        self.results_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #34495e;")
        header_layout.addWidget(self.results_title)
        
        # Compact info button with tooltip (replaces verbose help text)
        self.help_info_btn = QToolButton()
        self.help_info_btn.setText("ℹ")
        self.help_info_btn.setToolTip(
            "<b>Keyboard Shortcuts:</b><br>"
            "• <b>Ctrl+Enter</b> - Execute entire query<br>"
            "• <b>F5</b> - Execute all statements<br>"
            "• <b>F9</b> - Execute current statement<br>"
            "• <b>Ctrl+F</b> - Search in results<br>"
            "• <b>Ctrl+C</b> - Copy selected data<br>"
            "• <b>Ctrl+B</b> - Browse files<br>"
            "• <b>Ctrl+\\</b> - Toggle sidebar<br>"
            "• <b>Ctrl+Shift+C</b> - Compact mode<br><br>"
            "<b>Table Interactions:</b><br>"
            "• Double-click header → Rename column<br>"
            "• Right-click header → Analytical options"
        )
        self.help_info_btn.setStyleSheet("""
            QToolButton {
                border: none;
                color: #3498db;
                font-size: 12px;
                padding: 0 4px;
            }
            QToolButton:hover {
                color: #2980b9;
                background-color: #ecf0f1;
                border-radius: 2px;
            }
        """)
        header_layout.addWidget(self.help_info_btn)
        
        header_layout.addStretch()
        
        self.row_count_label = QLabel("")
        self.row_count_label.setStyleSheet(get_row_count_label_stylesheet())
        header_layout.addWidget(self.row_count_label)
        
        self.results_layout.addLayout(header_layout)
        
        # Results table with customized header
        self.results_table = CopyableTableWidget()
        self.results_table.setAlternatingRowColors(True)
        
        # Set a reference to this tab so the copy functionality can access current_df
        self.results_table._parent_tab = self
        
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
        
        # Set initial sizes - balanced split (45% query, 55% results)
        # Both areas are important for SQL work
        screen = QApplication.primaryScreen()
        if screen:
            available_height = screen.availableGeometry().height()
            if available_height >= 1080:  # Large screens
                query_height = int(available_height * 0.40)  # 40% for query area
                self.splitter.setSizes([query_height, available_height - query_height])
            else:  # Smaller screens
                self.splitter.setSizes([350, 400])
        else:
            self.splitter.setSizes([350, 400])
        
        main_layout.addWidget(self.splitter)
    
    def set_compact_mode(self, enabled):
        """Toggle compact mode for this tab to maximize query/results space"""
        self._compact_mode = enabled
        
        if enabled:
            # Compact mode: minimize UI chrome for maximum editor/results space
            self.query_layout.setContentsMargins(2, 2, 2, 2)
            self.query_layout.setSpacing(2)
            self.results_layout.setContentsMargins(2, 2, 2, 2)
            self.results_layout.setSpacing(2)
            self.results_title.setVisible(False)
            self.help_info_btn.setVisible(False)
            
            # Ultra-compact buttons (icons only)
            self.execute_btn.setText("▶")
            self.execute_btn.setFixedWidth(28)
            self.clear_btn.setText("✕")
            self.clear_btn.setFixedWidth(28)
            self.export_excel_btn.setVisible(False)
            self.export_parquet_btn.setVisible(False)
            self.docs_btn.setText("📚")
            self.docs_btn.setFixedWidth(28)
        else:
            # Normal mode
            self.query_layout.setContentsMargins(8, 6, 8, 6)
            self.query_layout.setSpacing(6)
            self.results_layout.setContentsMargins(8, 4, 8, 4)
            self.results_layout.setSpacing(4)
            self.results_title.setVisible(True)
            self.help_info_btn.setVisible(True)
            
            # Restore button labels
            self.execute_btn.setText("▶ Run")
            self.execute_btn.setMinimumWidth(0)
            self.execute_btn.setMaximumWidth(16777215)
            self.clear_btn.setText("Clear")
            self.clear_btn.setMinimumWidth(0)
            self.clear_btn.setMaximumWidth(16777215)
            self.export_excel_btn.setVisible(True)
            self.export_parquet_btn.setVisible(True)
            self.docs_btn.setText("📚 Docs")
            self.docs_btn.setMinimumWidth(0)
            self.docs_btn.setMaximumWidth(16777215)
        
    def get_query_text(self):
        """Get the current query text"""
        return self.query_edit.toPlainText()
        
    def set_query_text(self, text):
        """Set the query text"""
        self.query_edit.setPlainText(text)
    
    def get_column_name_by_index(self, column_index):
        """
        Get the column name at the given index from the DataFrame that will be used by tools.
        This ensures we get the correct column name after renames/deletes.
        
        Args:
            column_index: The index of the column
            
        Returns:
            The column name, or None if the index is invalid or no data is available
        """
        if hasattr(self.parent, 'get_data_for_tool'):
            df, _ = self.parent.get_data_for_tool()
            if df is not None and 0 <= column_index < len(df.columns):
                return df.columns[column_index]
        # Fallback to current_df if get_data_for_tool is not available
        if hasattr(self, 'current_df') and self.current_df is not None:
            if 0 <= column_index < len(self.current_df.columns):
                return self.current_df.columns[column_index]
        return None
        
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

        # Transform submenu for column-level operations
        transform_menu = menu.addMenu("Transform")
        delete_column_action = transform_menu.addAction("Delete (Del)")

        explain_action = menu.addAction("Find Related Columns")
        related_ohe_action = menu.addAction("Find Related One-Hot Encodings")
        encode_action = menu.addAction("One-Hot Encode")
        discover_rules_action = menu.addAction("Find IF-THEN Rules")
        
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
                
        elif action == related_ohe_action:
            # Find related one-hot encodings that predict this column
            if hasattr(self.parent, 'find_related_one_hot_encodings'):
                self.parent.find_related_one_hot_encodings(col_name)
                
        elif action == encode_action:
            # Call the encode text method on the parent
            if hasattr(self.parent, 'encode_text'):
                self.parent.encode_text(col_name)
        
        elif action == discover_rules_action:
            # Call the discover classification rules method on the parent
            if hasattr(self.parent, 'discover_classification_rules'):
                self.parent.discover_classification_rules(col_name)
        
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

        elif action == delete_column_action:
            # Request column deletion from the main window
            if hasattr(self.parent, "delete_column"):
                self.parent.delete_column(col_name)

    def handle_cell_double_click(self, row, column):
        """Handle double-click on a cell to add column to query editor"""
        # Get column name from the correct DataFrame (handles renames/deletes)
        col_name = self.get_column_name_by_index(column)
        if col_name is None:
            return
        
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
        
        # Get the column name from the correct DataFrame (handles renames/deletes)
        col_name = self.get_column_name_by_index(idx)
        if col_name is None:
            return
        
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

        # Transform submenu for column-level operations
        transform_menu = menu.addMenu("Transform")
        delete_column_action = transform_menu.addAction("Delete (Del)")

        explain_action = menu.addAction("Find Related Columns")
        related_ohe_action = menu.addAction("Find Related One-Hot Encodings")
        encode_action = menu.addAction("One-Hot Encode")
        discover_rules_action = menu.addAction("Find IF-THEN Rules")
        
        # Execute the menu
        action = menu.exec(position)
        
        # Handle actions
        if action == copy_col_name_action:
            QApplication.clipboard().setText(col_name)
            self.parent.statusBar().showMessage(f"Copied '{col_name}' to clipboard")
        
        elif action == explain_action:
            # Call the explain column method on the parent
            col_name = self.get_column_name_by_index(idx)
            if col_name and hasattr(self.parent, 'explain_column'):
                self.parent.explain_column(col_name)
                
        elif action == related_ohe_action:
            # Find related one-hot encodings that predict this column
            col_name = self.get_column_name_by_index(idx)
            if col_name and hasattr(self.parent, 'find_related_one_hot_encodings'):
                self.parent.find_related_one_hot_encodings(col_name)
                
        elif action == encode_action:
            # Call the encode text method on the parent
            col_name = self.get_column_name_by_index(idx)
            if col_name and hasattr(self.parent, 'encode_text'):
                self.parent.encode_text(col_name)
        
        elif action == discover_rules_action:
            # Call the discover classification rules method on the parent
            col_name = self.get_column_name_by_index(idx)
            if col_name and hasattr(self.parent, 'discover_classification_rules'):
                self.parent.discover_classification_rules(col_name)
        
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

        elif action == delete_column_action:
            # Request column deletion from the main window
            col_name = self.get_column_name_by_index(idx)
            if col_name and hasattr(self.parent, "delete_column"):
                self.parent.delete_column(col_name)

    def handle_header_double_click(self, idx):
        """Handle double-click on a column header to rename the column"""
        # Get column name
        if not hasattr(self, 'current_df') or self.current_df is None:
            return
        
        if idx >= len(self.current_df.columns):
            return
        
        # Get current column name
        col_name = self.current_df.columns[idx]
        
        # Show rename dialog
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Column",
            "Enter new column name:",
            QLineEdit.EchoMode.Normal,
            col_name
        )
        
        if not ok or not new_name:
            return
        
        # Validate the new name
        if new_name == col_name:
            return  # No change
        
        # Use the main window's rename_column method to handle preview mode and persistence
        if hasattr(self.parent, 'rename_column'):
            self.parent.rename_column(col_name, new_name)
        else:
            # Fallback to direct rename if method doesn't exist
            if new_name in self.current_df.columns:
                self.parent.statusBar().showMessage(f"Error: Column '{new_name}' already exists")
                return
            
            # Rename the column in the DataFrame
            self.current_df.rename(columns={col_name: new_name}, inplace=True)
            
            # Update the main window's current_df if it exists
            if hasattr(self.parent, 'current_df'):
                self.parent.current_df = self.current_df.copy()
            
            # Update the table header
            header_item = self.results_table.horizontalHeaderItem(idx)
            if header_item:
                header_item.setText(new_name)
            else:
                # If header item doesn't exist, set it
                from PyQt6.QtWidgets import QTableWidgetItem
                header_item = QTableWidgetItem(new_name)
                self.results_table.setHorizontalHeaderItem(idx, header_item)
            
            # Update status bar
            self.parent.statusBar().showMessage(f"Column renamed from '{col_name}' to '{new_name}'")

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
    
    # ==================== Documentation Panel Methods ====================
    
    def toggle_docs_panel(self):
        """Toggle the visibility of the DuckDB documentation panel."""
        self._docs_panel_visible = not self._docs_panel_visible
        
        if self._docs_panel_visible:
            self.docs_panel.show()
            # Animate to show the panel
            current_sizes = self.editor_docs_splitter.sizes()
            total_width = sum(current_sizes)
            # Give docs panel about 30% of the space
            docs_width = min(350, max(280, int(total_width * 0.30)))
            self.editor_docs_splitter.setSizes([total_width - docs_width, docs_width])
            self.docs_btn.setChecked(True)
            # Update docs panel with current editor content
            self._update_docs_from_editor()
            if hasattr(self.parent, 'statusBar'):
                self.parent.statusBar().showMessage('DuckDB documentation panel opened (F1 to toggle)', 2000)
        else:
            self.docs_panel.hide()
            # Give all space to editor
            current_sizes = self.editor_docs_splitter.sizes()
            total_width = sum(current_sizes)
            self.editor_docs_splitter.setSizes([total_width, 0])
            self.docs_btn.setChecked(False)
            if hasattr(self.parent, 'statusBar'):
                self.parent.statusBar().showMessage('DuckDB documentation panel closed', 2000)
    
    def show_docs_panel(self):
        """Show the documentation panel if hidden."""
        if not self._docs_panel_visible:
            self.toggle_docs_panel()
    
    def hide_docs_panel(self):
        """Hide the documentation panel if visible."""
        if self._docs_panel_visible:
            self.toggle_docs_panel()
    
    def _on_editor_text_changed(self):
        """Handle editor text changes - debounce before updating docs."""
        if self._docs_panel_visible:
            # Debounce to avoid excessive updates
            self._docs_update_timer.start(350)
    
    def _on_cursor_position_changed(self):
        """Handle cursor position changes in the editor."""
        if self._docs_panel_visible:
            # Shorter debounce for cursor moves
            self._docs_update_timer.start(200)
    
    def _update_docs_from_editor(self):
        """Update the docs panel based on current editor content."""
        if not self._docs_panel_visible:
            return
        
        try:
            # Get text before cursor
            cursor = self.query_edit.textCursor()
            position = cursor.position()
            full_text = self.query_edit.toPlainText()
            text_before_cursor = full_text[:position]
            
            # Update the docs panel
            self.docs_panel.update_from_cursor_position(text_before_cursor)
        except Exception as e:
            # Silently handle any errors to avoid disrupting the user
            pass
    
    def search_docs(self, query: str):
        """
        Search the documentation for a specific query.
        
        Args:
            query: The search term to look up
        """
        if not self._docs_panel_visible:
            self.show_docs_panel()
        
        # Set the search query in the docs panel
        self.docs_panel.search_input.setText(query)
    
    def is_docs_panel_visible(self) -> bool:
        """Check if the documentation panel is currently visible."""
        return self._docs_panel_visible
