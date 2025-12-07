"""
SQLShell - A powerful SQL shell with GUI interface for data analysis
"""

import sys

def _get_version() -> str:
    """Get version from pyproject.toml (single source of truth)."""
    from pathlib import Path
    import re
    
    # For PyInstaller frozen executables, check bundled pyproject.toml
    if getattr(sys, 'frozen', False):
        try:
            # PyInstaller stores data files in sys._MEIPASS
            bundle_dir = Path(sys._MEIPASS)
            pyproject = bundle_dir / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text()
                match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
                if match:
                    return match.group(1)
        except Exception:
            pass
    
    # Development mode: read from pyproject.toml relative to package
    try:
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            if match:
                return match.group(1)
    except Exception:
        pass
    
    # Fallback: read from installed package metadata (pip install)
    try:
        from importlib.metadata import version
        return version("sqlshell")
    except Exception:
        pass
    
    return "0.0.0"  # Last resort fallback

__version__ = _get_version()
__author__ = "SQLShell Team"

from sqlshell.__main__ import main, SQLShell
from PyQt6.QtWidgets import QApplication

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
                if source.startswith('database:'):
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