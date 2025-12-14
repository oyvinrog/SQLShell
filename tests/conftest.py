"""
Shared pytest fixtures and configuration for SQLShell tests.

This module provides common test fixtures that can be used across all test modules.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

import pytest
import pandas as pd
import numpy as np

# Add the parent directory to the path to import sqlshell modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==============================================================================
# Path Fixtures
# ==============================================================================

@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def test_data_dir():
    """Return the test data directory."""
    return PROJECT_ROOT / "tests" / "data"


@pytest.fixture(scope="session")
def sample_data_dir():
    """Return the sample_data directory."""
    return PROJECT_ROOT / "sample_data"


# ==============================================================================
# Temporary Directory Fixtures
# ==============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory that is cleaned up after the test."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def module_temp_dir():
    """Create a temporary directory for the module, cleaned up after all tests in module."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


# ==============================================================================
# Sample DataFrame Fixtures
# ==============================================================================

@pytest.fixture
def sample_df():
    """Create a simple sample DataFrame for testing."""
    return pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
        'age': [25, 30, 35, 28, 32],
        'salary': [50000.0, 60000.0, 70000.0, 55000.0, 65000.0],
        'department': ['Engineering', 'Marketing', 'Engineering', 'Sales', 'Marketing']
    })


@pytest.fixture
def large_sample_df():
    """Create a larger sample DataFrame for performance testing."""
    np.random.seed(42)
    n_rows = 10000
    return pd.DataFrame({
        'id': range(n_rows),
        'name': [f'User_{i:05d}' for i in range(n_rows)],
        'age': np.random.randint(18, 70, n_rows),
        'salary': np.random.uniform(30000, 150000, n_rows).round(2),
        'department': np.random.choice(['Engineering', 'Marketing', 'Sales', 'HR', 'Finance'], n_rows),
        'active': np.random.choice([True, False], n_rows),
        'score': np.random.uniform(0, 100, n_rows).round(2)
    })


@pytest.fixture
def df_with_nulls():
    """Create a DataFrame with null values for testing null handling."""
    return pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', None, 'Charlie', 'Diana', None],
        'value': [100.0, 200.0, None, 400.0, None],
        'category': ['A', 'B', 'A', None, 'B']
    })


@pytest.fixture
def df_with_types():
    """Create a DataFrame with various data types for testing type handling."""
    return pd.DataFrame({
        'int_col': [1, 2, 3],
        'float_col': [1.1, 2.2, 3.3],
        'str_col': ['a', 'b', 'c'],
        'bool_col': [True, False, True],
        'date_col': pd.to_datetime(['2024-01-01', '2024-02-01', '2024-03-01']),
        'category_col': pd.Categorical(['low', 'medium', 'high'])
    })


# ==============================================================================
# File Fixtures
# ==============================================================================

@pytest.fixture
def sample_csv_file(temp_dir, sample_df):
    """Create a sample CSV file and return its path."""
    path = temp_dir / "sample.csv"
    sample_df.to_csv(path, index=False)
    return path


@pytest.fixture
def sample_parquet_file(temp_dir, sample_df):
    """Create a sample Parquet file and return its path."""
    path = temp_dir / "sample.parquet"
    sample_df.to_parquet(path, index=False)
    return path


@pytest.fixture
def sample_excel_file(temp_dir, sample_df):
    """Create a sample Excel file and return its path."""
    path = temp_dir / "sample.xlsx"
    sample_df.to_excel(path, index=False)
    return path


# ==============================================================================
# Database Fixtures
# ==============================================================================

@pytest.fixture
def db_manager():
    """Create a fresh DatabaseManager instance for testing."""
    from sqlshell.db.database_manager import DatabaseManager
    manager = DatabaseManager()
    yield manager
    # Cleanup
    try:
        manager.close_connection()
    except Exception:
        pass


@pytest.fixture
def db_manager_with_data(db_manager, sample_csv_file):
    """Create a DatabaseManager with sample data loaded."""
    db_manager.load_file(str(sample_csv_file))
    return db_manager


@pytest.fixture
def temp_sqlite_db(temp_dir, sample_df):
    """Create a temporary SQLite database with sample data."""
    import sqlite3
    db_path = temp_dir / "test.db"
    conn = sqlite3.connect(str(db_path))
    sample_df.to_sql('users', conn, index=False, if_exists='replace')
    conn.close()
    return db_path


@pytest.fixture
def temp_duckdb(temp_dir, sample_df):
    """Create a temporary DuckDB database with sample data."""
    import duckdb
    db_path = temp_dir / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    # Register the DataFrame and create table from it
    conn.register('sample_df_view', sample_df)
    conn.execute("CREATE TABLE users AS SELECT * FROM sample_df_view")
    conn.close()
    return db_path


# ==============================================================================
# GUI/PyQt6 Fixtures (marked with gui marker)
# ==============================================================================

@pytest.fixture
def qapp():
    """Create a QApplication instance for GUI tests."""
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app here as it might be used by other tests


# ==============================================================================
# SQL Test Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_sql_text():
    """Return sample SQL text with multiple statements for testing."""
    return """
-- First query: simple select
SELECT * FROM users;

-- Second query: with filtering
SELECT name, age 
FROM users 
WHERE age > 25;

/* Third query: 
   with aggregation */
SELECT department, COUNT(*) as count
FROM users
GROUP BY department;

-- Fourth query: with string containing semicolon
SELECT 'Hello; World' as greeting;
"""


@pytest.fixture
def sql_with_comments():
    """Return SQL with various comment styles."""
    return """
-- Single line comment
SELECT 1; -- Inline comment

/* Multi-line
   block
   comment */
SELECT 2;

# Hash comment (not standard but sometimes used)
SELECT 3;
"""


# ==============================================================================
# Utility Functions
# ==============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    # Markers are already configured in pyproject.toml
    pass


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Mark GUI tests
        if "gui" in item.nodeid or "qt" in item.nodeid.lower():
            item.add_marker(pytest.mark.gui)
        
        # Mark performance tests - check class name and test name, not filename
        # This avoids marking all tests in a file just because filename contains "performance"
        test_name = item.name.lower()
        parent_name = item.parent.name.lower() if item.parent else ""
        
        # Only auto-mark if the class or test name suggests performance testing
        is_performance_test = (
            "performance" in test_name or 
            "perf" in test_name or
            (parent_name.startswith("test") and "performance" in parent_name)
        )
        
        if is_performance_test:
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        
        # Mark database tests
        if "database" in item.nodeid or "db" in item.nodeid:
            item.add_marker(pytest.mark.database)


# ==============================================================================
# Skip Decorators
# ==============================================================================

requires_gui = pytest.mark.skipif(
    os.environ.get("DISPLAY") is None and sys.platform != "win32" and sys.platform != "darwin",
    reason="No display available for GUI tests"
)

requires_large_memory = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Test requires large memory, skipped in CI"
)

