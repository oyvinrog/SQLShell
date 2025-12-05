"""
Tests for the DatabaseManager class.

This module tests core database operations including:
- Connection management
- File loading (CSV, Parquet, Excel)
- SQL query execution
- Table management
- Database attachment
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path


class TestDatabaseManagerConnection:
    """Tests for database connection management."""

    def test_init_creates_connection(self, db_manager):
        """Test that initialization creates a connection."""
        assert db_manager.is_connected()
        assert db_manager.conn is not None

    def test_connection_info_default(self, db_manager):
        """Test default connection info."""
        info = db_manager.get_connection_info()
        assert "In-memory DuckDB" in info

    def test_close_connection(self, db_manager):
        """Test closing database connection."""
        db_manager.close_connection()
        assert db_manager.conn is None
        assert not db_manager.is_connected()

    def test_reconnect_after_close(self, db_manager):
        """Test that manager can reconnect after closing."""
        db_manager.close_connection()
        assert not db_manager.is_connected()
        
        db_manager._init_connection()
        assert db_manager.is_connected()


class TestDatabaseManagerFileLoading:
    """Tests for file loading functionality."""

    def test_load_csv_file(self, db_manager, sample_csv_file):
        """Test loading a CSV file."""
        result = db_manager.load_file(str(sample_csv_file))
        # load_file returns (table_name, dataframe) tuple on success
        assert result is not None
        assert isinstance(result, tuple)
        table_name, df = result
        assert table_name is not None
        
        # Verify table was created
        tables = list(db_manager.loaded_tables.keys())
        assert len(tables) >= 1

    def test_load_parquet_file(self, db_manager, sample_parquet_file):
        """Test loading a Parquet file."""
        result = db_manager.load_file(str(sample_parquet_file))
        # load_file returns (table_name, dataframe) tuple on success
        assert result is not None
        assert isinstance(result, tuple)
        table_name, df = result
        assert table_name is not None
        
        tables = list(db_manager.loaded_tables.keys())
        assert len(tables) >= 1

    def test_load_excel_file(self, db_manager, sample_excel_file):
        """Test loading an Excel file."""
        result = db_manager.load_file(str(sample_excel_file))
        # load_file returns (table_name, dataframe) tuple on success
        assert result is not None
        assert isinstance(result, tuple)
        table_name, df = result
        assert table_name is not None
        
        tables = list(db_manager.loaded_tables.keys())
        assert len(tables) >= 1

    def test_load_nonexistent_file(self, db_manager, temp_dir):
        """Test loading a file that doesn't exist."""
        fake_path = temp_dir / "nonexistent.csv"
        
        with pytest.raises(Exception):
            db_manager.load_file(str(fake_path))

    def test_load_multiple_files(self, db_manager, temp_dir, sample_df):
        """Test loading multiple files."""
        # Create multiple CSV files
        file1 = temp_dir / "file1.csv"
        file2 = temp_dir / "file2.csv"
        
        sample_df.to_csv(file1, index=False)
        sample_df.to_csv(file2, index=False)
        
        db_manager.load_file(str(file1))
        db_manager.load_file(str(file2))
        
        assert len(db_manager.loaded_tables) == 2


class TestDatabaseManagerQueries:
    """Tests for SQL query execution."""

    def test_execute_simple_query(self, db_manager_with_data):
        """Test executing a simple SELECT query."""
        tables = list(db_manager_with_data.loaded_tables.keys())
        table_name = tables[0]
        
        result = db_manager_with_data.execute_query(f"SELECT * FROM {table_name}")
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_execute_query_with_where(self, db_manager_with_data):
        """Test executing a query with WHERE clause."""
        tables = list(db_manager_with_data.loaded_tables.keys())
        table_name = tables[0]
        
        result = db_manager_with_data.execute_query(
            f"SELECT * FROM {table_name} WHERE age > 25"
        )
        assert result is not None
        assert all(result['age'] > 25)

    def test_execute_aggregate_query(self, db_manager_with_data):
        """Test executing an aggregate query."""
        tables = list(db_manager_with_data.loaded_tables.keys())
        table_name = tables[0]
        
        result = db_manager_with_data.execute_query(
            f"SELECT COUNT(*) as count FROM {table_name}"
        )
        assert result is not None
        assert 'count' in result.columns
        assert result['count'].iloc[0] > 0

    def test_execute_invalid_query(self, db_manager):
        """Test executing an invalid SQL query."""
        with pytest.raises(Exception):
            db_manager.execute_query("SELECT * FROM nonexistent_table_xyz")

    def test_execute_create_table(self, db_manager):
        """Test creating a table via SQL."""
        db_manager.execute_query(
            "CREATE TABLE test_table (id INT, name VARCHAR)"
        )
        # Should not raise


class TestDatabaseManagerTableOperations:
    """Tests for table management operations."""

    def test_get_table_names(self, db_manager_with_data):
        """Test getting loaded table names."""
        tables = list(db_manager_with_data.loaded_tables.keys())
        assert len(tables) > 0

    def test_remove_table(self, db_manager_with_data):
        """Test removing a single table."""
        tables = list(db_manager_with_data.loaded_tables.keys())
        table_name = tables[0]
        
        initial_count = len(db_manager_with_data.loaded_tables)
        db_manager_with_data.remove_table(table_name)
        
        assert len(db_manager_with_data.loaded_tables) == initial_count - 1
        assert table_name not in db_manager_with_data.loaded_tables

    def test_remove_multiple_tables(self, db_manager, temp_dir, sample_df):
        """Test removing multiple tables at once."""
        # Create and load multiple files
        files = []
        for i in range(3):
            path = temp_dir / f"table{i}.csv"
            sample_df.to_csv(path, index=False)
            files.append(path)
            db_manager.load_file(str(path))
        
        tables = list(db_manager.loaded_tables.keys())
        assert len(tables) == 3
        
        # Remove first 2 tables
        tables_to_remove = tables[:2]
        successful, failed = db_manager.remove_multiple_tables(tables_to_remove)
        
        assert len(successful) == 2
        assert len(failed) == 0
        assert len(db_manager.loaded_tables) == 1

    def test_remove_nonexistent_table(self, db_manager):
        """Test removing a table that doesn't exist."""
        successful, failed = db_manager.remove_multiple_tables(['nonexistent_table'])
        
        assert len(successful) == 0
        assert len(failed) == 1


class TestDatabaseManagerDatabaseAttachment:
    """Tests for attaching external databases."""

    @pytest.mark.database
    def test_attach_sqlite_database(self, db_manager, temp_sqlite_db):
        """Test attaching a SQLite database."""
        result = db_manager.open_database(str(temp_sqlite_db))
        assert result is True
        
        # Should have attached databases
        assert len(db_manager.attached_databases) > 0

    @pytest.mark.database
    def test_attach_duckdb_database(self, db_manager, temp_duckdb):
        """Test attaching a DuckDB database."""
        result = db_manager.open_database(str(temp_duckdb))
        # open_database returns True on success, or may return other values
        assert result is not None
        
        # DuckDB database should be attached (or tables loaded)
        assert len(db_manager.attached_databases) > 0 or len(db_manager.loaded_tables) > 0

    @pytest.mark.database
    def test_query_attached_database(self, db_manager, temp_sqlite_db):
        """Test querying data from an attached database."""
        db_manager.open_database(str(temp_sqlite_db))
        
        # Get the alias used for attachment
        alias = list(db_manager.attached_databases.keys())[0]
        
        # Query the attached database
        result = db_manager.execute_query(f"SELECT * FROM {alias}.users")
        assert result is not None
        assert len(result) > 0


class TestDatabaseManagerDataTypes:
    """Tests for handling various data types."""

    def test_load_df_with_nulls(self, db_manager, temp_dir, df_with_nulls):
        """Test loading DataFrame with null values."""
        path = temp_dir / "nulls.csv"
        df_with_nulls.to_csv(path, index=False)
        
        db_manager.load_file(str(path))
        
        tables = list(db_manager.loaded_tables.keys())
        result = db_manager.execute_query(f"SELECT * FROM {tables[0]}")
        
        # Check that nulls are preserved
        assert result['name'].isna().sum() == 2
        assert result['value'].isna().sum() == 2

    def test_load_df_with_various_types(self, db_manager, temp_dir, df_with_types):
        """Test loading DataFrame with various data types."""
        path = temp_dir / "types.parquet"
        df_with_types.to_parquet(path, index=False)
        
        db_manager.load_file(str(path))
        
        tables = list(db_manager.loaded_tables.keys())
        result = db_manager.execute_query(f"SELECT * FROM {tables[0]}")
        
        assert len(result) == 3
        assert 'int_col' in result.columns
        assert 'float_col' in result.columns


class TestDatabaseManagerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_dataframe(self, db_manager, temp_dir):
        """Test loading an empty CSV file."""
        path = temp_dir / "empty.csv"
        pd.DataFrame(columns=['a', 'b', 'c']).to_csv(path, index=False)
        
        db_manager.load_file(str(path))
        
        tables = list(db_manager.loaded_tables.keys())
        result = db_manager.execute_query(f"SELECT * FROM {tables[0]}")
        
        assert len(result) == 0
        assert list(result.columns) == ['a', 'b', 'c']

    def test_large_dataframe(self, db_manager, temp_dir, large_sample_df):
        """Test loading a larger DataFrame."""
        path = temp_dir / "large.parquet"
        large_sample_df.to_parquet(path, index=False)
        
        db_manager.load_file(str(path))
        
        tables = list(db_manager.loaded_tables.keys())
        result = db_manager.execute_query(f"SELECT COUNT(*) as cnt FROM {tables[0]}")
        
        assert result['cnt'].iloc[0] == 10000

    def test_special_characters_in_data(self, db_manager, temp_dir):
        """Test handling data with special characters."""
        df = pd.DataFrame({
            'name': ["O'Brien", 'Smith "Jr"', 'Test\nNewline'],
            'value': [1, 2, 3]
        })
        
        path = temp_dir / "special.csv"
        df.to_csv(path, index=False)
        
        db_manager.load_file(str(path))
        
        tables = list(db_manager.loaded_tables.keys())
        result = db_manager.execute_query(f"SELECT * FROM {tables[0]}")
        
        assert len(result) == 3

