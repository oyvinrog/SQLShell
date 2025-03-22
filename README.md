# SQL Shell

A GUI application that provides a SQL REPL interface for querying Excel and parquet files (more to come!)


![SQLShell Interface](sqlshell_demo.png)

## Features

- SQL query interface with syntax highlighting
- Support for querying local DuckDB database (pool.db)
- Import and query Excel files (.xlsx, .xls) and CSV files
- Results displayed in a clear, tabular format
- Keyboard shortcuts (Ctrl+Enter to execute queries)

## Installation and Setup

### Using Virtual Environment (Linux)
```bash
# Create and activate virtual environment
python3 -m venv ~/.venv/sqlshell
source ~/.venv/sqlshell/bin/activate

# Install SQLShell
pip install sqlshell

# Add alias to your shell configuration (~/.bashrc or ~/.zshrc)
echo 'alias sqls="~/.venv/sqlshell/bin/sqls"' >> ~/.bashrc  # or ~/.zshrc for Zsh users
source ~/.bashrc  # or source ~/.zshrc
```

That's it! Now you can use `sqls` from anywhere.

### Quick Install (Windows)
On Windows, after running `pip install sqlshell`, the `sqls` command will be available immediately in any terminal.

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

select distinct productid from test_v;
```