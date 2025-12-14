"""
Tests for table set operations (UNION, UNION ALL, EXCEPT, INTERSECT).

This module tests the functionality for combining multiple tables
using SQL set operations based on common columns.
"""

import pytest
import pandas as pd
import numpy as np


class TestFindCommonColumns:
    """Tests for finding common columns between tables."""

    def test_find_common_columns_identical_tables(self, db_manager, temp_dir):
        """Test finding common columns between identical tables."""
        from sqlshell.utils.table_set_operations import find_common_columns
        
        # Create two identical tables
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35]
        })
        
        path1 = temp_dir / "table1.csv"
        path2 = temp_dir / "table2.csv"
        df.to_csv(path1, index=False)
        df.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        common_cols = find_common_columns(db_manager, table_names)
        
        assert set(common_cols) == {'id', 'name', 'age'}

    def test_find_common_columns_partial_overlap(self, db_manager, temp_dir):
        """Test finding common columns when tables have partial column overlap."""
        from sqlshell.utils.table_set_operations import find_common_columns
        
        df1 = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35]
        })
        
        df2 = pd.DataFrame({
            'id': [4, 5, 6],
            'name': ['Diana', 'Eve', 'Frank'],
            'salary': [50000, 60000, 70000]
        })
        
        path1 = temp_dir / "employees.csv"
        path2 = temp_dir / "contractors.csv"
        df1.to_csv(path1, index=False)
        df2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        common_cols = find_common_columns(db_manager, table_names)
        
        assert set(common_cols) == {'id', 'name'}

    def test_find_common_columns_no_overlap(self, db_manager, temp_dir):
        """Test finding common columns when tables have no common columns."""
        from sqlshell.utils.table_set_operations import find_common_columns
        
        df1 = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie']
        })
        
        df2 = pd.DataFrame({
            'product_id': [100, 200, 300],
            'price': [10.99, 20.99, 30.99]
        })
        
        path1 = temp_dir / "users.csv"
        path2 = temp_dir / "products.csv"
        df1.to_csv(path1, index=False)
        df2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        common_cols = find_common_columns(db_manager, table_names)
        
        assert common_cols == []

    def test_find_common_columns_three_tables(self, db_manager, temp_dir):
        """Test finding common columns across three tables."""
        from sqlshell.utils.table_set_operations import find_common_columns
        
        df1 = pd.DataFrame({'id': [1], 'name': ['A'], 'x': [1]})
        df2 = pd.DataFrame({'id': [2], 'name': ['B'], 'y': [2]})
        df3 = pd.DataFrame({'id': [3], 'name': ['C'], 'z': [3]})
        
        path1 = temp_dir / "t1.csv"
        path2 = temp_dir / "t2.csv"
        path3 = temp_dir / "t3.csv"
        df1.to_csv(path1, index=False)
        df2.to_csv(path2, index=False)
        df3.to_csv(path3, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        db_manager.load_file(str(path3))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        common_cols = find_common_columns(db_manager, table_names)
        
        assert set(common_cols) == {'id', 'name'}


class TestGenerateUnionAllSQL:
    """Tests for generating UNION ALL SQL queries."""

    def test_generate_union_all_two_tables(self, db_manager, temp_dir):
        """Test generating UNION ALL for two tables."""
        from sqlshell.utils.table_set_operations import generate_set_operation_sql
        
        df1 = pd.DataFrame({'id': [1, 2], 'name': ['A', 'B']})
        df2 = pd.DataFrame({'id': [3, 4], 'name': ['C', 'D']})
        
        path1 = temp_dir / "a.csv"
        path2 = temp_dir / "b.csv"
        df1.to_csv(path1, index=False)
        df2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_set_operation_sql(db_manager, table_names, 'UNION ALL')
        
        assert 'UNION ALL' in sql
        assert 'SELECT' in sql
        # Both table names should be in the query
        for name in table_names:
            assert name in sql

    def test_generate_union_all_produces_valid_sql(self, db_manager, temp_dir):
        """Test that generated UNION ALL SQL is executable."""
        from sqlshell.utils.table_set_operations import generate_set_operation_sql
        
        df1 = pd.DataFrame({'id': [1, 2], 'name': ['Alice', 'Bob']})
        df2 = pd.DataFrame({'id': [3, 4], 'name': ['Charlie', 'Diana']})
        
        path1 = temp_dir / "users1.csv"
        path2 = temp_dir / "users2.csv"
        df1.to_csv(path1, index=False)
        df2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_set_operation_sql(db_manager, table_names, 'UNION ALL')
        
        # Execute the query
        result = db_manager.execute_query(sql)
        
        assert len(result) == 4  # All rows combined
        assert set(result.columns) == {'id', 'name'}


class TestGenerateUnionSQL:
    """Tests for generating UNION SQL queries (removes duplicates)."""

    def test_generate_union_removes_duplicates(self, db_manager, temp_dir):
        """Test that UNION removes duplicate rows."""
        from sqlshell.utils.table_set_operations import generate_set_operation_sql
        
        # Create tables with overlapping data
        df1 = pd.DataFrame({'id': [1, 2, 3], 'name': ['Alice', 'Bob', 'Charlie']})
        df2 = pd.DataFrame({'id': [2, 3, 4], 'name': ['Bob', 'Charlie', 'Diana']})
        
        path1 = temp_dir / "set1.csv"
        path2 = temp_dir / "set2.csv"
        df1.to_csv(path1, index=False)
        df2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_set_operation_sql(db_manager, table_names, 'UNION')
        
        result = db_manager.execute_query(sql)
        
        # Should have 4 unique rows (1-Alice, 2-Bob, 3-Charlie, 4-Diana)
        assert len(result) == 4


class TestGenerateExceptSQL:
    """Tests for generating EXCEPT SQL queries."""

    def test_generate_except_sql(self, db_manager, temp_dir):
        """Test generating EXCEPT query."""
        from sqlshell.utils.table_set_operations import generate_set_operation_sql
        
        df1 = pd.DataFrame({'id': [1, 2, 3], 'name': ['Alice', 'Bob', 'Charlie']})
        df2 = pd.DataFrame({'id': [2, 3], 'name': ['Bob', 'Charlie']})
        
        path1 = temp_dir / "all_users.csv"
        path2 = temp_dir / "excluded.csv"
        df1.to_csv(path1, index=False)
        df2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_set_operation_sql(db_manager, table_names, 'EXCEPT')
        
        result = db_manager.execute_query(sql)
        
        # Should have 1 row (1-Alice) that's in first but not second
        assert len(result) == 1
        assert result['name'].iloc[0] == 'Alice'


class TestGenerateIntersectSQL:
    """Tests for generating INTERSECT SQL queries."""

    def test_generate_intersect_sql(self, db_manager, temp_dir):
        """Test generating INTERSECT query."""
        from sqlshell.utils.table_set_operations import generate_set_operation_sql
        
        df1 = pd.DataFrame({'id': [1, 2, 3], 'name': ['Alice', 'Bob', 'Charlie']})
        df2 = pd.DataFrame({'id': [2, 3, 4], 'name': ['Bob', 'Charlie', 'Diana']})
        
        path1 = temp_dir / "group1.csv"
        path2 = temp_dir / "group2.csv"
        df1.to_csv(path1, index=False)
        df2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_set_operation_sql(db_manager, table_names, 'INTERSECT')
        
        result = db_manager.execute_query(sql)
        
        # Should have 2 rows (2-Bob, 3-Charlie) that are in both
        assert len(result) == 2
        assert set(result['name'].tolist()) == {'Bob', 'Charlie'}


class TestSetOperationWithNoCommonColumns:
    """Tests for handling tables with no common columns."""

    def test_set_operation_no_common_columns_raises(self, db_manager, temp_dir):
        """Test that set operations raise an error when no common columns exist."""
        from sqlshell.utils.table_set_operations import generate_set_operation_sql
        
        df1 = pd.DataFrame({'id': [1, 2], 'name': ['A', 'B']})
        df2 = pd.DataFrame({'product_id': [100], 'price': [10.99]})
        
        path1 = temp_dir / "users.csv"
        path2 = temp_dir / "products.csv"
        df1.to_csv(path1, index=False)
        df2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        with pytest.raises(ValueError, match="[Nn]o common columns"):
            generate_set_operation_sql(db_manager, table_names, 'UNION ALL')


class TestSetOperationWithSingleTable:
    """Tests for handling single table edge case."""

    def test_set_operation_single_table_raises(self, db_manager, temp_dir):
        """Test that set operations raise an error with only one table."""
        from sqlshell.utils.table_set_operations import generate_set_operation_sql
        
        df = pd.DataFrame({'id': [1, 2], 'name': ['A', 'B']})
        path = temp_dir / "only_table.csv"
        df.to_csv(path, index=False)
        
        db_manager.load_file(str(path))
        table_names = list(db_manager.loaded_tables.keys())
        
        with pytest.raises(ValueError, match="[Aa]t least two tables"):
            generate_set_operation_sql(db_manager, table_names, 'UNION ALL')


class TestSetOperationMultipleTables:
    """Tests for set operations with more than two tables."""

    def test_union_all_three_tables(self, db_manager, temp_dir):
        """Test UNION ALL with three tables."""
        from sqlshell.utils.table_set_operations import generate_set_operation_sql
        
        df1 = pd.DataFrame({'id': [1], 'name': ['A']})
        df2 = pd.DataFrame({'id': [2], 'name': ['B']})
        df3 = pd.DataFrame({'id': [3], 'name': ['C']})
        
        path1 = temp_dir / "t1.csv"
        path2 = temp_dir / "t2.csv"
        path3 = temp_dir / "t3.csv"
        df1.to_csv(path1, index=False)
        df2.to_csv(path2, index=False)
        df3.to_csv(path3, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        db_manager.load_file(str(path3))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_set_operation_sql(db_manager, table_names, 'UNION ALL')
        
        result = db_manager.execute_query(sql)
        
        assert len(result) == 3
        assert set(result['name'].tolist()) == {'A', 'B', 'C'}
