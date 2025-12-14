"""
Table join operations module.

This module provides functionality for joining multiple tables using inferred
foreign key relationships based on column naming conventions and matching values.
"""

from typing import List, Dict, Optional
import re


def _normalize_table_name(name: str) -> str:
    """Normalize a table name for matching (lowercase, remove trailing 's' for plurals)."""
    name = name.lower()
    # Remove common plural suffixes
    if name.endswith('ies'):
        return name[:-3] + 'y'  # companies -> company
    elif name.endswith('es') and len(name) > 3:
        return name[:-2]  # matches -> match
    elif name.endswith('s') and len(name) > 2:
        return name[:-1]  # customers -> customer
    return name


def _table_names_match(prefix: str, table_name: str) -> bool:
    """Check if a column prefix matches a table name (handles plurals)."""
    prefix_norm = _normalize_table_name(prefix)
    table_norm = _normalize_table_name(table_name)
    
    return (
        prefix_norm == table_norm or
        table_norm.startswith(prefix_norm) or
        prefix_norm.startswith(table_norm) or
        table_norm.endswith(prefix_norm) or
        prefix_norm.endswith(table_norm)
    )


def infer_table_relationships(db_manager, table_names: List[str]) -> List[Dict]:
    """
    Infer relationships between tables based on column naming conventions.
    
    Looks for patterns like:
    - table_id column referencing table.id
    - Matching column names across tables
    
    Args:
        db_manager: DatabaseManager instance with loaded tables
        table_names: List of table names to analyze
        
    Returns:
        List of relationship dictionaries with keys:
        - from_table: Table containing the foreign key
        - from_column: Column in from_table
        - to_table: Referenced table
        - to_column: Referenced column
        - confidence: Score indicating relationship strength (higher = more confident)
    """
    relationships = []
    
    # Get columns for all tables
    table_columns = {}
    for table_name in table_names:
        if table_name in db_manager.table_columns:
            table_columns[table_name] = db_manager.table_columns[table_name]
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
                table_columns[table_name] = list(result.columns)
            except Exception:
                table_columns[table_name] = []
    
    # Look for relationships
    for table_name, columns in table_columns.items():
        for column in columns:
            col_lower = column.lower()
            
            # Pattern 1: column_name ends with '_id' -> look for 'column_name' table with 'id'
            if col_lower.endswith('_id'):
                potential_table_prefix = col_lower[:-3]  # Remove '_id'
                
                for other_table in table_names:
                    if other_table == table_name:
                        continue
                    
                    other_columns_lower = [c.lower() for c in table_columns.get(other_table, [])]
                    
                    # Check if the table name matches the prefix (handles plurals)
                    if _table_names_match(potential_table_prefix, other_table):
                        # Look for 'id' column in the other table
                        if 'id' in other_columns_lower:
                            # Find the actual column name (case-preserved)
                            id_col = None
                            for c in table_columns.get(other_table, []):
                                if c.lower() == 'id':
                                    id_col = c
                                    break
                            
                            if id_col:
                                relationships.append({
                                    'from_table': table_name,
                                    'from_column': column,
                                    'to_table': other_table,
                                    'to_column': id_col,
                                    'confidence': 0.9  # High confidence for naming convention
                                })
            
            # Pattern 2: column ends with 'Id' (camelCase)
            elif col_lower.endswith('id') and len(col_lower) > 2:
                potential_table_prefix = col_lower[:-2]  # Remove 'id'
                
                for other_table in table_names:
                    if other_table == table_name:
                        continue
                    
                    other_columns_lower = [c.lower() for c in table_columns.get(other_table, [])]
                    
                    if _table_names_match(potential_table_prefix, other_table):
                        if 'id' in other_columns_lower:
                            id_col = None
                            for c in table_columns.get(other_table, []):
                                if c.lower() == 'id':
                                    id_col = c
                                    break
                            
                            if id_col:
                                relationships.append({
                                    'from_table': table_name,
                                    'from_column': column,
                                    'to_table': other_table,
                                    'to_column': id_col,
                                    'confidence': 0.85
                                })
    
    # Pattern 3: Matching column names across tables (same name in multiple tables)
    all_columns = {}  # column_name -> [(table_name, column_name), ...]
    for table_name, columns in table_columns.items():
        for column in columns:
            col_lower = column.lower()
            if col_lower not in all_columns:
                all_columns[col_lower] = []
            all_columns[col_lower].append((table_name, column))
    
    # Find columns that appear in multiple tables
    for col_lower, occurrences in all_columns.items():
        if len(occurrences) > 1:
            # Create relationships between tables sharing this column
            for i in range(len(occurrences)):
                for j in range(i + 1, len(occurrences)):
                    table1, col1 = occurrences[i]
                    table2, col2 = occurrences[j]
                    
                    # Determine confidence based on column name
                    if 'id' in col_lower or 'key' in col_lower:
                        confidence = 0.8
                    elif col_lower.endswith('_id'):
                        confidence = 0.85
                    else:
                        confidence = 0.6
                    
                    # Avoid duplicate relationships
                    existing = any(
                        (r['from_table'] == table1 and r['to_table'] == table2 and 
                         r['from_column'].lower() == col1.lower() and r['to_column'].lower() == col2.lower()) or
                        (r['from_table'] == table2 and r['to_table'] == table1 and 
                         r['from_column'].lower() == col2.lower() and r['to_column'].lower() == col1.lower())
                        for r in relationships
                    )
                    
                    if not existing:
                        relationships.append({
                            'from_table': table1,
                            'from_column': col1,
                            'to_table': table2,
                            'to_column': col2,
                            'confidence': confidence
                        })
    
    # Sort by confidence (highest first)
    relationships.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Remove duplicate relationships (keep highest confidence)
    seen = set()
    unique_relationships = []
    for rel in relationships:
        # Create a normalized key for the relationship
        key = tuple(sorted([
            (rel['from_table'], rel['from_column']),
            (rel['to_table'], rel['to_column'])
        ]))
        
        if key not in seen:
            seen.add(key)
            unique_relationships.append(rel)
    
    return unique_relationships


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


def _build_join_graph(relationships: List[Dict], table_names: List[str]) -> Dict:
    """
    Build a graph of table relationships for join ordering.
    
    Args:
        relationships: List of relationship dictionaries
        table_names: List of tables to include
        
    Returns:
        Dictionary mapping table pairs to their relationship info
    """
    graph = {}
    for rel in relationships:
        if rel['from_table'] in table_names and rel['to_table'] in table_names:
            key = (rel['from_table'], rel['to_table'])
            if key not in graph or rel['confidence'] > graph[key]['confidence']:
                graph[key] = rel
            
            # Add reverse direction
            rev_key = (rel['to_table'], rel['from_table'])
            if rev_key not in graph or rel['confidence'] > graph[rev_key]['confidence']:
                graph[rev_key] = {
                    'from_table': rel['to_table'],
                    'from_column': rel['to_column'],
                    'to_table': rel['from_table'],
                    'to_column': rel['from_column'],
                    'confidence': rel['confidence']
                }
    
    return graph


def generate_join_sql(
    db_manager,
    table_names: List[str],
    join_type: str = 'INNER',
    relationships: Optional[List[Dict]] = None
) -> str:
    """
    Generate a SQL query that joins multiple tables using inferred relationships.
    
    Args:
        db_manager: DatabaseManager instance with loaded tables
        table_names: List of table names to join
        join_type: Type of join ('INNER', 'LEFT', 'RIGHT', 'FULL')
        relationships: Optional pre-computed relationships. If None, will be inferred.
        
    Returns:
        SQL query string
        
    Raises:
        ValueError: If fewer than 2 tables or no relationships can be inferred
    """
    # Validate inputs
    if len(table_names) < 2:
        raise ValueError("At least two tables are required for join operations")
    
    # Normalize join type
    join_type = join_type.upper().strip()
    valid_join_types = {'INNER', 'LEFT', 'RIGHT', 'FULL', 'LEFT OUTER', 'RIGHT OUTER', 'FULL OUTER'}
    if join_type not in valid_join_types:
        raise ValueError(f"Invalid join type '{join_type}'. Must be one of: {valid_join_types}")
    
    # Add JOIN suffix if needed
    if join_type in {'LEFT', 'RIGHT', 'FULL'}:
        join_keyword = f"{join_type} JOIN"
    elif 'OUTER' in join_type:
        join_keyword = f"{join_type} JOIN"
    else:
        join_keyword = f"{join_type} JOIN"
    
    # Infer relationships if not provided
    if relationships is None:
        relationships = infer_table_relationships(db_manager, table_names)
    
    if not relationships:
        raise ValueError("No relationships could be inferred between the specified tables. "
                        "Tables must have common columns or follow naming conventions (e.g., table_id -> table.id).")
    
    # Build join graph
    join_graph = _build_join_graph(relationships, table_names)
    
    if not join_graph:
        raise ValueError("No relationships found between the specified tables.")
    
    # Start with the first table
    first_table = table_names[0]
    joined_tables = {first_table}
    join_clauses = []
    
    # Greedily add tables using available relationships
    remaining_tables = set(table_names[1:])
    
    while remaining_tables:
        best_join = None
        best_confidence = -1
        
        # Find the best relationship from joined tables to remaining tables
        for joined_table in joined_tables:
            for remaining_table in remaining_tables:
                key = (joined_table, remaining_table)
                if key in join_graph:
                    rel = join_graph[key]
                    if rel['confidence'] > best_confidence:
                        best_confidence = rel['confidence']
                        best_join = (joined_table, remaining_table, rel)
        
        if best_join is None:
            # No direct relationship found - tables are not connected
            # Use CROSS JOIN for remaining tables or raise error
            remaining_table = remaining_tables.pop()
            qualified_remaining = _get_qualified_table_name(db_manager, remaining_table)
            join_clauses.append(f"CROSS JOIN {qualified_remaining}")
            joined_tables.add(remaining_table)
        else:
            joined_table, remaining_table, rel = best_join
            remaining_tables.remove(remaining_table)
            joined_tables.add(remaining_table)
            
            qualified_remaining = _get_qualified_table_name(db_manager, remaining_table)
            qualified_joined = _get_qualified_table_name(db_manager, joined_table)
            
            # Build the ON clause
            on_clause = f'{qualified_joined}."{rel["from_column"]}" = {qualified_remaining}."{rel["to_column"]}"'
            join_clauses.append(f"{join_keyword} {qualified_remaining} ON {on_clause}")
    
    # Build SELECT clause - get all columns from all tables with table prefixes
    select_columns = []
    for table_name in table_names:
        if table_name in db_manager.table_columns:
            columns = db_manager.table_columns[table_name]
            qualified_name = _get_qualified_table_name(db_manager, table_name)
            for col in columns:
                select_columns.append(f'{qualified_name}."{col}" AS "{table_name}_{col}"')
    
    # If no columns found, use SELECT *
    if select_columns:
        select_clause = ', '.join(select_columns)
    else:
        select_clause = '*'
    
    # Build the final query
    first_qualified = _get_qualified_table_name(db_manager, first_table)
    sql = f"SELECT {select_clause}\nFROM {first_qualified}"
    
    if join_clauses:
        sql += "\n" + "\n".join(join_clauses)
    
    return sql


def get_available_join_types() -> List[dict]:
    """
    Get a list of available join types with their descriptions.
    
    Returns:
        List of dictionaries with 'name', 'sql', and 'description' keys
    """
    return [
        {
            'name': 'Inner Join',
            'sql': 'INNER',
            'description': 'Only rows that match in all tables'
        },
        {
            'name': 'Left Join',
            'sql': 'LEFT',
            'description': 'All rows from first table, matching rows from others'
        },
        {
            'name': 'Right Join',
            'sql': 'RIGHT',
            'description': 'All rows from last table, matching rows from others'
        },
        {
            'name': 'Full Outer Join',
            'sql': 'FULL',
            'description': 'All rows from all tables (with NULLs for non-matches)'
        }
    ]
