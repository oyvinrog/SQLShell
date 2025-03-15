import sys
import os
import duckdb
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTextEdit, QPushButton, QFileDialog,
                           QLabel, QSplitter, QListWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import numpy as np
from datetime import datetime

class SQLShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.conn = duckdb.connect('pool.db')
        self.loaded_tables = {}  # Keep track of loaded tables
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('SQL Shell')
        self.setGeometry(100, 100, 1400, 800)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left panel for table list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        tables_label = QLabel("Loaded Tables:")
        left_layout.addWidget(tables_label)
        
        self.tables_list = QListWidget()
        left_layout.addWidget(self.tables_list)
        
        # Buttons for table management
        table_buttons_layout = QHBoxLayout()
        self.browse_btn = QPushButton('Load Files')
        self.browse_btn.clicked.connect(self.browse_files)
        self.remove_table_btn = QPushButton('Remove Selected')
        self.remove_table_btn.clicked.connect(self.remove_selected_table)
        
        table_buttons_layout.addWidget(self.browse_btn)
        table_buttons_layout.addWidget(self.remove_table_btn)
        left_layout.addLayout(table_buttons_layout)

        # Right panel for query and results
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Create splitter for query and results
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top part - Query section
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)
        
        # Button row
        button_layout = QHBoxLayout()
        self.execute_btn = QPushButton('Execute (Ctrl+Enter)')
        self.execute_btn.clicked.connect(self.execute_query)
        self.clear_btn = QPushButton('Clear')
        self.clear_btn.clicked.connect(self.clear_query)
        
        button_layout.addWidget(self.execute_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        query_layout.addLayout(button_layout)

        # Query input
        self.query_edit = QTextEdit()
        self.query_edit.setPlaceholderText("Enter your SQL query here...")
        query_layout.addWidget(self.query_edit)

        # Bottom part - Results section
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        results_label = QLabel("Results:")
        results_layout.addWidget(results_label)
        
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        # Set monospace font for better table alignment
        self.results_display.setFont(QFont("Courier New"))
        results_layout.addWidget(self.results_display)

        # Add widgets to splitter
        splitter.addWidget(query_widget)
        splitter.addWidget(results_widget)
        
        # Set initial sizes for splitter
        splitter.setSizes([300, 500])
        
        right_layout.addWidget(splitter)

        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 4)

        # Status bar
        self.statusBar().showMessage('Ready')

    def format_value(self, value):
        """Format values for display"""
        if pd.isna(value):
            return 'NULL'
        elif isinstance(value, (int, np.integer)):
            return f"{value:,}"
        elif isinstance(value, (float, np.floating)):
            return f"{value:,.2f}"
        elif isinstance(value, (datetime, pd.Timestamp)):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        return str(value)

    def format_dataframe(self, df):
        """Format DataFrame as a nice ASCII table"""
        if len(df) == 0:
            return "Query returned no results."

        # Convert all values to formatted strings
        formatted_df = df.applymap(self.format_value)

        # Get maximum width for each column (including header)
        col_widths = {}
        for col in df.columns:
            col_widths[col] = max(
                len(str(col)),
                formatted_df[col].astype(str).str.len().max()
            )

        # Create header
        header = " | ".join(f"{col:<{col_widths[col]}}" for col in df.columns)
        separator = "-+-".join("-" * width for width in col_widths.values())
        
        # Create rows
        rows = []
        for _, row in formatted_df.iterrows():
            formatted_row = " | ".join(
                f"{str(val):<{col_widths[col]}}" 
                for col, val in row.items()
            )
            rows.append(formatted_row)

        # Combine all parts
        table = f"\n{header}\n{separator}\n" + "\n".join(rows)
        
        # Add summary
        summary = f"\n\nNumber of rows: {len(df):,}"
        if len(df) == 1:
            summary = f"\n\nNumber of row: 1"
            
        return table + summary

    def browse_files(self):
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Data Files",
            "",
            "Data Files (*.xlsx *.xls *.csv *.parquet);;Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;Parquet Files (*.parquet);;All Files (*)"
        )
        
        for file_name in file_names:
            try:
                if file_name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_name)
                elif file_name.endswith('.csv'):
                    df = pd.read_csv(file_name)
                elif file_name.endswith('.parquet'):
                    df = pd.read_parquet(file_name)
                else:
                    raise ValueError("Unsupported file format")
                
                # Generate table name from file name
                base_name = os.path.splitext(os.path.basename(file_name))[0]
                table_name = self.sanitize_table_name(base_name)
                
                # Ensure unique table name
                original_name = table_name
                counter = 1
                while table_name in self.loaded_tables:
                    table_name = f"{original_name}_{counter}"
                    counter += 1
                
                # Register table in DuckDB
                self.conn.register(table_name, df)
                self.loaded_tables[table_name] = file_name
                
                # Update UI
                self.tables_list.addItem(f"{table_name} ({os.path.basename(file_name)})")
                self.statusBar().showMessage(f'Loaded {file_name} as table "{table_name}"')
                self.results_display.append(f'Successfully loaded {file_name} as table "{table_name}"\n')
                self.results_display.append(f'Schema:\n{df.dtypes.to_string()}\n')
                
            except Exception as e:
                self.statusBar().showMessage(f'Error loading file: {str(e)}')
                self.results_display.append(f'Error loading file {file_name}: {str(e)}\n')

    def sanitize_table_name(self, name):
        # Replace invalid characters with underscores
        import re
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure it starts with a letter
        if not name[0].isalpha():
            name = 'table_' + name
        return name.lower()

    def remove_selected_table(self):
        current_item = self.tables_list.currentItem()
        if current_item:
            table_name = current_item.text().split(' (')[0]
            if table_name in self.loaded_tables:
                # Remove from DuckDB
                self.conn.execute(f'DROP VIEW IF EXISTS {table_name}')
                # Remove from our tracking
                del self.loaded_tables[table_name]
                # Remove from list widget
                self.tables_list.takeItem(self.tables_list.row(current_item))
                self.statusBar().showMessage(f'Removed table "{table_name}"')
                self.results_display.append(f'Removed table "{table_name}"\n')

    def execute_query(self):
        query = self.query_edit.toPlainText().strip()
        if not query:
            return
        
        try:
            result = self.conn.execute(query).fetchdf()
            formatted_result = self.format_dataframe(result)
            self.results_display.setText(formatted_result)
            self.statusBar().showMessage('Query executed successfully')
        except Exception as e:
            self.results_display.setText(f'Error executing query: {str(e)}')
            self.statusBar().showMessage('Error executing query')

    def clear_query(self):
        self.query_edit.clear()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.execute_query()
        else:
            super().keyPressEvent(event)

def main():
    app = QApplication(sys.argv)
    sql_shell = SQLShell()
    sql_shell.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 