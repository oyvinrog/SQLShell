#!/usr/bin/env python3
"""
Demo script to showcase F5/F9 functionality in SQLShell.
This creates a simple test environment with sample data.
"""

import sys
import os
import pandas as pd
import tempfile

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from sqlshell.main import SQLShell
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer


def create_sample_data():
    """Create sample data for testing F5/F9 functionality."""
    
    # Sample data 1: Employees
    employees = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice Johnson', 'Bob Smith', 'Carol Williams', 'David Brown', 'Eva Davis'],
        'department': ['Engineering', 'Sales', 'Engineering', 'Marketing', 'Sales'],
        'salary': [75000, 60000, 80000, 55000, 65000],
        'hire_date': ['2020-01-15', '2019-06-20', '2021-03-10', '2020-11-05', '2021-01-25']
    })
    
    # Sample data 2: Projects
    projects = pd.DataFrame({
        'project_id': [101, 102, 103, 104],
        'project_name': ['Website Redesign', 'Mobile App', 'Data Analytics', 'Marketing Campaign'],
        'status': ['Completed', 'In Progress', 'Planning', 'Completed'],
        'budget': [50000, 80000, 120000, 30000]
    })
    
    # Sample data 3: Project Assignments
    assignments = pd.DataFrame({
        'employee_id': [1, 1, 2, 3, 4, 5],
        'project_id': [101, 103, 104, 102, 104, 102],
        'role': ['Lead Developer', 'Data Analyst', 'Sales Lead', 'Developer', 'Marketing Manager', 'Sales Support'],
        'hours_allocated': [40, 20, 30, 35, 40, 25]
    })
    
    return employees, projects, assignments


def setup_sqlshell_with_data(app):
    """Set up SQLShell with sample data and demo queries."""
    
    # Create SQLShell instance
    main_window = SQLShell()
    
    try:
        # Create sample data
        employees, projects, assignments = create_sample_data()
        
        # Load data into SQLShell
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            employees.to_csv(f.name, index=False)
            employees_file = f.name
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            projects.to_csv(f.name, index=False)
            projects_file = f.name
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            assignments.to_csv(f.name, index=False)
            assignments_file = f.name
        
        # Load the CSV files
        main_window.db_manager.load_file(employees_file)
        main_window.db_manager.load_file(projects_file)
        main_window.db_manager.load_file(assignments_file)
        
        # Update the tables list
        main_window.tables_list.refresh_tables()
        
        # Clean up temp files
        os.unlink(employees_file)
        os.unlink(projects_file)
        os.unlink(assignments_file)
        
        # Set up a demo query in the editor
        demo_queries = """-- Demo queries for F5/F9 functionality
-- Try these features:
-- F5: Execute ALL statements
-- F9: Execute CURRENT statement (where your cursor is)
-- Ctrl+Enter: Execute entire content

-- Query 1: Basic employee data
SELECT name, department, salary 
FROM employees 
WHERE salary > 60000;

-- Query 2: Project summary
SELECT project_name, status, budget 
FROM projects 
ORDER BY budget DESC;

-- Query 3: Complex join - Employee project assignments
SELECT 
    e.name,
    e.department,
    p.project_name,
    a.role,
    a.hours_allocated
FROM employees e
JOIN assignments a ON e.id = a.employee_id
JOIN projects p ON a.project_id = p.project_id
WHERE p.status = 'In Progress';

-- Query 4: Department budget analysis
SELECT 
    e.department,
    COUNT(*) as employee_count,
    AVG(e.salary) as avg_salary,
    SUM(p.budget) as total_project_budget
FROM employees e
JOIN assignments a ON e.id = a.employee_id
JOIN projects p ON a.project_id = p.project_id
GROUP BY e.department
ORDER BY total_project_budget DESC"""
        
        # Get the current tab and set the demo query
        current_tab = main_window.get_current_tab()
        if current_tab:
            current_tab.set_query_text(demo_queries)
        
        # Show instructions
        def show_instructions():
            QMessageBox.information(
                main_window,
                "F5/F9 Functionality Demo",
                """🚀 F5/F9 Execution Demo Ready!

Features to test:
• F5 - Execute ALL statements (all 4 queries)
• F9 - Execute CURRENT statement (move cursor to different queries and press F9)
• Ctrl+Enter - Execute entire content (traditional behavior)

📝 Instructions:
1. Place your cursor in different SQL statements
2. Press F9 to execute just that statement
3. Press F5 to execute all statements sequentially
4. Use the F5/F9 buttons in the toolbar

Sample data loaded:
• employees (5 records)
• projects (4 records) 
• assignments (6 records)

Move your cursor around and try F9 on different statements!"""
            )
        
        # Show instructions after a short delay
        QTimer.singleShot(1000, show_instructions)
        
    except Exception as e:
        QMessageBox.critical(main_window, "Setup Error", f"Error setting up demo: {str(e)}")
    
    return main_window


def main():
    """Main function to run the F5/F9 demo."""
    app = QApplication(sys.argv)
    app.setApplicationName("SQLShell F5/F9 Demo")
    app.setApplicationDisplayName("SQLShell F5/F9 Demo")
    
    # Set up SQLShell with demo data
    main_window = setup_sqlshell_with_data(app)
    main_window.show()
    
    # Set window title to indicate it's a demo
    main_window.setWindowTitle("SQLShell - F5/F9 Execution Demo")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 