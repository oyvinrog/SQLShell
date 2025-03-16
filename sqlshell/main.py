import sys
import os
import duckdb
import sqlite3
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTextEdit, QPushButton, QFileDialog,
                           QLabel, QSplitter, QListWidget, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtGui import QFont, QColor
import numpy as np
from datetime import datetime
from sqlshell.sqlshell import create_test_data  # Import from the correct location

class SQLShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_db_type = 'duckdb'  # Default to DuckDB
        self.conn = duckdb.connect(':memory:')  # Create in-memory DuckDB connection by default
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
        
        # Database info label
        self.db_info_label = QLabel("No database connected")
        left_layout.addWidget(self.db_info_label)
        
        tables_label = QLabel("Tables:")
        left_layout.addWidget(tables_label)
        
        self.tables_list = QListWidget()
        self.tables_list.itemClicked.connect(self.show_table_preview)
        left_layout.addWidget(self.tables_list)
        
        # Buttons for table management
        table_buttons_layout = QHBoxLayout()
        self.open_db_btn = QPushButton('Open Database')
        self.open_db_btn.clicked.connect(self.open_database)
        self.browse_btn = QPushButton('Load Files')
        self.browse_btn.clicked.connect(self.browse_files)
        self.remove_table_btn = QPushButton('Remove Selected')
        self.remove_table_btn.clicked.connect(self.remove_selected_table)
        self.test_btn = QPushButton('Test')
        self.test_btn.clicked.connect(self.load_test_data)
        
        table_buttons_layout.addWidget(self.open_db_btn)
        table_buttons_layout.addWidget(self.browse_btn)
        table_buttons_layout.addWidget(self.remove_table_btn)
        table_buttons_layout.addWidget(self.test_btn)
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
        
        # Add export buttons
        self.export_excel_btn = QPushButton('Export to Excel')
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        self.export_parquet_btn = QPushButton('Export to Parquet')
        self.export_parquet_btn.clicked.connect(self.export_to_parquet)
        
        button_layout.addWidget(self.execute_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.export_excel_btn)
        button_layout.addWidget(self.export_parquet_btn)
        button_layout.addStretch()
        
        query_layout.addLayout(button_layout)

        # Query input
        self.query_edit = QTextEdit()
        self.query_edit.setPlaceholderText("Enter your SQL query here...")
        query_layout.addWidget(self.query_edit)

        # Bottom part - Results section
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        # Results header with row count
        results_header = QWidget()
        results_header_layout = QHBoxLayout(results_header)
        self.results_label = QLabel("Results:")
        self.row_count_label = QLabel("")
        results_header_layout.addWidget(self.results_label)
        results_header_layout.addWidget(self.row_count_label)
        results_header_layout.addStretch()
        results_layout.addWidget(results_header)
        
        # Table widget for results
        self.results_table = QTableWidget()
        self.results_table.setSortingEnabled(True)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.horizontalHeader().setSectionsMovable(True)
        self.results_table.verticalHeader().setVisible(False)
        results_layout.addWidget(self.results_table)

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

    def populate_table(self, df):
        """Populate the table widget with DataFrame content"""
        if len(df) == 0:
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(0)
            self.row_count_label.setText("No results")
            return

        # Set dimensions
        self.results_table.setRowCount(len(df))
        self.results_table.setColumnCount(len(df.columns))
        
        # Set headers
        self.results_table.setHorizontalHeaderLabels(df.columns)
        
        # Populate data
        for i, (_, row) in enumerate(df.iterrows()):
            for j, value in enumerate(row):
                formatted_value = self.format_value(value)
                item = QTableWidgetItem(formatted_value)
                
                # Set alignment based on data type
                if isinstance(value, (int, float, np.integer, np.floating)):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
                # Make cells read-only
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                self.results_table.setItem(i, j, item)
        
        # Auto-adjust column widths while ensuring minimum and maximum sizes
        self.results_table.resizeColumnsToContents()
        for i in range(len(df.columns)):
            width = self.results_table.columnWidth(i)
            self.results_table.setColumnWidth(i, min(max(width, 50), 300))
        
        # Update row count
        row_text = "row" if len(df) == 1 else "rows"
        self.row_count_label.setText(f"{len(df):,} {row_text}")

    def browse_files(self):
        if not self.conn:
            # Create a default in-memory DuckDB connection if none exists
            self.conn = duckdb.connect(':memory:')
            self.current_db_type = 'duckdb'
            self.db_info_label.setText("Connected to: in-memory DuckDB")
            
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
                
                # Handle table creation based on database type
                if self.current_db_type == 'sqlite':
                    # For SQLite, create a table from the DataFrame
                    df.to_sql(table_name, self.conn, index=False, if_exists='replace')
                else:
                    # For DuckDB, register the DataFrame as a view
                    self.conn.register(table_name, df)
                
                self.loaded_tables[table_name] = file_name
                
                # Update UI
                self.tables_list.addItem(f"{table_name} ({os.path.basename(file_name)})")
                self.statusBar().showMessage(f'Loaded {file_name} as table "{table_name}"')
                
                # Show preview of loaded data
                preview_df = df.head()
                self.populate_table(preview_df)
                self.results_label.setText(f"Preview of {table_name}:")
                
            except Exception as e:
                self.statusBar().showMessage(f'Error loading file: {str(e)}')
                self.results_table.setRowCount(0)
                self.results_table.setColumnCount(0)
                self.row_count_label.setText("")
                self.results_label.setText(f"Error loading file: {str(e)}")

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
                self.results_table.setRowCount(0)
                self.results_table.setColumnCount(0)
                self.row_count_label.setText("")
                self.results_label.setText(f"Removed table: {table_name}")

    def open_database(self):
        """Open a database file (DuckDB or SQLite)"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Database File",
            "",
            "Database Files (*.db);;All Files (*)"
        )
        
        if not file_name:
            return
            
        try:
            # Try to detect database type
            is_sqlite = self.is_sqlite_db(file_name)
            
            # Close existing connection if any
            if self.conn:
                self.conn.close()
            
            # Connect to the database
            if is_sqlite:
                self.conn = sqlite3.connect(file_name)
                self.current_db_type = 'sqlite'
            else:
                self.conn = duckdb.connect(file_name)
                self.current_db_type = 'duckdb'
            
            # Clear existing tables
            self.loaded_tables.clear()
            self.tables_list.clear()
            
            # Load tables
            self.load_database_tables()
            
            # Update UI
            db_type = "SQLite" if is_sqlite else "DuckDB"
            self.db_info_label.setText(f"Connected to: {os.path.basename(file_name)} ({db_type})")
            self.statusBar().showMessage(f'Successfully opened {db_type} database: {file_name}')
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open database: {str(e)}")
            self.statusBar().showMessage('Error opening database')

    def is_sqlite_db(self, filename):
        """Check if the file is a SQLite database"""
        try:
            with open(filename, 'rb') as f:
                header = f.read(16)
                return header[:16] == b'SQLite format 3\x00'
        except:
            return False

    def load_database_tables(self):
        """Load all tables from the current database"""
        try:
            if self.current_db_type == 'sqlite':
                query = "SELECT name FROM sqlite_master WHERE type='table'"
                cursor = self.conn.cursor()
                tables = cursor.execute(query).fetchall()
                for (table_name,) in tables:
                    self.loaded_tables[table_name] = 'database'
                    self.tables_list.addItem(f"{table_name} (database)")
            else:  # duckdb
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
                result = self.conn.execute(query).fetchdf()
                for table_name in result['table_name']:
                    self.loaded_tables[table_name] = 'database'
                    self.tables_list.addItem(f"{table_name} (database)")
        except Exception as e:
            self.statusBar().showMessage(f'Error loading tables: {str(e)}')

    def execute_query(self):
        query = self.query_edit.toPlainText().strip()
        if not query:
            return
        
        try:
            if self.current_db_type == 'sqlite':
                # Execute SQLite query and convert to DataFrame
                result = pd.read_sql_query(query, self.conn)
            else:
                # Execute DuckDB query
                result = self.conn.execute(query).fetchdf()
                
            self.populate_table(result)
            self.results_label.setText("Query Results:")
            self.statusBar().showMessage('Query executed successfully')
        except Exception as e:
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(0)
            self.row_count_label.setText("")
            self.results_label.setText(f"Error executing query: {str(e)}")
            self.statusBar().showMessage('Error executing query')

    def clear_query(self):
        self.query_edit.clear()

    def show_table_preview(self, item):
        """Show a preview of the selected table"""
        if item:
            table_name = item.text().split(' (')[0]
            try:
                if self.current_db_type == 'sqlite':
                    preview_df = pd.read_sql_query(f'SELECT * FROM "{table_name}" LIMIT 5', self.conn)
                else:
                    preview_df = self.conn.execute(f'SELECT * FROM {table_name} LIMIT 5').fetchdf()
                    
                self.populate_table(preview_df)
                self.results_label.setText(f"Preview of {table_name}:")
                self.statusBar().showMessage(f'Showing preview of table "{table_name}"')
            except Exception as e:
                self.results_table.setRowCount(0)
                self.results_table.setColumnCount(0)
                self.row_count_label.setText("")
                self.results_label.setText(f"Error showing preview: {str(e)}")
                self.statusBar().showMessage('Error showing table preview')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.execute_query()
        else:
            super().keyPressEvent(event)

    def load_test_data(self):
        """Generate and load test data"""
        try:
            # Create test data directory if it doesn't exist
            os.makedirs('test_data', exist_ok=True)
            
            # Generate test data
            sales_df = create_test_data.create_sales_data()
            customer_df = create_test_data.create_customer_data()
            product_df = create_test_data.create_product_data()
            
            # Save test data
            sales_df.to_excel('test_data/sample_sales_data.xlsx', index=False)
            customer_df.to_parquet('test_data/customer_data.parquet', index=False)
            product_df.to_excel('test_data/product_catalog.xlsx', index=False)
            
            # Load the files into DuckDB
            self.conn.register('sample_sales_data', sales_df)
            self.conn.register('product_catalog', product_df)
            self.conn.register('customer_data', customer_df)
            
            # Update loaded tables tracking
            self.loaded_tables['sample_sales_data'] = 'test_data/sample_sales_data.xlsx'
            self.loaded_tables['product_catalog'] = 'test_data/product_catalog.xlsx'
            self.loaded_tables['customer_data'] = 'test_data/customer_data.parquet'
            
            # Update UI
            self.tables_list.clear()
            for table_name, file_path in self.loaded_tables.items():
                self.tables_list.addItem(f"{table_name} ({os.path.basename(file_path)})")
            
            # Set the sample query
            self.query_edit.setText("select * from sample_sales_data cd inner join product_catalog pc on pc.productid = cd.productid limit 3")
            
            self.statusBar().showMessage('Test data loaded successfully')
            
        except Exception as e:
            self.statusBar().showMessage(f'Error loading test data: {str(e)}')

    def export_to_excel(self):
        if self.results_table.rowCount() == 0:
            QMessageBox.warning(self, "No Data", "There is no data to export.")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(self, "Save as Excel", "", "Excel Files (*.xlsx);;All Files (*)")
        if not file_name:
            return
        
        try:
            # Convert table data to DataFrame
            df = self.get_table_data_as_dataframe()
            df.to_excel(file_name, index=False)
            self.statusBar().showMessage(f'Data exported to {file_name}')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")

    def export_to_parquet(self):
        if self.results_table.rowCount() == 0:
            QMessageBox.warning(self, "No Data", "There is no data to export.")
            return
        
        file_name, _ = QFileDialog.getSaveFileName(self, "Save as Parquet", "", "Parquet Files (*.parquet);;All Files (*)")
        if not file_name:
            return
        
        try:
            # Convert table data to DataFrame
            df = self.get_table_data_as_dataframe()
            df.to_parquet(file_name, index=False)
            self.statusBar().showMessage(f'Data exported to {file_name}')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")

    def get_table_data_as_dataframe(self):
        """Helper function to convert table widget data to a DataFrame"""
        headers = [self.results_table.horizontalHeaderItem(i).text() for i in range(self.results_table.columnCount())]
        data = []
        for row in range(self.results_table.rowCount()):
            row_data = []
            for column in range(self.results_table.columnCount()):
                item = self.results_table.item(row, column)
                row_data.append(item.text() if item else '')
            data.append(row_data)
        return pd.DataFrame(data, columns=headers)

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    sql_shell = SQLShell()
    sql_shell.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 