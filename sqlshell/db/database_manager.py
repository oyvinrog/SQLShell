import os
import sqlite3
import pandas as pd
import duckdb
from pathlib import Path

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
        self.database_path = None  # Track the path to the current database file
    
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
                self.database_path = None  # Clear the database path
    
    def open_database(self, filename, load_all_tables=True):
        """
        Open a database connection to the specified file.
        Detects whether it's a SQLite or DuckDB database.
        
        Args:
            filename: Path to the database file
            load_all_tables: Whether to automatically load all tables from the database
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            Exception: If there's an error opening the database
        """
        # Close any existing connection
        self.close_connection()
        
        # Clear any existing loaded tables
        self.loaded_tables = {}
        self.table_columns = {}
        
        try:
            if self.is_sqlite_db(filename):
                self.conn = sqlite3.connect(filename)
                self.connection_type = "sqlite"
            else:
                self.conn = duckdb.connect(filename)
                self.connection_type = "duckdb"
            
            # Store the database path
            self.database_path = os.path.abspath(filename)
            
            # Load tables from the database if requested
            if load_all_tables:
                self.load_database_tables()
            return True
        except (sqlite3.Error, duckdb.Error) as e:
            self.conn = None
            self.connection_type = None
            self.database_path = None
            raise Exception(f"Failed to open database: {str(e)}")
    
    def create_memory_connection(self):
        """Create an in-memory DuckDB connection."""
        self.close_connection()
        self.conn = duckdb.connect(':memory:')
        self.connection_type = 'duckdb'
        self.database_path = None  # No file path for in-memory database
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
                # Extract the table name from the error message when possible
                import re
                table_match = re.search(r"'([^']+)'", str(e))
                table_name = table_match.group(1) if table_match else "unknown"
                
                # Check if this table is in our loaded_tables dict but came from a database
                if table_name in self.loaded_tables and self.loaded_tables[table_name] == 'database':
                    raise ValueError(f"Table '{table_name}' was part of a database but is not accessible. "
                                   f"Please reconnect to the original database using the 'Open Database' button.")
                else:
                    raise ValueError(f"Table not found: {str(e)}")
            elif "no such column" in error_msg:
                raise ValueError(f"Column not found: {str(e)}")
            else:
                raise Exception(f"Database error: {str(e)}")
    
    def load_file(self, file_path):
        """
        Load data from a file into the database.
        
        Args:
            file_path: Path to the data file (Excel, CSV, TXT, Parquet, Delta)
            
        Returns:
            Tuple of (table_name, DataFrame) for the loaded data
            
        Raises:
            ValueError: If the file format is unsupported or there's an error
        """
        try:
            # Check if this is a Delta table (folder with _delta_log)
            delta_path = Path(file_path)
            is_delta_table = (delta_path.is_dir() and 
                             (delta_path / '_delta_log').exists()) or file_path.endswith('.delta')
            
            # Read the file into a DataFrame, using optimized loading strategies
            if is_delta_table:
                # Read as Delta table using deltalake library
                try:
                    # Load the Delta table
                    import deltalake
                    delta_table = deltalake.DeltaTable(file_path)
                    
                    # Get the schema to identify decimal columns
                    schema = delta_table.schema()
                    decimal_columns = []
                    
                    # Identify decimal columns from schema
                    for field in schema.fields:
                        # Use string representation to check for decimal
                        if 'decimal' in str(field.type).lower():
                            decimal_columns.append(field.name)
                    
                    # Read the data
                    df = delta_table.to_pandas()
                    
                    # Try to convert decimal columns to float64, warn if not possible
                    for col in decimal_columns:
                        if col in df.columns:
                            try:
                                df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')
                                if df[col].isna().any():
                                    print(f"Warning: Some values in column '{col}' could not be converted to float64 and are set as NaN.")
                            except Exception as e:
                                print(f"Warning: Could not convert column '{col}' to float64: {e}")
                except Exception as e:
                    raise ValueError(f"Error loading Delta table: {str(e)}")
            elif file_path.endswith(('.xlsx', '.xls')):
                # Try to use a streaming approach for Excel files
                try:
                    # For Excel files, we first check if it's a large file
                    # If it's large, we may want to show only a subset
                    excel_file = pd.ExcelFile(file_path)
                    sheet_name = excel_file.sheet_names[0]  # Default to first sheet
                    
                    # Read the first row to get column names
                    df_preview = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=5)
                    
                    # If the file is very large, use chunksize
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
                    
                    if file_size > 50:  # If file is larger than 50MB
                        # Use a limited subset for large files to avoid memory issues
                        df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=100000)  # Cap at 100k rows
                    else:
                        # For smaller files, read everything
                        df = pd.read_excel(excel_file, sheet_name=sheet_name)
                except Exception:
                    # Fallback to standard reading method
                    df = pd.read_excel(file_path)
            elif file_path.endswith(('.csv', '.txt')):
                # For CSV and TXT files, detect separator and use chunking for large files
                try:
                    # Check if it's a large file
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
                    
                    # Try multiple encodings if needed
                    encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'ISO-8859-1']
                    
                    # Detect the separator automatically
                    def detect_separator(sample_data):
                        # Common separators to check
                        separators = [',', ';', '\t']
                        separator_scores = {}

                        # Split into lines and analyze
                        lines = [line.strip() for line in sample_data.split('\n') if line.strip()]
                        if not lines:
                            return ','  # Default if no content

                        # Check for quoted content with separators
                        has_quotes = '"' in sample_data or "'" in sample_data
                        
                        # If we have quoted content, use a different approach
                        if has_quotes:
                            for sep in separators:
                                # Look for patterns like "value";
                                pattern_count = 0
                                for line in lines:
                                    # Count occurrences of quote + separator
                                    double_quote_pattern = f'"{sep}'
                                    single_quote_pattern = f"'{sep}"
                                    pattern_count += line.count(double_quote_pattern) + line.count(single_quote_pattern)
                                
                                # If we found clear quote+separator patterns, this is likely our separator
                                if pattern_count > 0:
                                    separator_scores[sep] = pattern_count
                        
                        # Standard approach based on consistent column counts
                        if not separator_scores:
                            for sep in separators:
                                # Count consistent occurrences across lines
                                counts = [line.count(sep) for line in lines]
                                if counts and all(c > 0 for c in counts):
                                    # Calculate consistency score: higher if all counts are the same
                                    consistency = 1.0 if all(c == counts[0] for c in counts) else 0.5
                                    # Score is average count * consistency
                                    separator_scores[sep] = sum(counts) / len(counts) * consistency
                        
                        # Choose the separator with the highest score
                        if separator_scores:
                            return max(separator_scores.items(), key=lambda x: x[1])[0]
                        
                        # Default to comma if we couldn't determine
                        return ','
                    
                    # First, sample the file to detect separator
                    with open(file_path, 'rb') as f:
                        # Read first few KB to detect encoding and separator
                        raw_sample = f.read(4096)
                    
                    # Try to decode with various encodings
                    sample_text = None
                    detected_encoding = None
                    
                    for encoding in encodings_to_try:
                        try:
                            sample_text = raw_sample.decode(encoding)
                            detected_encoding = encoding
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    if not sample_text:
                        raise ValueError("Could not decode file with any of the attempted encodings")
                    
                    # Detect separator from the sample
                    separator = detect_separator(sample_text)
                    
                    # Determine quote character (default to double quote)
                    quotechar = '"'
                    if sample_text.count("'") > sample_text.count('"'):
                        quotechar = "'"
                    
                    if file_size > 50:  # If file is larger than 50MB
                        # Read the first chunk to get column types
                        try:
                            df_preview = pd.read_csv(
                                file_path, 
                                sep=separator,
                                nrows=1000, 
                                encoding=detected_encoding,
                                engine='python' if separator != ',' else 'c',
                                quotechar=quotechar,
                                doublequote=True
                            )
                            
                            # Use optimized dtypes for better memory usage
                            dtypes = {col: df_preview[col].dtype for col in df_preview.columns}
                            
                            # Read again with chunk processing, combining up to 100k rows
                            chunks = []
                            for chunk in pd.read_csv(
                                file_path, 
                                sep=separator,
                                dtype=dtypes, 
                                chunksize=10000, 
                                encoding=detected_encoding,
                                engine='python' if separator != ',' else 'c',
                                quotechar=quotechar,
                                doublequote=True
                            ):
                                chunks.append(chunk)
                                if len(chunks) * 10000 >= 100000:  # Cap at 100k rows
                                    break
                            
                            df = pd.concat(chunks, ignore_index=True)
                        except pd.errors.ParserError as e:
                            # If parsing fails, try again with error recovery options
                            print(f"Initial parsing failed: {str(e)}. Trying with error recovery options...")
                            
                            # Try with Python engine which is more flexible
                            try:
                                # First try with pandas >= 1.3 parameters
                                df = pd.read_csv(
                                    file_path,
                                    sep=separator,
                                    encoding=detected_encoding,
                                    engine='python',  # Always use python engine for error recovery
                                    quotechar=quotechar,
                                    doublequote=True,
                                    on_bad_lines='warn',  # New parameter in pandas >= 1.3
                                    na_values=[''],
                                    keep_default_na=True
                                )
                            except TypeError:
                                # Fall back to pandas < 1.3 parameters
                                df = pd.read_csv(
                                    file_path,
                                    sep=separator,
                                    encoding=detected_encoding,
                                    engine='python',
                                    quotechar=quotechar,
                                    doublequote=True,
                                    error_bad_lines=False,  # Old parameter
                                    warn_bad_lines=True,    # Old parameter
                                    na_values=[''],
                                    keep_default_na=True
                                )
                    else:
                        # For smaller files, read everything at once
                        try:
                            df = pd.read_csv(
                                file_path, 
                                sep=separator,
                                encoding=detected_encoding,
                                engine='python' if separator != ',' else 'c',
                                quotechar=quotechar,
                                doublequote=True
                            )
                        except pd.errors.ParserError as e:
                            # If parsing fails, try again with error recovery options
                            print(f"Initial parsing failed: {str(e)}. Trying with error recovery options...")
                            
                            # Try with Python engine which is more flexible
                            try:
                                # First try with pandas >= 1.3 parameters
                                df = pd.read_csv(
                                    file_path,
                                    sep=separator,
                                    encoding=detected_encoding,
                                    engine='python',  # Always use python engine for error recovery
                                    quotechar=quotechar,
                                    doublequote=True,
                                    on_bad_lines='warn',  # New parameter in pandas >= 1.3
                                    na_values=[''],
                                    keep_default_na=True
                                )
                            except TypeError:
                                # Fall back to pandas < 1.3 parameters
                                df = pd.read_csv(
                                    file_path,
                                    sep=separator,
                                    encoding=detected_encoding,
                                    engine='python',
                                    quotechar=quotechar,
                                    doublequote=True,
                                    error_bad_lines=False,  # Old parameter
                                    warn_bad_lines=True,    # Old parameter
                                    na_values=[''],
                                    keep_default_na=True
                                )
                except Exception as e:
                    # Log the error for debugging
                    import traceback
                    print(f"Error loading CSV/TXT file: {str(e)}")
                    print(traceback.format_exc())
                    raise ValueError(f"Error loading CSV/TXT file: {str(e)}")
            elif file_path.endswith('.parquet'):
                df = pd.read_parquet(file_path)
            else:
                raise ValueError("Unsupported file format. Supported formats: .xlsx, .xls, .csv, .txt, .parquet, and Delta tables.")
            
            # Generate table name from file name
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # For directories like Delta tables, use the directory name
            if os.path.isdir(file_path):
                base_name = os.path.basename(file_path)
                
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
                # For large dataframes, use a chunked approach to avoid memory issues
                if len(df) > 10000:
                    # Create the table with the first chunk
                    df.iloc[:1000].to_sql(table_name, self.conn, index=False, if_exists='replace')
                    
                    # Append the rest in chunks
                    chunk_size = 5000
                    for i in range(1000, len(df), chunk_size):
                        end = min(i + chunk_size, len(df))
                        df.iloc[i:end].to_sql(table_name, self.conn, index=False, if_exists='append')
                else:
                    # For smaller dataframes, do it in one go
                    df.to_sql(table_name, self.conn, index=False, if_exists='replace')
            else:
                # For DuckDB, register the DataFrame as a view
                self.conn.register(table_name, df)
            
            # Store information about the table
            self.loaded_tables[table_name] = file_path
            self.table_columns[table_name] = df.columns.tolist()
            
            return table_name, df
            
        except MemoryError:
            raise ValueError("Not enough memory to load this file. Try using a smaller file or increasing available memory.")
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
    
    def reload_table(self, table_name):
        """
        Reload a table's data from its source file.
        
        Args:
            table_name: Name of the table to reload
            
        Returns:
            Tuple of (bool, message) indicating success/failure and a message
            
        Raises:
            ValueError: If the table cannot be reloaded
        """
        if not table_name in self.loaded_tables:
            return False, f"Table '{table_name}' not found"
        
        file_path = self.loaded_tables[table_name]
        
        # Check if this is a file-based table
        if file_path in ['database', 'query_result']:
            return False, f"Cannot reload '{table_name}' because it's not a file-based table"
        
        try:
            # Check if the file still exists
            if not os.path.exists(file_path):
                return False, f"Source file '{file_path}' no longer exists"
            
            # Store the original table name
            original_name = table_name
            
            # Remove the existing table
            self.remove_table(table_name)
            
            # Check if this is a Delta table
            delta_path = Path(file_path)
            is_delta_table = (delta_path.is_dir() and 
                             (delta_path / '_delta_log').exists()) or file_path.endswith('.delta')
            
            # Load the file with the original table name
            df = None
            if is_delta_table:
                # Read as Delta table
                import deltalake
                delta_table = deltalake.DeltaTable(file_path)
                df = delta_table.to_pandas()
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            elif file_path.endswith(('.csv', '.txt')):
                # Try multiple encodings for CSV/TXT files
                encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'ISO-8859-1']
                
                # Detect the separator automatically
                def detect_separator(sample_data):
                    # Common separators to check
                    separators = [',', ';', '\t']
                    separator_scores = {}

                    # Split into lines and analyze
                    lines = [line.strip() for line in sample_data.split('\n') if line.strip()]
                    if not lines:
                        return ','  # Default if no content

                    # Check for quoted content with separators
                    has_quotes = '"' in sample_data or "'" in sample_data
                    
                    # If we have quoted content, use a different approach
                    if has_quotes:
                        for sep in separators:
                            # Look for patterns like "value";
                            pattern_count = 0
                            for line in lines:
                                # Count occurrences of quote + separator
                                double_quote_pattern = f'"{sep}'
                                single_quote_pattern = f"'{sep}"
                                pattern_count += line.count(double_quote_pattern) + line.count(single_quote_pattern)
                            
                            # If we found clear quote+separator patterns, this is likely our separator
                            if pattern_count > 0:
                                separator_scores[sep] = pattern_count
                    
                    # Standard approach based on consistent column counts
                    if not separator_scores:
                        for sep in separators:
                            # Count consistent occurrences across lines
                            counts = [line.count(sep) for line in lines]
                            if counts and all(c > 0 for c in counts):
                                # Calculate consistency score: higher if all counts are the same
                                consistency = 1.0 if all(c == counts[0] for c in counts) else 0.5
                                # Score is average count * consistency
                                separator_scores[sep] = sum(counts) / len(counts) * consistency
                    
                    # Choose the separator with the highest score
                    if separator_scores:
                        return max(separator_scores.items(), key=lambda x: x[1])[0]
                    
                    # Default to comma if we couldn't determine
                    return ','
                
                # First, sample the file to detect separator and encoding
                with open(file_path, 'rb') as f:
                    # Read first few KB to detect encoding and separator
                    raw_sample = f.read(4096)
                
                # Try to decode with various encodings
                sample_text = None
                detected_encoding = None
                
                for encoding in encodings_to_try:
                    try:
                        sample_text = raw_sample.decode(encoding)
                        detected_encoding = encoding
                        break
                    except UnicodeDecodeError:
                        # If this encoding fails, try the next one
                        continue
                
                if not sample_text:
                    raise ValueError("Could not decode file with any of the attempted encodings")
                
                # Detect separator from the sample
                separator = detect_separator(sample_text)
                
                # Determine quote character (default to double quote)
                quotechar = '"'
                if sample_text.count("'") > sample_text.count('"'):
                    quotechar = "'"
                
                # Read with detected parameters
                try:
                    df = pd.read_csv(
                        file_path, 
                        sep=separator,
                        encoding=detected_encoding,
                        engine='python' if separator != ',' else 'c',
                        quotechar=quotechar,
                        doublequote=True
                    )
                except pd.errors.ParserError as e:
                    # If parsing fails, try again with error recovery options
                    print(f"Initial parsing failed on reload: {str(e)}. Trying with error recovery options...")
                    
                    # Try with Python engine which is more flexible
                    try:
                        # First try with pandas >= 1.3 parameters
                        df = pd.read_csv(
                            file_path,
                            sep=separator,
                            encoding=detected_encoding,
                            engine='python',  # Always use python engine for error recovery
                            quotechar=quotechar,
                            doublequote=True,
                            on_bad_lines='warn',  # New parameter in pandas >= 1.3
                            na_values=[''],
                            keep_default_na=True
                        )
                    except TypeError:
                        # Fall back to pandas < 1.3 parameters
                        df = pd.read_csv(
                            file_path,
                            sep=separator,
                            encoding=detected_encoding,
                            engine='python',
                            quotechar=quotechar,
                            doublequote=True,
                            error_bad_lines=False,  # Old parameter
                            warn_bad_lines=True,    # Old parameter
                            na_values=[''],
                            keep_default_na=True
                        )
            elif file_path.endswith('.parquet'):
                df = pd.read_parquet(file_path)
            else:
                return False, "Unsupported file format"
            
            # Register the dataframe with the original name
            self.register_dataframe(df, original_name, file_path)
            
            return True, f"Table '{table_name}' reloaded successfully"
            
        except Exception as e:
            return False, f"Error reloading table: {str(e)}"
    
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
            # Register the DataFrame directly
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
        # Start with table names
        completion_words = set(self.loaded_tables.keys())
        
        # Track column data types for smarter autocompletion
        column_data_types = {}  # {table.column: data_type}
        
        # Detect potential table relationships for JOIN suggestions
        potential_relationships = []  # [(table1, column1, table2, column2)]
        
        # Add column names with and without table prefixes, up to reasonable limits
        MAX_COLUMNS_PER_TABLE = 100  # Limit columns to prevent memory issues
        MAX_TABLES_WITH_COLUMNS = 20  # Limit the number of tables to process
        
        # Sort tables by name to ensure consistent behavior
        table_items = sorted(list(self.table_columns.items()))
        
        # Process only a limited number of tables
        for table, columns in table_items[:MAX_TABLES_WITH_COLUMNS]:
            # Add each column name by itself
            for col in columns[:MAX_COLUMNS_PER_TABLE]:
                completion_words.add(col)
            
            # Add qualified column names (table.column)
            for col in columns[:MAX_COLUMNS_PER_TABLE]:
                completion_words.add(f"{table}.{col}")
            
            # Try to infer table relationships based on column naming
            self._detect_relationships(table, columns, potential_relationships)
            
            # Try to infer column data types when possible
            if self.is_connected():
                try:
                    self._detect_column_types(table, column_data_types)
                except Exception:
                    pass
        
        # Add common SQL functions and aggregations with context-aware completions
        sql_functions = [
            # Aggregation functions with completed parentheses
            "COUNT(*)", "COUNT(DISTINCT ", "SUM(", "AVG(", "MIN(", "MAX(", 
            
            # String functions
            "CONCAT(", "SUBSTR(", "LOWER(", "UPPER(", "TRIM(", "REPLACE(", "LENGTH(", 
            "REGEXP_REPLACE(", "REGEXP_EXTRACT(", "REGEXP_MATCH(",
            
            # Date/time functions
            "CURRENT_DATE", "CURRENT_TIME", "CURRENT_TIMESTAMP", "NOW()", 
            "EXTRACT(", "DATE_TRUNC(", "DATE_PART(", "DATEADD(", "DATEDIFF(",
            
            # Type conversion
            "CAST( AS ", "CONVERT(", "TRY_CAST( AS ", "FORMAT(", 
            
            # Conditional functions
            "COALESCE(", "NULLIF(", "GREATEST(", "LEAST(", "IFF(", "IFNULL(",
            
            # Window functions
            "ROW_NUMBER() OVER (", "RANK() OVER (", "DENSE_RANK() OVER (",
            "LEAD( OVER (", "LAG( OVER (", "FIRST_VALUE( OVER (", "LAST_VALUE( OVER ("
        ]
        
        # Add common SQL patterns with context awareness
        sql_patterns = [
            # Basic query patterns
            "SELECT * FROM ", "SELECT COUNT(*) FROM ", 
            "SELECT DISTINCT ", "GROUP BY ", "ORDER BY ", "HAVING ",
            "LIMIT ", "OFFSET ", "WHERE ",
            
            # JOIN patterns - complete with ON and common join points
            "INNER JOIN ", "LEFT JOIN ", "RIGHT JOIN ", "FULL OUTER JOIN ",
            "LEFT OUTER JOIN ", "RIGHT OUTER JOIN ", "CROSS JOIN ",
            
            # Advanced patterns
            "WITH _ AS (", "CASE WHEN _ THEN _ ELSE _ END",
            "OVER (PARTITION BY _ ORDER BY _)",
            "EXISTS (SELECT 1 FROM _ WHERE _)",
            "NOT EXISTS (SELECT 1 FROM _ WHERE _)",
            
            # Common operator patterns
            "BETWEEN _ AND _", "IN (", "NOT IN (", "IS NULL", "IS NOT NULL",
            "LIKE '%_%'", "NOT LIKE ", "ILIKE ", 
            
            # Data manipulation patterns
            "INSERT INTO _ VALUES (", "INSERT INTO _ (_) VALUES (_)",
            "UPDATE _ SET _ = _ WHERE _", "DELETE FROM _ WHERE _"
        ]
        
        # Add table relationships as suggested JOIN patterns
        for table1, col1, table2, col2 in potential_relationships:
            join_pattern = f"JOIN {table2} ON {table1}.{col1} = {table2}.{col2}"
            completion_words.add(join_pattern)
            
            # Also add the reverse relationship
            join_pattern_rev = f"JOIN {table1} ON {table2}.{col2} = {table1}.{col1}"
            completion_words.add(join_pattern_rev)
        
        # Add all SQL extras to the completion words
        completion_words.update(sql_functions)
        completion_words.update(sql_patterns)
        
        # Add common data-specific comparison patterns based on column types
        for col_name, data_type in column_data_types.items():
            if 'INT' in data_type.upper() or 'NUM' in data_type.upper() or 'FLOAT' in data_type.upper():
                # Numeric columns
                completion_words.add(f"{col_name} > ")
                completion_words.add(f"{col_name} < ")
                completion_words.add(f"{col_name} >= ")
                completion_words.add(f"{col_name} <= ")
                completion_words.add(f"{col_name} BETWEEN ")
            elif 'DATE' in data_type.upper() or 'TIME' in data_type.upper():
                # Date/time columns
                completion_words.add(f"{col_name} > CURRENT_DATE")
                completion_words.add(f"{col_name} < CURRENT_DATE")
                completion_words.add(f"{col_name} BETWEEN CURRENT_DATE - INTERVAL ")
                completion_words.add(f"EXTRACT(YEAR FROM {col_name})")
                completion_words.add(f"DATE_TRUNC('month', {col_name})")
            elif 'CHAR' in data_type.upper() or 'TEXT' in data_type.upper() or 'VARCHAR' in data_type.upper():
                # String columns
                completion_words.add(f"{col_name} LIKE '%")
                completion_words.add(f"{col_name} ILIKE '%")
                completion_words.add(f"LOWER({col_name}) = ")
                completion_words.add(f"UPPER({col_name}) = ")
        
        # Convert set back to list and sort for better usability
        completion_list = list(completion_words)
        completion_list.sort(key=lambda x: (not x.isupper(), x))  # Prioritize SQL keywords
        
        return completion_list
        
    def _detect_relationships(self, table, columns, potential_relationships):
        """
        Detect potential relationships between tables based on column naming patterns.
        
        Args:
            table: Current table name
            columns: List of column names in this table
            potential_relationships: List to populate with detected relationships
        """
        # Look for columns that might be foreign keys (common patterns)
        for col in columns:
            # Common ID patterns: table_id, tableId, TableID, etc.
            if col.lower().endswith('_id') or col.lower().endswith('id'):
                # Extract potential table name from column name
                if col.lower().endswith('_id'):
                    potential_table = col[:-3]  # Remove '_id'
                else:
                    # Try to extract tablename from camelCase or PascalCase
                    potential_table = col[:-2]  # Remove 'Id'
                
                # Normalize to lowercase for comparison
                potential_table = potential_table.lower()
                
                # Check if this potential table exists in our loaded tables
                for existing_table in self.loaded_tables.keys():
                    # Normalize for comparison
                    existing_lower = existing_table.lower()
                    
                    # If we find a matching table, it's likely a relationship
                    if existing_lower == potential_table or existing_lower.endswith(f"_{potential_table}"):
                        # Add this relationship
                        # We assume the target column in the referenced table is 'id'
                        potential_relationships.append((table, col, existing_table, 'id'))
                        break
            
            # Also detect columns with same name across tables (potential join points)
            for other_table, other_columns in self.table_columns.items():
                if other_table != table and col in other_columns:
                    # Same column name in different tables - potential join point
                    potential_relationships.append((table, col, other_table, col))
    
    def _detect_column_types(self, table, column_data_types):
        """
        Detect column data types for a table to enable smarter autocompletion.
        
        Args:
            table: Table name to analyze
            column_data_types: Dictionary to populate with column data types
        """
        if not self.is_connected():
            return
            
        try:
            if self.connection_type == 'sqlite':
                # Get column info from SQLite
                cursor = self.conn.cursor()
                cursor.execute(f"PRAGMA table_info({table})")
                columns_info = cursor.fetchall()
                
                for column_info in columns_info:
                    col_name = column_info[1]  # Column name is at index 1
                    data_type = column_info[2]  # Data type is at index 2
                    
                    # Store as table.column: data_type for qualified lookups
                    column_data_types[f"{table}.{col_name}"] = data_type
                    # Also store just column: data_type for unqualified lookups
                    column_data_types[col_name] = data_type
                    
            elif self.connection_type == 'duckdb':
                # Get column info from DuckDB
                query = f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name='{table}' AND table_schema='main'
                """
                result = self.conn.execute(query).fetchdf()
                
                for _, row in result.iterrows():
                    col_name = row['column_name']
                    data_type = row['data_type']
                    
                    # Store as table.column: data_type for qualified lookups
                    column_data_types[f"{table}.{col_name}"] = data_type
                    # Also store just column: data_type for unqualified lookups
                    column_data_types[col_name] = data_type
        except Exception:
            # Ignore errors in type detection - this is just for enhancement
            pass 
    
    def load_specific_table(self, table_name):
        """
        Load metadata for a specific table from the database.
        This is used when we know which tables we want to load rather than loading all tables.
        
        Args:
            table_name: Name of the table to load
            
        Returns:
            Boolean indicating if the table was found and loaded
        """
        if not self.is_connected():
            return False
            
        try:
            if self.connection_type == 'sqlite':
                # Check if the table exists in SQLite
                cursor = self.conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                result = cursor.fetchone()
                
                if result:
                    # Get column names for the table
                    try:
                        column_query = f"PRAGMA table_info({table_name})"
                        columns = cursor.execute(column_query).fetchall()
                        self.table_columns[table_name] = [col[1] for col in columns]  # Column name is at index 1
                    except Exception:
                        self.table_columns[table_name] = []
                    
                    # Register the table
                    self.loaded_tables[table_name] = 'database'
                    return True
                    
            else:  # duckdb
                # Check if the table exists in DuckDB
                query = f"SELECT table_name FROM information_schema.tables WHERE table_name='{table_name}' AND table_schema='main'"
                result = self.conn.execute(query).fetchdf()
                
                if not result.empty:
                    # Get column names for the table
                    try:
                        column_query = f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}' AND table_schema='main'"
                        columns = self.conn.execute(column_query).fetchdf()
                        self.table_columns[table_name] = columns['column_name'].tolist()
                    except Exception:
                        self.table_columns[table_name] = []
                    
                    # Register the table
                    self.loaded_tables[table_name] = 'database'
                    return True
            
            return False
            
        except Exception:
            return False 