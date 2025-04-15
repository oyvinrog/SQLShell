"""
Context-aware SQL suggestions for SQLShell.

This module provides advanced context-based suggestion capabilities
for the SQL editor, providing intelligent and relevant completions
based on the current query context, schema information, and query history.
"""

import re
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional, Any


class ContextSuggester:
    """
    Provides context-aware SQL suggestions based on schema information,
    query context analysis, and usage patterns.
    """
    
    def __init__(self):
        # Schema information
        self.tables = set()  # Set of table names
        self.table_columns = defaultdict(list)  # {table_name: [column_names]}
        self.column_types = {}  # {table.column: data_type} or {column: data_type}
        
        # Detected relationships between tables for JOIN suggestions
        self.relationships = []  # [(table1, column1, table2, column2)]
        
        # Usage statistics for prioritizing suggestions
        self.usage_counts = Counter()  # {completion_term: count}
        
        # Query pattern detection
        self.common_patterns = []
        
        # Context cache to avoid recomputing
        self._context_cache = {}
        self._last_analyzed_text = ""
        
        # Query history
        self.query_history = []  # List of recent queries for pattern detection
        
        # Initialize with common SQL elements
        self._initialize_sql_keywords()
    
    def _initialize_sql_keywords(self) -> None:
        """Initialize common SQL keywords by category"""
        self.sql_keywords = {
            'basic': [
                'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING',
                'LIMIT', 'OFFSET', 'INSERT INTO', 'VALUES', 'UPDATE', 'SET',
                'DELETE FROM', 'CREATE TABLE', 'DROP TABLE', 'ALTER TABLE',
                'ADD COLUMN', 'DROP COLUMN', 'RENAME TO', 'UNION', 'UNION ALL',
                'INTERSECT', 'EXCEPT', 'AS', 'WITH', 'DISTINCT', 'CASE', 'WHEN',
                'THEN', 'ELSE', 'END', 'AND', 'OR', 'NOT', 'LIKE', 'IN', 'BETWEEN',
                'IS NULL', 'IS NOT NULL', 'ALL', 'ANY', 'EXISTS'
            ],
            'aggregation': [
                'AVG(', 'COUNT(', 'COUNT(*)', 'COUNT(DISTINCT ', 'SUM(', 'MIN(', 'MAX(',
                'MEDIAN(', 'PERCENTILE_CONT(', 'PERCENTILE_DISC(', 'VARIANCE(', 'STDDEV(',
                'FIRST(', 'LAST(', 'ARRAY_AGG(', 'STRING_AGG(', 'GROUP_CONCAT('
            ],
            'functions': [
                # String functions
                'LOWER(', 'UPPER(', 'INITCAP(', 'TRIM(', 'LTRIM(', 'RTRIM(', 'SUBSTRING(',
                'SUBSTR(', 'REPLACE(', 'POSITION(', 'CONCAT(', 'LENGTH(', 'CHAR_LENGTH(',
                'LEFT(', 'RIGHT(', 'REGEXP_REPLACE(', 'REGEXP_EXTRACT(', 'REGEXP_MATCH(',
                'FORMAT(', 'LPAD(', 'RPAD(', 'REVERSE(', 'SPLIT_PART(',
                
                # Numeric functions
                'ABS(', 'SIGN(', 'ROUND(', 'CEIL(', 'FLOOR(', 'TRUNC(', 'MOD(',
                'POWER(', 'SQRT(', 'CBRT(', 'LOG(', 'LOG10(', 'EXP(', 'RANDOM(',
                
                # Date/time functions
                'CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'NOW()',
                'DATE(', 'TIME(', 'DATETIME(', 'EXTRACT(', 'DATE_TRUNC(', 'DATE_PART(',
                'DATEADD(', 'DATEDIFF(', 'DATE_FORMAT(', 'STRFTIME(', 'MAKEDATE(',
                'YEAR(', 'QUARTER(', 'MONTH(', 'WEEK(', 'DAY(', 'HOUR(', 'MINUTE(', 'SECOND(',
                
                # Conditional functions
                'CASE', 'COALESCE(', 'NULLIF(', 'GREATEST(', 'LEAST(', 'IFF(', 'IFNULL(',
                'DECODE(', 'NVL(', 'NVL2(',
                
                # Type conversion
                'CAST(', 'CONVERT(', 'TRY_CAST(', 'TO_CHAR(', 'TO_DATE(', 'TO_NUMBER(',
                'TO_TIMESTAMP(', 'PARSE_JSON(',
                
                # Window functions
                'ROW_NUMBER() OVER (', 'RANK() OVER (', 'DENSE_RANK() OVER (',
                'LEAD(', 'LAG(', 'FIRST_VALUE(', 'LAST_VALUE(', 'NTH_VALUE('
            ],
            'table_ops': [
                'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'INSERT', 'UPDATE', 'DELETE',
                'MERGE', 'COPY', 'GRANT', 'REVOKE', 'INDEX', 'PRIMARY KEY', 'FOREIGN KEY',
                'REFERENCES', 'UNIQUE', 'NOT NULL', 'CHECK', 'DEFAULT'
            ],
            'join': [
                'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'CROSS JOIN',
                'NATURAL JOIN', 'LEFT OUTER JOIN', 'RIGHT OUTER JOIN', 'FULL OUTER JOIN'
            ]
        }
        
        # Create a flattened list of all keywords for easy lookup
        self.all_keywords = []
        for category, keywords in self.sql_keywords.items():
            self.all_keywords.extend(keywords)
    
    def update_schema(self, tables: Set[str], table_columns: Dict[str, List[str]], 
                     column_types: Dict[str, str] = None) -> None:
        """
        Update schema information for suggestions.
        
        Args:
            tables: Set of table names
            table_columns: Dictionary mapping table names to column lists
            column_types: Optional dictionary of column data types
        """
        self.tables = tables
        self.table_columns = table_columns
        
        if column_types:
            self.column_types = column_types
        
        # Clear context cache since schema has changed
        self._context_cache = {}
        
        # Detect relationships between tables
        self._detect_relationships()
    
    def _detect_relationships(self) -> None:
        """Detect potential relationships between tables based on column naming patterns"""
        self.relationships = []
        
        # For each table and its columns
        for table, columns in self.table_columns.items():
            for col in columns:
                # Check for foreign key naming pattern (table_id, tableId)
                if col.lower().endswith('_id') or (col.lower().endswith('id') and len(col) > 2):
                    # Extract potential referenced table name
                    if col.lower().endswith('_id'):
                        ref_table = col[:-3]  # Remove '_id'
                    else:
                        # Extract from camelCase/PascalCase
                        ref_table = col[:-2]  # Remove 'Id'
                    
                    # Normalize and check if this table exists
                    ref_table_lower = ref_table.lower()
                    for other_table in self.tables:
                        other_lower = other_table.lower()
                        if other_lower == ref_table_lower or other_lower.endswith(f"_{ref_table_lower}"):
                            # Found a potential relationship - check for id column
                            if 'id' in self.table_columns[other_table]:
                                self.relationships.append((table, col, other_table, 'id'))
                            else:
                                # Look for any primary key column
                                for other_col in self.table_columns[other_table]:
                                    if other_col.lower() == 'id' or other_col.lower().endswith('_id'):
                                        self.relationships.append((table, col, other_table, other_col))
                                        break
                
                # Also check for columns with the same name across tables
                for other_table, other_columns in self.table_columns.items():
                    if other_table != table and col in other_columns:
                        self.relationships.append((table, col, other_table, col))
    
    def record_query(self, query: str) -> None:
        """
        Record a query to improve suggestion relevance.
        
        Args:
            query: SQL query to record
        """
        if not query.strip():
            return
            
        # Add to query history (limit size)
        self.query_history.append(query)
        if len(self.query_history) > 100:
            self.query_history.pop(0)
        
        # Update usage statistics
        self._update_usage_stats(query)
        
        # Extract common patterns
        self._extract_patterns(query)
    
    def _update_usage_stats(self, query: str) -> None:
        """Update usage statistics by analyzing the query"""
        # Extract tables
        tables = self._extract_tables_from_query(query)
        for table in tables:
            if table in self.tables:
                self.usage_counts[table] += 1
        
        # Extract columns (with and without table prefix)
        columns = self._extract_columns_from_query(query)
        for col in columns:
            self.usage_counts[col] += 1
        
        # Extract SQL keywords
        keywords = re.findall(r'\b([A-Z_]{2,})\b', query.upper())
        for kw in keywords:
            if kw in self.all_keywords:
                self.usage_counts[kw] += 1
        
        # Extract common patterns (like "GROUP BY")
        patterns = [
            r'(SELECT\s+.*?\s+FROM)',
            r'(GROUP\s+BY\s+.*?(?:HAVING|ORDER|LIMIT|$))',
            r'(ORDER\s+BY\s+.*?(?:LIMIT|$))',
            r'(INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+JOIN).*?ON\s+.*?=\s+.*?(?:WHERE|JOIN|GROUP|ORDER|LIMIT|$)',
            r'(INSERT\s+INTO\s+.*?\s+VALUES)',
            r'(UPDATE\s+.*?\s+SET\s+.*?\s+WHERE)',
            r'(DELETE\s+FROM\s+.*?\s+WHERE)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Normalize pattern by removing extra whitespace and converting to uppercase
                normalized = re.sub(r'\s+', ' ', match).strip().upper()
                if len(normalized) < 50:  # Only track reasonably sized patterns
                    self.usage_counts[normalized] += 1
    
    def _extract_tables_from_query(self, query: str) -> List[str]:
        """Extract table names from a SQL query"""
        tables = []
        
        # Look for tables after FROM and JOIN
        from_matches = re.findall(r'FROM\s+([a-zA-Z0-9_]+)', query, re.IGNORECASE)
        join_matches = re.findall(r'JOIN\s+([a-zA-Z0-9_]+)', query, re.IGNORECASE)
        
        tables.extend(from_matches)
        tables.extend(join_matches)
        
        # Look for tables in UPDATE and INSERT statements
        update_matches = re.findall(r'UPDATE\s+([a-zA-Z0-9_]+)', query, re.IGNORECASE)
        insert_matches = re.findall(r'INSERT\s+INTO\s+([a-zA-Z0-9_]+)', query, re.IGNORECASE)
        
        tables.extend(update_matches)
        tables.extend(insert_matches)
        
        return tables
    
    def _extract_columns_from_query(self, query: str) -> List[str]:
        """Extract column names from a SQL query"""
        columns = []
        
        # Extract qualified column names (table.column)
        qual_columns = re.findall(r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)', query)
        for table, column in qual_columns:
            columns.append(f"{table}.{column}")
            columns.append(column)
        
        # Other patterns would need more complex parsing which is beyond the scope
        return columns
    
    def _extract_patterns(self, query: str) -> None:
        """Extract common query patterns for future suggestions"""
        # This would require a more sophisticated SQL parser to be accurate
        # Placeholder for future pattern extraction logic
        pass
    
    def analyze_context(self, text_before_cursor: str, current_word: str) -> Dict[str, Any]:
        """
        Analyze the SQL context at the current cursor position.
        
        Args:
            text_before_cursor: Text from the start of the document to the cursor
            current_word: The current word being typed
            
        Returns:
            Dictionary with context information
        """
        # Use cached context if analyzing the same text
        cache_key = f"{text_before_cursor}:{current_word}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]
        
        # Convert to uppercase for easier keyword matching
        text_upper = text_before_cursor.upper()
        
        # Initialize context dictionary
        context = {
            'type': 'unknown',
            'table_prefix': None,
            'after_from': False,
            'after_join': False,
            'after_select': False,
            'after_where': False,
            'after_group_by': False,
            'after_order_by': False,
            'after_having': False,
            'in_function_args': False,
            'columns_already_selected': [],
            'tables_in_from': [],
            'last_token': '',
            'current_word': current_word,
            'current_function': None,
        }
        
        # Extract tables from the query for context-aware suggestions
        # Look for tables after FROM and JOIN
        from_matches = re.findall(r'FROM\s+([a-zA-Z0-9_]+)', text_upper)
        join_matches = re.findall(r'JOIN\s+([a-zA-Z0-9_]+)', text_upper)
        
        # Add all found tables to context
        if from_matches or join_matches:
            tables = []
            tables.extend(from_matches)
            tables.extend(join_matches)
            context['tables_in_from'] = tables
        
        # Check for table.column context
        if '.' in current_word:
            parts = current_word.split('.')
            if len(parts) == 2:
                context['type'] = 'column'
                context['table_prefix'] = parts[0]
        
        # Extract the last few keywords to determine context
        keywords = re.findall(r'\b([A-Z_]+)\b', text_upper)
        last_keywords = keywords[-5:] if keywords else []
        last_keyword = last_keywords[-1] if last_keywords else ""
        context['last_token'] = last_keyword
        
        # Check for function context - match the last opening parenthesis
        if '(' in text_before_cursor:
            # Count parentheses to check if we're inside function arguments
            open_parens = text_before_cursor.count('(')
            close_parens = text_before_cursor.count(')')
            
            if open_parens > close_parens:
                context['type'] = 'function_arg'
                context['in_function_args'] = True
                
                # Find the last open parenthesis position
                last_open_paren_pos = text_before_cursor.rindex('(')
                
                # Extract text before the parenthesis to identify the function
                func_text = text_before_cursor[:last_open_paren_pos].strip()
                # Get the last word which should be the function name
                func_words = re.findall(r'\b([A-Za-z0-9_]+)\b', func_text)
                if func_words:
                    context['current_function'] = func_words[-1].upper()
                    context['last_token'] = context['current_function']
        
        # Extract the last line or statement
        last_line = text_before_cursor.split('\n')[-1].strip().upper()
        
        # Check for specific contexts
        
        # FROM/JOIN context - likely to be followed by table names
        if 'FROM' in last_keywords and not any(k in last_keywords[last_keywords.index('FROM'):] for k in ['WHERE', 'GROUP', 'HAVING', 'ORDER']):
            context['type'] = 'table'
            context['after_from'] = True
        
        elif any(k.endswith('JOIN') for k in last_keywords):
            context['type'] = 'table'
            context['after_join'] = True
        
        # WHERE/AND/OR context - likely to be followed by columns or expressions
        elif any(kw in last_keywords for kw in ['WHERE', 'AND', 'OR']):
            context['type'] = 'column_or_expression'
            context['after_where'] = True
        
        # SELECT context - likely to be followed by columns
        elif 'SELECT' in last_keywords and not any(k in last_keywords[last_keywords.index('SELECT'):] for k in ['FROM', 'WHERE']):
            context['type'] = 'column'
            context['after_select'] = True
            # Try to extract columns already in SELECT clause
            select_text = text_before_cursor[text_before_cursor.upper().find('SELECT'):]
            if 'FROM' in select_text.upper():
                select_text = select_text[:select_text.upper().find('FROM')]
            context['columns_already_selected'] = [c.strip() for c in select_text.split(',')[1:]]
            
        # GROUP BY context
        elif 'GROUP' in last_keywords or ('BY' in last_keywords and len(last_keywords) >= 2 and last_keywords[-2:] == ['GROUP', 'BY']):
            context['type'] = 'column'
            context['after_group_by'] = True
        
        # ORDER BY context
        elif 'ORDER' in last_keywords or ('BY' in last_keywords and len(last_keywords) >= 2 and last_keywords[-2:] == ['ORDER', 'BY']):
            context['type'] = 'column'
            context['after_order_by'] = True
        
        # HAVING context
        elif 'HAVING' in last_keywords:
            context['type'] = 'aggregation'
            context['after_having'] = True
        
        # Cache the context
        self._context_cache[cache_key] = context
        return context
    
    def get_suggestions(self, text_before_cursor: str, current_word: str) -> List[str]:
        """
        Get context-aware SQL suggestions.
        
        Args:
            text_before_cursor: Text from start of document to cursor position
            current_word: The current word being typed (possibly empty)
            
        Returns:
            List of suggestion strings relevant to the current context
        """
        # Get detailed context
        context = self.analyze_context(text_before_cursor, current_word)
        
        # Start with an empty suggestion list
        suggestions = []
        
        # Different suggestion strategies based on context type
        if context['type'] == 'table':
            suggestions = self._get_table_suggestions(context)
        elif context['type'] == 'column' and context['table_prefix']:
            suggestions = self._get_column_suggestions_for_table(context['table_prefix'])
        elif context['type'] == 'column' or context['type'] == 'column_or_expression':
            suggestions = self._get_column_suggestions(context)
        elif context['type'] == 'function_arg':
            suggestions = self._get_function_arg_suggestions(context)
        elif context['type'] == 'aggregation':
            suggestions = self._get_aggregation_suggestions(context)
        else:
            # Default case - general SQL keywords
            suggestions = self._get_default_suggestions()
        
        # Filter by current word if needed
        if current_word:
            suggestions = [s for s in suggestions if s.lower().startswith(current_word.lower())]
        
        # Prioritize by usage frequency
        return self._prioritize_suggestions(suggestions, context)
    
    def _get_table_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """Get table name suggestions"""
        suggestions = list(self.tables)
        
        # Add table aliases if relevant
        aliases = [f"{t} AS {t[0]}" for t in self.tables]
        suggestions.extend(aliases)
        
        # Add keywords that might follow FROM/JOIN
        if context['after_from'] or context['after_join']:
            suggestions.extend(self.sql_keywords['join'])
            
            # If we have previous tables, suggest relationships
            if context['tables_in_from'] and self.relationships:
                prev_tables = context['tables_in_from']
                for prev_table in prev_tables:
                    for t1, c1, t2, c2 in self.relationships:
                        if t1 == prev_table:
                            join_suggestion = f"{t2} ON {t2}.{c2} = {t1}.{c1}"
                            suggestions.append(join_suggestion)
                        elif t2 == prev_table:
                            join_suggestion = f"{t1} ON {t1}.{c1} = {t2}.{c2}"
                            suggestions.append(join_suggestion)
        
        return suggestions
    
    def _get_column_suggestions_for_table(self, table_prefix: str) -> List[str]:
        """Get column suggestions for a specific table"""
        if table_prefix in self.table_columns:
            return self.table_columns[table_prefix]
        return []
    
    def _get_column_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """Get column name suggestions"""
        suggestions = []
        
        # Add SQL functions and keywords for columns
        suggestions.extend(self.sql_keywords['aggregation'])
        suggestions.extend(self.sql_keywords['functions'])
        
        # Identify active tables in the current query
        active_tables = set()
        # First check tables extracted from FROM/JOIN clauses
        if 'tables_in_from' in context and context['tables_in_from']:
            active_tables.update(context['tables_in_from'])
        
        # Define column lists by priority
        active_table_columns = []
        other_columns = []
        
        # Get columns from active tables first
        for table in active_tables:
            if table in self.table_columns:
                columns = self.table_columns[table]
                # Add both plain column names and qualified ones
                active_table_columns.extend(columns)
                active_table_columns.extend([f"{table}.{col}" for col in columns])
        
        # Then get all other columns as fallback
        for table, columns in self.table_columns.items():
            if table not in active_tables:
                other_columns.extend(columns)
                # Only add qualified names if we have multiple tables to avoid confusion
                if len(self.table_columns) > 1:
                    other_columns.extend([f"{table}.{col}" for col in columns])
        
        # Add * and table.* suggestions
        suggestions.append("*")
        for table in self.tables:
            suggestions.append(f"{table}.*")
        
        # Context-specific additions
        if context['after_select']:
            # Add common SELECT patterns
            suggestions.append("DISTINCT ")
            # Avoid suggesting columns already in the select list
            already_selected = [col.split(' ')[0].split('.')[0] for col in context['columns_already_selected']]
            for col in already_selected:
                if col in suggestions:
                    suggestions.remove(col)
        
        elif context['after_where']:
            # Add comparison operators for WHERE clause
            operators = ["=", ">", "<", ">=", "<=", "<>", "!=", "LIKE", "IN", "BETWEEN", "IS NULL", "IS NOT NULL"]
            suggestions.extend(operators)
        
        # Add columns with priority ordering
        suggestions.extend(active_table_columns)
        suggestions.extend(other_columns)
        
        # Remove duplicates while preserving order
        seen = set()
        filtered_suggestions = []
        for item in suggestions:
            if item not in seen:
                seen.add(item)
                filtered_suggestions.append(item)
        
        return filtered_suggestions
    
    def _get_function_arg_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """Get suggestions for function arguments"""
        suggestions = []
        
        # Identify active tables in the current query
        active_tables = set()
        # First check tables extracted from FROM/JOIN clauses
        if 'tables_in_from' in context and context['tables_in_from']:
            active_tables.update(context['tables_in_from'])
        
        # Add column names as function arguments, prioritizing columns from active tables
        active_table_columns = []
        other_columns = []
        
        # First get columns from active tables
        for table in active_tables:
            if table in self.table_columns:
                columns = self.table_columns[table]
                # Add both plain column names and qualified ones
                active_table_columns.extend(columns)
                active_table_columns.extend([f"{table}.{col}" for col in columns])
        
        # Then get all other columns as fallback
        for table, columns in self.table_columns.items():
            if table not in active_tables:
                other_columns.extend(columns)
                # Only add qualified names if we have multiple tables to avoid confusion
                if len(self.table_columns) > 1:
                    other_columns.extend([f"{table}.{col}" for col in columns])
        
        # Add context-specific suggestions based on the last token
        last_token = context['last_token']
        
        if last_token in ['AVG', 'SUM', 'MIN', 'MAX', 'COUNT']:
            # For aggregate functions, prioritize numeric columns
            numeric_columns = []
            
            # First check active tables for numeric columns
            for table in active_tables:
                if table in self.table_columns:
                    for col in self.table_columns[table]:
                        qualified_name = f"{table}.{col}"
                        # Check if column type info is available
                        if qualified_name in self.column_types:
                            data_type = self.column_types[qualified_name].upper()
                            if any(t in data_type for t in ['INT', 'NUM', 'FLOAT', 'DOUBLE', 'DECIMAL']):
                                numeric_columns.append(qualified_name)
                                numeric_columns.append(col)
            
            # If no numeric columns found in active tables, check all columns
            if not numeric_columns:
                for col_name, data_type in self.column_types.items():
                    if data_type and any(t in data_type.upper() for t in ['INT', 'NUM', 'FLOAT', 'DOUBLE', 'DECIMAL']):
                        numeric_columns.append(col_name)
            
            # Build final suggestion list with priority order:
            # 1. Numeric columns from active tables
            # 2. All columns from active tables
            # 3. Numeric columns from other tables
            # 4. All other columns
            suggestions = numeric_columns + active_table_columns + other_columns
            
        elif last_token in ['SUBSTRING', 'LOWER', 'UPPER', 'TRIM', 'REPLACE', 'CONCAT']:
            # For string functions, prioritize text columns
            text_columns = []
            
            # First check active tables for text columns
            for table in active_tables:
                if table in self.table_columns:
                    for col in self.table_columns[table]:
                        qualified_name = f"{table}.{col}"
                        # Check if column type info is available
                        if qualified_name in self.column_types:
                            data_type = self.column_types[qualified_name].upper()
                            if any(t in data_type for t in ['CHAR', 'VARCHAR', 'TEXT', 'STRING']):
                                text_columns.append(qualified_name)
                                text_columns.append(col)
            
            # If no text columns found in active tables, check all columns
            if not text_columns:
                for col_name, data_type in self.column_types.items():
                    if data_type and any(t in data_type.upper() for t in ['CHAR', 'VARCHAR', 'TEXT', 'STRING']):
                        text_columns.append(col_name)
            
            suggestions = text_columns + active_table_columns + other_columns
            
        elif last_token in ['DATE', 'DATETIME', 'EXTRACT', 'DATEADD', 'DATEDIFF']:
            # For date functions, prioritize date columns
            date_columns = []
            
            # First check active tables for date columns
            for table in active_tables:
                if table in self.table_columns:
                    for col in self.table_columns[table]:
                        qualified_name = f"{table}.{col}"
                        # Check if column type info is available
                        if qualified_name in self.column_types:
                            data_type = self.column_types[qualified_name].upper()
                            if any(t in data_type for t in ['DATE', 'TIME', 'TIMESTAMP']):
                                date_columns.append(qualified_name)
                                date_columns.append(col)
            
            # If no date columns found in active tables, check all columns
            if not date_columns:
                for col_name, data_type in self.column_types.items():
                    if data_type and any(t in data_type.upper() for t in ['DATE', 'TIME', 'TIMESTAMP']):
                        date_columns.append(col_name)
            
            suggestions = date_columns + active_table_columns + other_columns
            
        else:
            # For other functions or generic cases, prioritize active table columns
            suggestions = active_table_columns + other_columns
        
        # Remove duplicates while preserving order
        seen = set()
        filtered_suggestions = []
        for item in suggestions:
            if item not in seen:
                seen.add(item)
                filtered_suggestions.append(item)
        
        return filtered_suggestions
    
    def _get_aggregation_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """Get suggestions for aggregation functions (HAVING clause)"""
        suggestions = []
        
        # Aggregation functions
        suggestions.extend(self.sql_keywords['aggregation'])
        
        # Common HAVING patterns
        having_patterns = [
            "COUNT(*) > ", 
            "COUNT(*) < ", 
            "COUNT(DISTINCT ", 
            "SUM(", 
            "AVG(", 
            "MIN(", 
            "MAX("
        ]
        suggestions.extend(having_patterns)
        
        return suggestions
    
    def _get_default_suggestions(self) -> List[str]:
        """Get default suggestions when no specific context is detected"""
        suggestions = []
        
        # Basic SQL keywords
        suggestions.extend(self.sql_keywords['basic'])
        
        # Common query starters
        query_starters = [
            "SELECT * FROM ",
            "SELECT COUNT(*) FROM ",
            "SELECT DISTINCT ",
            "INSERT INTO ",
            "UPDATE ",
            "DELETE FROM ",
            "CREATE TABLE ",
            "DROP TABLE ",
            "ALTER TABLE "
        ]
        suggestions.extend(query_starters)
        
        # Add most-used tables and columns
        top_used = [item for item, _ in self.usage_counts.most_common(10)]
        suggestions.extend(top_used)
        
        return suggestions
    
    def _prioritize_suggestions(self, suggestions: List[str], context: Dict[str, Any]) -> List[str]:
        """
        Prioritize suggestions based on relevance and usage statistics.
        
        Args:
            suggestions: List of initial suggestions
            context: Current SQL context
            
        Returns:
            Prioritized list of suggestions
        """
        # If there are no suggestions, return empty list
        if not suggestions:
            return []
        
        # Create a set for O(1) lookups and to remove duplicates
        suggestion_set = set(suggestions)
        
        # Start with a list of (suggestion, score) tuples
        scored_suggestions = []
        
        for suggestion in suggestion_set:
            # Base score from usage count (normalize to 0-10 range)
            count = self.usage_counts.get(suggestion, 0)
            max_count = max(self.usage_counts.values()) if self.usage_counts else 1
            usage_score = (count / max_count) * 10 if max_count > 0 else 0
            
            # Start with usage score
            score = usage_score
            
            # Boost for SQL keywords
            if suggestion.upper() in self.all_keywords:
                score += 5
            
            # Context-specific boosting
            if context['type'] == 'table' and suggestion in self.tables:
                score += 10
            elif context['type'] == 'column' and context['table_prefix']:
                if suggestion in self.table_columns.get(context['table_prefix'], []):
                    score += 15
            elif context['type'] == 'column' and any(suggestion in cols for cols in self.table_columns.values()):
                score += 8
            elif context['type'] == 'aggregation' and suggestion in self.sql_keywords['aggregation']:
                score += 12
            
            # Exact prefix match gives a big boost
            current_word = context['current_word']
            if current_word and suggestion.lower().startswith(current_word.lower()):
                # More boost for exact case match
                if suggestion.startswith(current_word):
                    score += 20
                else:
                    score += 15
            
            # Add to scored list
            scored_suggestions.append((suggestion, score))
        
        # Sort by score (descending) and return just the suggestions
        scored_suggestions.sort(key=lambda x: x[1], reverse=True)
        return [suggestion for suggestion, _ in scored_suggestions] 