"""
SQLShell - A powerful SQL shell with GUI interface for data analysis
"""

__version__ = "0.3.0"
__author__ = "SQLShell Team"

from sqlshell.main import main, SQLShell
from PyQt6.QtWidgets import QApplication
import sys

def start(database_path=None):
    """Start the SQLShell application.
    
    Args:
        database_path (str, optional): Path to a database file to open. If provided,
            SQLShell will automatically open this database on startup.
    """
    app = QApplication(sys.argv)
    window = SQLShell()
    
    if database_path:
        try:
            # Open the database
            window.db_manager.open_database(database_path, load_all_tables=True)
            
            # Update UI with tables from the database
            for table_name, source in window.db_manager.loaded_tables.items():
                if source == 'database':
                    window.tables_list.add_table_item(table_name, "database")
            
            # Update the completer with table and column names
            window.update_completer()
            
            # Update status bar
            window.statusBar().showMessage(f"Connected to database: {database_path}")
            window.db_info_label.setText(window.db_manager.get_connection_info())
        except Exception as e:
            print(f"Error opening database: {e}")
    
    window.show()
    return app.exec()

# SQLShell package initialization 