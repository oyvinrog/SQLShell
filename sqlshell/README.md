# SQLShell - DEPRECATED README

**NOTE: This README is deprecated. Please refer to the main README.md file in the root directory of the repository for the most up-to-date information.**

A powerful SQL shell with GUI interface for data analysis. SQLShell provides an intuitive interface for working with various data formats (CSV, Excel, Parquet) using SQL queries powered by DuckDB.

![SQLShell Interface](sqlshell_demo.png)

## Features

- Load and analyze data from CSV, Excel (.xlsx, .xls), and Parquet files
- Interactive GUI with syntax highlighting
- Real-time query results
- Table preview functionality
- Built-in test data generation
- Support for multiple concurrent table views
- "Explain Column" feature for analyzing relationships between data columns

## Installation

You can install SQLShell using pip:

```bash
pip install sqlshell
```

refer to 

For development installation:

```bash
git clone https://github.com/oyvinrog/SQLShell.git
cd sqlshell
pip install -e .
```

## Usage

After installation, you can start SQLShell from anywhere in your terminal by running:

```bash
sqls
```

This will open the GUI interface where you can:
1. Load data files using the "Load Files" button
2. Write SQL queries in the query editor
3. Execute queries using the "Execute" button or Ctrl+Enter
4. View results in the table view below
5. Load sample test data using the "Test" button
6. Right-click on column headers in the results to access features like sorting, filtering, and the "Explain Column" analysis tool

## Requirements

- Python 3.8 or higher
- PyQt6
- DuckDB
- Pandas
- Other dependencies will be automatically installed

## License

This project is licensed under the MIT License - see the LICENSE file for details. 