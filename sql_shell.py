import sys
import duckdb
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QTextEdit, QPushButton, QFileDialog,
                           QLabel, QSplitter)
from PyQt6.QtCore import Qt

class SQLShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.conn = duckdb.connect('pool.db')
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('SQL Shell')
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create splitter for query and results
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)

        # Top part - Query section
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)
        
        # Button row
        button_layout = QHBoxLayout()
        self.browse_btn = QPushButton('Browse Excel')
        self.browse_btn.clicked.connect(self.browse_file)
        self.execute_btn = QPushButton('Execute (Ctrl+Enter)')
        self.execute_btn.clicked.connect(self.execute_query)
        self.clear_btn = QPushButton('Clear')
        self.clear_btn.clicked.connect(self.clear_query)
        
        button_layout.addWidget(self.browse_btn)
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
        results_layout.addWidget(self.results_display)

        # Add widgets to splitter
        splitter.addWidget(query_widget)
        splitter.addWidget(results_widget)

        # Set initial sizes
        splitter.setSizes([300, 500])

        # Status bar
        self.statusBar().showMessage('Ready')

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Excel File",
            "",
            "Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;All Files (*)"
        )
        
        if file_name:
            try:
                if file_name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_name)
                elif file_name.endswith('.csv'):
                    df = pd.read_csv(file_name)
                else:
                    raise ValueError("Unsupported file format")
                
                table_name = 'imported_data'
                self.conn.register(table_name, df)
                self.statusBar().showMessage(f'Loaded {file_name} as table "{table_name}"')
                self.results_display.append(f'Successfully loaded {file_name} as table "{table_name}"\n')
                self.results_display.append(f'Schema:\n{df.dtypes.to_string()}\n')
            except Exception as e:
                self.statusBar().showMessage(f'Error loading file: {str(e)}')
                self.results_display.append(f'Error loading file: {str(e)}\n')

    def execute_query(self):
        query = self.query_edit.toPlainText().strip()
        if not query:
            return
        
        try:
            result = self.conn.execute(query).fetchdf()
            self.results_display.setText(result.to_string())
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