#!/usr/bin/env python3
"""
SQLShell - A powerful SQL shell with GUI interface for data analysis
Run this file to start the application.
"""

import sys
import os

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from sqlshell.main import main

if __name__ == '__main__':
    main() 