"""
Table set operations module.

This module provides functionality for combining multiple tables using SQL set operations
(UNION, UNION ALL, EXCEPT, INTERSECT) based on their common columns.
"""

from typing import List, Optional


def find_common_columns(db_manager, table_names: List[str]) -> List[str]:
    """
    Find columns that are common across all specified tables.
    
    Args:
        db_manager: DatabaseManager instance with loaded tables
        table_names: List of table names to find common columns for
        
    Returns:
        List of column names that exist in all specified tables
    """
    if not table_names:
        return []
    
    # Get columns for each table
    all_column_sets = []
    for table_name in table_names:
        if table_name in db_manager.table_columns:
            columns = db_manager.table_columns[table_name]
            all_column_sets.append(set(columns))
        else:
            # Try to get columns from the table directly
            try:
                source = db_manager.loaded_tables.get(table_name, '')
                if source.startswith('database:'):
                    alias = source.split(':')[1]
                    query = f'SELECT * FROM {alias}."{table_name}" LIMIT 0'
                else:
                    query = f'SELECT * FROM "{table_name}" LIMIT 0'
                
                result = db_manager.execute_query(query)
                all_column_sets.append(set(result.columns.tolist()))
            except Exception:
                all_column_sets.append(set())
    
    if not all_column_sets:
        return []
    
    # Find intersection of all column sets
    common_columns = all_column_sets[0]
    for column_set in all_column_sets[1:]:
        common_columns = common_columns.intersection(column_set)
    
    return list(common_columns)


def _get_qualified_table_name(db_manager, table_name: str) -> str:
    """
    Get the fully qualified table name for SQL queries.
    
    Args:
        db_manager: DatabaseManager instance
        table_name: Name of the table
        
    Returns:
        Qualified table name (e.g., 'db.table_name' for database tables)
    """
    source = db_manager.loaded_tables.get(table_name, '')
    if source.startswith('database:'):
        alias = source.split(':')[1]
        return f'{alias}."{table_name}"'
    else:
        return f'"{table_name}"'


def generate_set_operation_sql(
    db_manager,
    table_names: List[str],
    operation: str,
    columns: Optional[List[str]] = None
) -> str:
    """
    Generate a SQL query that combines tables using a set operation.
    
    Args:
        db_manager: DatabaseManager instance with loaded tables
        table_names: List of table names to combine
        operation: Set operation to use ('UNION', 'UNION ALL', 'EXCEPT', 'INTERSECT')
        columns: Optional list of columns to select. If None, uses common columns.
        
    Returns:
        SQL query string
        
    Raises:
        ValueError: If fewer than 2 tables are provided or no common columns exist
    """
    # Validate inputs
    if len(table_names) < 2:
        raise ValueError("At least two tables are required for set operations")
    
    # Normalize operation
    operation = operation.upper().strip()
    valid_operations = {'UNION', 'UNION ALL', 'EXCEPT', 'INTERSECT'}
    if operation not in valid_operations:
        raise ValueError(f"Invalid operation '{operation}'. Must be one of: {valid_operations}")
    
    # Get common columns if not specified
    if columns is None:
        columns = find_common_columns(db_manager, table_names)
    
    if not columns:
        raise ValueError("No common columns found between the specified tables")
    
    # Build column list for SELECT
    column_list = ', '.join(f'"{col}"' for col in columns)
    
    # Build individual SELECT statements
    select_statements = []
    for table_name in table_names:
        qualified_name = _get_qualified_table_name(db_manager, table_name)
        select_statements.append(f"SELECT {column_list} FROM {qualified_name}")
    
    # Combine with the set operation
    separator = f"\n{operation}\n"
    sql = separator.join(select_statements)
    
    return sql


def get_available_set_operations() -> List[dict]:
    """
    Get a list of available set operations with their descriptions.
    
    Returns:
        List of dictionaries with 'name', 'sql', and 'description' keys
    """
    return [
        {
            'name': 'UNION ALL',
            'sql': 'UNION ALL',
            'description': 'Combine all rows from selected tables (keeps duplicates)'
        },
        {
            'name': 'UNION',
            'sql': 'UNION',
            'description': 'Combine rows from selected tables (removes duplicates)'
        },
        {
            'name': 'EXCEPT',
            'sql': 'EXCEPT',
            'description': 'Rows in first table but not in subsequent tables'
        },
        {
            'name': 'INTERSECT',
            'sql': 'INTERSECT',
            'description': 'Only rows that exist in all selected tables'
        }
    ]
