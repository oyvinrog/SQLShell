#!/usr/bin/env python3
"""
SQLShell - A powerful SQL shell with GUI interface for data analysis

This is the main entry point for the application. You can start SQLShell in two ways:

1. Normal way (if 'sqls' command works):
   sqls

2. Alternative way (if 'sqls' command leads to "access denied" on Windows):
   python -c "import sqlshell; sqlshell.start()"
"""

import sys
import os

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from sqlshell.main import main

def start():
    """Start the SQLShell application.
    This function is provided for Windows compatibility when the 'sqls' command doesn't work."""
    main()

if __name__ == '__main__':
    main() 