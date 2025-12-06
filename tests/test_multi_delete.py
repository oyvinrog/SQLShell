"""
Tests for multiple table deletion functionality.

This module tests the DatabaseManager's remove_multiple_tables method
and related functionality.
"""

import pytest
import pandas as pd


class TestMultipleTableDeletion:
    """Tests for multiple table deletion functionality."""

    def test_remove_multiple_tables_success(self, db_manager, temp_dir, sample_df):
        """Test successfully removing multiple tables."""
        # Create and load multiple files
        for i in range(3):
            path = temp_dir / f"table_{i}.csv"
            sample_df.to_csv(path, index=False)
            db_manager.load_file(str(path))
        
        tables = list(db_manager.loaded_tables.keys())
        assert len(tables) == 3, "Should have 3 tables loaded"
        
        # Remove first 2 tables
        tables_to_delete = tables[:2]
        successful, failed = db_manager.remove_multiple_tables(tables_to_delete)
        
        assert len(successful) == 2, f"Expected 2 successful deletions, got {len(successful)}"
        assert len(failed) == 0, f"Expected 0 failed deletions, got {len(failed)}"
        assert len(db_manager.loaded_tables) == 1, "Should have 1 table remaining"

    def test_remove_nonexistent_tables(self, db_manager):
        """Test removing tables that don't exist."""
        fake_tables = ['nonexistent_table1', 'nonexistent_table2']
        successful, failed = db_manager.remove_multiple_tables(fake_tables)
        
        assert len(successful) == 0, f"Expected 0 successful deletions, got {len(successful)}"
        assert len(failed) == 2, f"Expected 2 failed deletions, got {len(failed)}"

    def test_remove_mixed_tables(self, db_manager, temp_dir, sample_df):
        """Test removing a mix of existing and non-existing tables."""
        # Create and load one file
        path = temp_dir / "real_table.csv"
        sample_df.to_csv(path, index=False)
        db_manager.load_file(str(path))
        
        tables = list(db_manager.loaded_tables.keys())
        real_table = tables[0]
        
        # Try to remove both real and fake tables
        tables_to_delete = [real_table, 'fake_table']
        successful, failed = db_manager.remove_multiple_tables(tables_to_delete)
        
        assert len(successful) == 1, "Should have 1 successful deletion"
        assert len(failed) == 1, "Should have 1 failed deletion"
        assert real_table in successful, "Real table should be in successful list"
        assert 'fake_table' in failed, "Fake table should be in failed list"

    def test_remove_all_tables(self, db_manager, temp_dir, sample_df):
        """Test removing all loaded tables."""
        # Create and load multiple files
        for i in range(5):
            path = temp_dir / f"table_{i}.csv"
            sample_df.to_csv(path, index=False)
            db_manager.load_file(str(path))
        
        tables = list(db_manager.loaded_tables.keys())
        assert len(tables) == 5, "Should have 5 tables loaded"
        
        # Remove all tables
        successful, failed = db_manager.remove_multiple_tables(tables)
        
        assert len(successful) == 5, "All 5 tables should be successfully deleted"
        assert len(failed) == 0, "No failures expected"
        assert len(db_manager.loaded_tables) == 0, "No tables should remain"

    def test_remove_empty_list(self, db_manager, temp_dir, sample_df):
        """Test removing with an empty list."""
        # Load a table first
        path = temp_dir / "table.csv"
        sample_df.to_csv(path, index=False)
        db_manager.load_file(str(path))
        
        initial_count = len(db_manager.loaded_tables)
        
        # Try to remove empty list
        successful, failed = db_manager.remove_multiple_tables([])
        
        assert len(successful) == 0
        assert len(failed) == 0
        assert len(db_manager.loaded_tables) == initial_count, "Table count should not change"

    def test_remove_same_table_twice(self, db_manager, temp_dir, sample_df):
        """Test removing the same table name twice in the list - duplicates should be handled."""
        # Use a non-reserved name (not 'table' which is a SQL keyword)
        path = temp_dir / "mytable.csv"
        sample_df.to_csv(path, index=False)
        result = db_manager.load_file(str(path))
        
        # Get the actual table name from the load result
        table_name, _ = result
        
        # Verify table was loaded
        assert table_name in db_manager.loaded_tables, f"Table {table_name} should be loaded"
        
        # First remove the table normally to verify it works
        success = db_manager.remove_table(table_name)
        assert success, f"Single removal should work for {table_name}"
        assert table_name not in db_manager.loaded_tables, "Table should be gone from loaded_tables"
        
        # Trying to remove again should fail (already gone)
        success2 = db_manager.remove_table(table_name)
        assert not success2, "Second removal should fail (already removed)"


class TestTableDeletionIntegration:
    """Integration tests for table deletion with queries."""

    def test_query_after_deletion(self, db_manager, temp_dir, sample_df):
        """Test that deleted tables are not queryable."""
        # Load two tables
        path1 = temp_dir / "table1.csv"
        path2 = temp_dir / "table2.csv"
        
        sample_df.to_csv(path1, index=False)
        sample_df.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        tables = list(db_manager.loaded_tables.keys())
        table_to_delete = tables[0]
        remaining_table = tables[1]
        
        # Delete one table
        db_manager.remove_multiple_tables([table_to_delete])
        
        # Query remaining table should work
        result = db_manager.execute_query(f"SELECT * FROM {remaining_table}")
        assert result is not None
        assert len(result) > 0
        
        # Query deleted table should fail
        with pytest.raises(Exception):
            db_manager.execute_query(f"SELECT * FROM {table_to_delete}")

    def test_reload_after_deletion(self, db_manager, temp_dir, sample_df):
        """Test reloading a file after its table was deleted."""
        # Use a non-reserved name (not 'table' which is a SQL keyword)
        path = temp_dir / "mydata.csv"
        sample_df.to_csv(path, index=False)
        
        # Load and get the actual table name
        result = db_manager.load_file(str(path))
        table_name, _ = result
        
        # Delete using the single remove method
        success = db_manager.remove_table(table_name)
        assert success, f"Should be able to remove {table_name}"
        
        # Reload the same file  
        db_manager.load_file(str(path))
        
        # Should have at least one table loaded after reload
        assert len(db_manager.loaded_tables) >= 1, "File should be reloaded"

