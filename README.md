# SQL Shell

A GUI application that provides a SQL REPL interface for querying Excel and parquet files (more to come!)


![SQLShell Interface](sqlshell_demo.png)

## Features

- SQL query interface with syntax highlighting
- Support for querying local DuckDB database (pool.db)
- Import and query Excel files (.xlsx, .xls) and CSV files
- Results displayed in a clear, tabular format
- Keyboard shortcuts (Ctrl+Enter to execute queries)

## Installation

### Simple Installation (Recommended)
```bash
pip install sqlshell
```

After installation, you can run SQLShell by typing:
```bash
sqls
```

### Windows Users - Important Notes

- **Python 3.13+**: The simple installation method above works best with Python 3.13 or newer on Windows
- **Older Python Versions**: If you encounter an error message about "dtype size changed" when running `sqls`, you have two options:

  1. **Upgrade Python** (Recommended):
     - Download and install the latest Python version from [python.org](https://www.python.org/downloads/)
     - Reinstall SQLShell using pip

  2. **Use a Virtual Environment**:
     ```bash
     # Create a virtual environment
     python -m venv venv
     
     # Activate it (Windows)
     venv\Scripts\activate
     
     # Install SQLShell
     pip install sqlshell
     
     # Run SQLShell
     sqls
     ```

## Usage

1. Run the application:
   ```bash
   sqls
   ```

2. The application will automatically connect to a local DuckDB database named 'pool.db'

3. To query Excel files:
   - Click the "Browse Excel" button
   - Select your Excel file
   - The file will be loaded as a table named 'imported_data'
   - Query the data using SQL commands (e.g., `SELECT * FROM imported_data`)

4. Enter SQL queries in the top text area
   - Press Ctrl+Enter or click "Execute" to run the query
   - Results will be displayed in the bottom panel

## Example Queries

```sql
select * from sample_sales_data cd inner join product_catalog pc on pc.productid = cd.productid limit 3
```

you can also do multiple statements, i.e:

```sql
create or replace temporary view test_v as 
select * from sample_sales_data cd
inner join product_catalog pc on pc.productid = cd.productid;

select distinct productid from test_v ;
```