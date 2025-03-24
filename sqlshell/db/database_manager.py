import os
import sqlite3
import pandas as pd
import duckdb

class DatabaseManager:
    """
    Manages database connections and operations for SQLShell.
    Handles both SQLite and DuckDB connections.
    """
    
    def __init__(self):
        """Initialize the database manager with no active connection."""
        self.conn = None
        self.connection_type = None
        self.loaded_tables = {}  # Maps table_name to file_path or 'database'/'query_result'
        self.table_columns = {}  # Maps table_name to list of column names
    
    def is_connected(self):
        """Check if there is an active database connection."""
        return self.conn is not None
    
    def get_connection_info(self):
        """Get information about the current connection."""
        if not self.is_connected():
            return "No database connected"
        
        if self.connection_type == "sqlite":
            return "Connected to: SQLite database"
        elif self.connection_type == "duckdb":
            return "Connected to: DuckDB database"
        return "Connected to: Unknown database type"
    
    def close_connection(self):
        """Close the current database connection if one exists."""
        if self.conn:
            try:
                if self.connection_type == "duckdb":
                    self.conn.close()
                else:  # sqlite
                    self.conn.close()
            except Exception:
                pass  # Ignore errors when closing
            finally:
                self.conn = None
                self.connection_type = None
    
    def open_database(self, filename):
        """
        Open a database connection to the specified file.
        Detects whether it's a SQLite or DuckDB database.
        
        Args:
            filename: Path to the database file
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            Exception: If there's an error opening the database
        """
        # Close any existing connection
        self.close_connection()
        
        try:
            if self.is_sqlite_db(filename):
                self.conn = sqlite3.connect(filename)
                self.connection_type = "sqlite"
            else:
                self.conn = duckdb.connect(filename)
                self.connection_type = "duckdb"
            
            # Load tables from the database
            self.load_database_tables()
            return True
        except (sqlite3.Error, duckdb.Error) as e:
            self.conn = None
            self.connection_type = None
            raise Exception(f"Failed to open database: {str(e)}")
    
    def create_memory_connection(self):
        """Create an in-memory DuckDB connection."""
        self.close_connection()
        self.conn = duckdb.connect(':memory:')
        self.connection_type = 'duckdb'
        return "Connected to: in-memory DuckDB"
    
    def is_sqlite_db(self, filename):
        """
        Check if the file is a SQLite database by examining its header.
        
        Args:
            filename: Path to the database file
            
        Returns:
            Boolean indicating if the file is a SQLite database
        """
        try:
            with open(filename, 'rb') as f:
                header = f.read(16)
                return header[:16] == b'SQLite format 3\x00'
        except:
            return False
    
    def load_database_tables(self):
        """
        Load all tables from the current database connection.
        
        Returns:
            A list of table names loaded
        """
        try:
            if not self.is_connected():
                return []
            
            table_names = []
            
            if self.connection_type == 'sqlite':
                query = "SELECT name FROM sqlite_master WHERE type='table'"
                cursor = self.conn.cursor()
                tables = cursor.execute(query).fetchall()
                
                for (table_name,) in tables:
                    self.loaded_tables[table_name] = 'database'
                    table_names.append(table_name)
                    
                    # Get column names for each table
                    try:
                        column_query = f"PRAGMA table_info({table_name})"
                        columns = cursor.execute(column_query).fetchall()
                        self.table_columns[table_name] = [col[1] for col in columns]  # Column name is at index 1
                    except Exception:
                        self.table_columns[table_name] = []
            
            else:  # duckdb
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
                result = self.conn.execute(query).fetchdf()
                
                for table_name in result['table_name']:
                    self.loaded_tables[table_name] = 'database'
                    table_names.append(table_name)
                    
                    # Get column names for each table
                    try:
                        column_query = f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}' AND table_schema='main'"
                        columns = self.conn.execute(column_query).fetchdf()
                        self.table_columns[table_name] = columns['column_name'].tolist()
                    except Exception:
                        self.table_columns[table_name] = []
            
            return table_names
            
        except Exception as e:
            raise Exception(f'Error loading tables: {str(e)}')
    
    def execute_query(self, query):
        """
        Execute a SQL query against the current database connection.
        
        Args:
            query: SQL query string to execute
            
        Returns:
            Pandas DataFrame with the query results
            
        Raises:
            Exception: If there's an error executing the query
        """
        if not query.strip():
            raise ValueError("Empty query")
        
        if not self.is_connected():
            raise ValueError("No database connection")
        
        try:
            if self.connection_type == "duckdb":
                result = self.conn.execute(query).fetchdf()
            else:  # sqlite
                result = pd.read_sql_query(query, self.conn)
            
            return result
        except (duckdb.Error, sqlite3.Error) as e:
            error_msg = str(e).lower()
            if "syntax error" in error_msg:
                raise SyntaxError(f"SQL syntax error: {str(e)}")
            elif "no such table" in error_msg:
                raise ValueError(f"Table not found: {str(e)}")
            elif "no such column" in error_msg:
                raise ValueError(f"Column not found: {str(e)}")
            else:
                raise Exception(f"Database error: {str(e)}")
    
    def load_file(self, file_path):
        """
        Load data from a file into the database.
        
        Args:
            file_path: Path to the data file (Excel, CSV, Parquet)
            
        Returns:
            Tuple of (table_name, DataFrame) for the loaded data
            
        Raises:
            ValueError: If the file format is unsupported or there's an error
        """
        try:
            # Read the file into a DataFrame
            if file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.parquet'):
                df = pd.read_parquet(file_path)
            else:
                raise ValueError("Unsupported file format")
            
            # Generate table name from file name
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            table_name = self.sanitize_table_name(base_name)
            
            # Ensure unique table name
            original_name = table_name
            counter = 1
            while table_name in self.loaded_tables:
                table_name = f"{original_name}_{counter}"
                counter += 1
            
            # Register the table in the database
            if not self.is_connected():
                self.create_memory_connection()
                
            # Handle table creation based on database type
            if self.connection_type == 'sqlite':
                # For SQLite, create a table from the DataFrame
                df.to_sql(table_name, self.conn, index=False, if_exists='replace')
            else:
                # For DuckDB, register the DataFrame as a view
                self.conn.register(table_name, df)
            
            # Store information about the table
            self.loaded_tables[table_name] = file_path
            self.table_columns[table_name] = df.columns.tolist()
            
            return table_name, df
            
        except Exception as e:
            raise ValueError(f"Error loading file: {str(e)}")
    
    def remove_table(self, table_name):
        """
        Remove a table from the database.
        
        Args:
            table_name: Name of the table to remove
            
        Returns:
            Boolean indicating success
        """
        if not table_name in self.loaded_tables:
            return False
        
        try:
            # Remove from database
            if self.connection_type == 'sqlite':
                self.conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            else:  # duckdb
                self.conn.execute(f'DROP VIEW IF EXISTS {table_name}')
            
            # Remove from tracking
            del self.loaded_tables[table_name]
            if table_name in self.table_columns:
                del self.table_columns[table_name]
            
            return True
        except Exception:
            return False
    
    def get_table_preview(self, table_name, limit=5):
        """
        Get a preview of the data in a table.
        
        Args:
            table_name: Name of the table to preview
            limit: Number of rows to preview
            
        Returns:
            Pandas DataFrame with the preview data
        """
        if not table_name in self.loaded_tables:
            raise ValueError(f"Table '{table_name}' not found")
        
        try:
            if self.connection_type == 'sqlite':
                return pd.read_sql_query(f'SELECT * FROM "{table_name}" LIMIT {limit}', self.conn)
            else:
                return self.conn.execute(f'SELECT * FROM {table_name} LIMIT {limit}').fetchdf()
        except Exception as e:
            raise Exception(f"Error previewing table: {str(e)}")
    
    def rename_table(self, old_name, new_name):
        """
        Rename a table in the database.
        
        Args:
            old_name: Current name of the table
            new_name: New name for the table
            
        Returns:
            Boolean indicating success
        """
        if not old_name in self.loaded_tables:
            return False
        
        try:
            # Sanitize the new name
            new_name = self.sanitize_table_name(new_name)
            
            # Check if new name already exists
            if new_name in self.loaded_tables and new_name != old_name:
                raise ValueError(f"Table '{new_name}' already exists")
                
            # Rename in database
            if self.connection_type == 'sqlite':
                self.conn.execute(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"')
            else:  # duckdb
                # For DuckDB, we need to:
                # 1. Get the data from the old view/table
                df = self.conn.execute(f'SELECT * FROM {old_name}').fetchdf()
                # 2. Drop the old view
                self.conn.execute(f'DROP VIEW IF EXISTS {old_name}')
                # 3. Register the data under the new name
                self.conn.register(new_name, df)
            
            # Update tracking
            self.loaded_tables[new_name] = self.loaded_tables.pop(old_name)
            self.table_columns[new_name] = self.table_columns.pop(old_name)
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to rename table: {str(e)}")
    
    def sanitize_table_name(self, name):
        """
        Sanitize a table name to be valid in SQL.
        
        Args:
            name: The proposed table name
            
        Returns:
            A sanitized table name
        """
        import re
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Ensure it starts with a letter
        if not name or not name[0].isalpha():
            name = 'table_' + name
        return name.lower()
    
    def register_dataframe(self, df, table_name, source='query_result'):
        """
        Register a DataFrame as a table in the database.
        
        Args:
            df: Pandas DataFrame to register
            table_name: Name for the table
            source: Source of the data (for tracking)
            
        Returns:
            The table name used (may be different if there was a conflict)
        """
        # Sanitize and ensure unique name
        table_name = self.sanitize_table_name(table_name)
        original_name = table_name
        counter = 1
        while table_name in self.loaded_tables:
            table_name = f"{original_name}_{counter}"
            counter += 1
        
        # Register in database
        if self.connection_type == 'sqlite':
            df.to_sql(table_name, self.conn, index=False, if_exists='replace')
        else:  # duckdb
            self.conn.register(table_name, df)
        
        # Track the table
        self.loaded_tables[table_name] = source
        self.table_columns[table_name] = df.columns.tolist()
        
        return table_name
    
    def get_all_table_columns(self):
        """
        Get all table and column names for autocompletion.
        
        Returns:
            List of completion words (table names and column names)
        """
        completion_words = list(self.loaded_tables.keys())
        
        # Add column names with table name prefix (for joins)
        for table, columns in self.table_columns.items():
            completion_words.extend(columns)
            completion_words.extend([f"{table}.{col}" for col in columns])
            
        return completion_words 