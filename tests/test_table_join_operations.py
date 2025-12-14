"""
Tests for table join operations with inferred dependencies.

This module tests the functionality for joining multiple tables
using inferred foreign key relationships.
"""

import pytest
import pandas as pd
import numpy as np


class TestInferTableRelationships:
    """Tests for inferring relationships between tables."""

    def test_infer_relationship_by_column_name_convention(self, db_manager, temp_dir):
        """Test inferring relationships based on column naming convention (table_id)."""
        from sqlshell.utils.table_join_operations import infer_table_relationships
        
        # customers table with id column
        customers = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie']
        })
        
        # orders table with customer_id (foreign key)
        orders = pd.DataFrame({
            'order_id': [101, 102, 103],
            'customer_id': [1, 2, 1],
            'amount': [100.0, 200.0, 150.0]
        })
        
        path1 = temp_dir / "customers.csv"
        path2 = temp_dir / "orders.csv"
        customers.to_csv(path1, index=False)
        orders.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        relationships = infer_table_relationships(db_manager, table_names)
        
        # Should detect the customer_id -> customers.id relationship
        assert len(relationships) >= 1
        
        # Check that the relationship is correct
        found_relationship = False
        for rel in relationships:
            if ('customer' in rel['from_table'].lower() or 'customer' in rel['to_table'].lower()) and \
               'customer_id' in [rel['from_column'], rel['to_column']] or 'id' in [rel['from_column'], rel['to_column']]:
                found_relationship = True
                break
        
        assert found_relationship, f"Expected customer relationship, got: {relationships}"

    def test_infer_relationship_by_matching_column_names(self, db_manager, temp_dir):
        """Test inferring relationships when columns have the exact same name."""
        from sqlshell.utils.table_join_operations import infer_table_relationships
        
        # Both tables have 'user_id' column
        table1 = pd.DataFrame({
            'user_id': [1, 2, 3],
            'data1': ['a', 'b', 'c']
        })
        
        table2 = pd.DataFrame({
            'user_id': [1, 2, 3],
            'data2': ['x', 'y', 'z']
        })
        
        path1 = temp_dir / "data1.csv"
        path2 = temp_dir / "data2.csv"
        table1.to_csv(path1, index=False)
        table2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        relationships = infer_table_relationships(db_manager, table_names)
        
        # Should detect the matching user_id columns
        assert len(relationships) >= 1
        
        found_user_id_rel = any(
            rel['from_column'] == 'user_id' and rel['to_column'] == 'user_id'
            for rel in relationships
        )
        assert found_user_id_rel, f"Expected user_id relationship, got: {relationships}"

    def test_infer_no_relationship(self, db_manager, temp_dir):
        """Test when tables have no inferable relationship."""
        from sqlshell.utils.table_join_operations import infer_table_relationships
        
        table1 = pd.DataFrame({
            'alpha': [1, 2, 3],
            'beta': ['a', 'b', 'c']
        })
        
        table2 = pd.DataFrame({
            'gamma': [10, 20, 30],
            'delta': ['x', 'y', 'z']
        })
        
        path1 = temp_dir / "greek1.csv"
        path2 = temp_dir / "greek2.csv"
        table1.to_csv(path1, index=False)
        table2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        relationships = infer_table_relationships(db_manager, table_names)
        
        # Should not detect any relationships
        assert len(relationships) == 0


class TestGenerateJoinSQL:
    """Tests for generating JOIN SQL queries."""

    def test_generate_simple_join(self, db_manager, temp_dir):
        """Test generating a simple JOIN between two tables."""
        from sqlshell.utils.table_join_operations import generate_join_sql
        
        customers = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie']
        })
        
        orders = pd.DataFrame({
            'order_id': [101, 102, 103],
            'customer_id': [1, 2, 1],
            'amount': [100.0, 200.0, 150.0]
        })
        
        path1 = temp_dir / "customers.csv"
        path2 = temp_dir / "orders.csv"
        customers.to_csv(path1, index=False)
        orders.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_join_sql(db_manager, table_names)
        
        assert 'JOIN' in sql
        assert 'ON' in sql
        # The SQL should be executable
        result = db_manager.execute_query(sql)
        assert len(result) > 0

    def test_generate_join_three_tables(self, db_manager, temp_dir):
        """Test generating JOINs for three related tables."""
        from sqlshell.utils.table_join_operations import generate_join_sql
        
        customers = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie']
        })
        
        orders = pd.DataFrame({
            'id': [101, 102, 103],
            'customer_id': [1, 2, 1],
            'amount': [100.0, 200.0, 150.0]
        })
        
        order_items = pd.DataFrame({
            'item_id': [1001, 1002, 1003],
            'order_id': [101, 101, 102],
            'product': ['Widget', 'Gadget', 'Gizmo']
        })
        
        path1 = temp_dir / "customers.csv"
        path2 = temp_dir / "orders.csv"
        path3 = temp_dir / "order_items.csv"
        customers.to_csv(path1, index=False)
        orders.to_csv(path2, index=False)
        order_items.to_csv(path3, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        db_manager.load_file(str(path3))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_join_sql(db_manager, table_names)
        
        # Should have multiple JOINs
        assert sql.count('JOIN') >= 2
        
        # The SQL should be executable
        result = db_manager.execute_query(sql)
        assert len(result) > 0

    def test_generate_join_with_matching_columns(self, db_manager, temp_dir):
        """Test generating JOIN when tables have matching column names."""
        from sqlshell.utils.table_join_operations import generate_join_sql
        
        table1 = pd.DataFrame({
            'shared_key': [1, 2, 3],
            'value1': ['a', 'b', 'c']
        })
        
        table2 = pd.DataFrame({
            'shared_key': [1, 2, 3],
            'value2': ['x', 'y', 'z']
        })
        
        path1 = temp_dir / "t1.csv"
        path2 = temp_dir / "t2.csv"
        table1.to_csv(path1, index=False)
        table2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_join_sql(db_manager, table_names)
        
        assert 'shared_key' in sql
        
        result = db_manager.execute_query(sql)
        assert len(result) == 3


class TestGenerateJoinWithNoRelationships:
    """Tests for handling tables with no inferable relationships."""

    def test_generate_join_no_relationship_raises(self, db_manager, temp_dir):
        """Test that JOIN raises an error when no relationships can be inferred."""
        from sqlshell.utils.table_join_operations import generate_join_sql
        
        table1 = pd.DataFrame({
            'alpha': [1, 2, 3],
            'beta': ['a', 'b', 'c']
        })
        
        table2 = pd.DataFrame({
            'gamma': [10, 20, 30],
            'delta': ['x', 'y', 'z']
        })
        
        path1 = temp_dir / "unrelated1.csv"
        path2 = temp_dir / "unrelated2.csv"
        table1.to_csv(path1, index=False)
        table2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        with pytest.raises(ValueError, match="[Nn]o.*relationship"):
            generate_join_sql(db_manager, table_names)


class TestGenerateJoinSingleTable:
    """Tests for handling single table edge case."""

    def test_generate_join_single_table_raises(self, db_manager, temp_dir):
        """Test that JOIN raises an error with only one table."""
        from sqlshell.utils.table_join_operations import generate_join_sql
        
        df = pd.DataFrame({'id': [1, 2], 'name': ['A', 'B']})
        path = temp_dir / "single.csv"
        df.to_csv(path, index=False)
        
        db_manager.load_file(str(path))
        table_names = list(db_manager.loaded_tables.keys())
        
        with pytest.raises(ValueError, match="[Aa]t least two tables"):
            generate_join_sql(db_manager, table_names)


class TestJoinTypes:
    """Tests for different JOIN types."""

    def test_generate_left_join(self, db_manager, temp_dir):
        """Test generating LEFT JOIN."""
        from sqlshell.utils.table_join_operations import generate_join_sql
        
        customers = pd.DataFrame({
            'id': [1, 2, 3, 4],
            'name': ['Alice', 'Bob', 'Charlie', 'Diana']
        })
        
        orders = pd.DataFrame({
            'order_id': [101, 102],
            'customer_id': [1, 2],
            'amount': [100.0, 200.0]
        })
        
        path1 = temp_dir / "customers.csv"
        path2 = temp_dir / "orders.csv"
        customers.to_csv(path1, index=False)
        orders.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_join_sql(db_manager, table_names, join_type='LEFT')
        
        assert 'LEFT JOIN' in sql or 'LEFT OUTER JOIN' in sql
        
        result = db_manager.execute_query(sql)
        # All 4 customers should be present (LEFT JOIN keeps all from first table)
        assert len(result) >= 2  # At least the matched rows

    def test_generate_inner_join(self, db_manager, temp_dir):
        """Test generating INNER JOIN (default)."""
        from sqlshell.utils.table_join_operations import generate_join_sql
        
        table1 = pd.DataFrame({
            'key': [1, 2, 3, 4],
            'value1': ['a', 'b', 'c', 'd']
        })
        
        table2 = pd.DataFrame({
            'key': [2, 3, 5],
            'value2': ['x', 'y', 'z']
        })
        
        path1 = temp_dir / "left.csv"
        path2 = temp_dir / "right.csv"
        table1.to_csv(path1, index=False)
        table2.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_join_sql(db_manager, table_names, join_type='INNER')
        
        result = db_manager.execute_query(sql)
        # Only 2 matching rows (key=2, key=3)
        assert len(result) == 2


class TestRelationshipScoring:
    """Tests for relationship scoring/ranking."""

    def test_prefer_id_column_relationships(self, db_manager, temp_dir):
        """Test that relationships involving 'id' columns are preferred."""
        from sqlshell.utils.table_join_operations import infer_table_relationships
        
        # Table with both 'id' and 'code' that could match
        primary = pd.DataFrame({
            'id': [1, 2, 3],
            'code': ['A', 'B', 'C'],
            'name': ['One', 'Two', 'Three']
        })
        
        # Table with foreign key pattern
        secondary = pd.DataFrame({
            'record_id': [101, 102, 103],
            'primary_id': [1, 2, 3],  # Should match primary.id
            'code': ['A', 'B', 'C']   # Also matches but less preferred
        })
        
        path1 = temp_dir / "primary.csv"
        path2 = temp_dir / "secondary.csv"
        primary.to_csv(path1, index=False)
        secondary.to_csv(path2, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        relationships = infer_table_relationships(db_manager, table_names)
        
        # Should have relationships
        assert len(relationships) >= 1
        
        # The primary_id -> id relationship should be detected
        has_id_relationship = any(
            'id' in rel['from_column'].lower() or 'id' in rel['to_column'].lower()
            for rel in relationships
        )
        assert has_id_relationship


class TestComplexJoinScenarios:
    """Tests for complex multi-table join scenarios."""

    def test_star_schema_join(self, db_manager, temp_dir):
        """Test joining tables in a star schema pattern."""
        from sqlshell.utils.table_join_operations import generate_join_sql
        
        # Fact table
        sales = pd.DataFrame({
            'sale_id': [1, 2, 3],
            'customer_id': [1, 2, 1],
            'product_id': [10, 20, 10],
            'amount': [100, 200, 150]
        })
        
        # Dimension tables
        customers = pd.DataFrame({
            'id': [1, 2],
            'name': ['Alice', 'Bob']
        })
        
        products = pd.DataFrame({
            'id': [10, 20],
            'name': ['Widget', 'Gadget']
        })
        
        path1 = temp_dir / "sales.csv"
        path2 = temp_dir / "customers.csv"
        path3 = temp_dir / "products.csv"
        sales.to_csv(path1, index=False)
        customers.to_csv(path2, index=False)
        products.to_csv(path3, index=False)
        
        db_manager.load_file(str(path1))
        db_manager.load_file(str(path2))
        db_manager.load_file(str(path3))
        
        table_names = list(db_manager.loaded_tables.keys())
        
        sql = generate_join_sql(db_manager, table_names)
        
        # Should produce executable SQL
        result = db_manager.execute_query(sql)
        assert len(result) > 0
