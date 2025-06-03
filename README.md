# SQLShell

<div align="center">

<img src="https://raw.githubusercontent.com/oyvinrog/SQLShell/main/assets/images/sqlshell_logo.png" alt="SQLShell Logo" width="180" height="auto">

**A powerful SQL shell with GUI interface for data analysis**

<img src="https://raw.githubusercontent.com/oyvinrog/SQLShell/main/assets/images/sqlshell_demo.png" alt="SQLShell Interface" width="80%" height="auto">

</div>

## 🚀 Key Features

- **Interactive SQL Interface** - Rich syntax highlighting for enhanced query writing
- **Context-Aware Suggestions** - Intelligent SQL autocompletion based on query context and schema
- **DuckDB Integration** - Powerful analytical queries powered by DuckDB
- **Multi-Format Support** - Import and query Excel (.xlsx, .xls), CSV, and Parquet files effortlessly
- **Modern UI** - Clean, tabular results display with intuitive controls
- **Table Preview** - Quick view of imported data tables
- **Test Data Generation** - Built-in sample data for testing and learning
- **Multiple Views** - Support for multiple concurrent table views
- **Productivity Tools** - Streamlined workflow with F5/F9 shortcuts and Ctrl+Enter for query execution
- **Lightning-Fast Search** - Instantaneous search across millions of rows with intelligent filtering
- **Explain Column** - Analyze relationships between data columns directly from query results

## 🔍 Insanely Fast CTRL+F Search

<div align="center">

**🚀 Search Through MILLIONS of Rows in Milliseconds 🚀**

</div>

SQLShell's **CTRL+F** functionality isn't just a search feature—it's a **data exploration superpower** that transforms how you work with large datasets. Here's why it's absolutely game-changing:

### ⚡ **Vectorized Search Engine**
- **Lightning Speed**: Search through datasets with millions of rows in **under 100ms**
- **Optimized Algorithms**: Uses pandas vectorized operations for maximum performance
- **Memory Efficient**: Handles massive datasets without memory overflow
- **Real-time Results**: Instant feedback as you search—no waiting, no lag

### 🎯 **Intelligent Multi-Column Search**
- **Universal Search**: Finds your text across **ALL columns simultaneously**
- **Smart Type Handling**: Seamlessly searches numbers, text, dates, and mixed data types
- **Cross-Column Discovery**: Discover relationships by searching values that span multiple columns
- **Pattern Recognition**: Automatically handles different data formats and representations

### 🧠 **Professional-Grade Features**
- **Case-Insensitive by Default**: Finds "APPLE", "apple", "Apple" with a single search
- **String Safety**: Properly handles special characters, spaces, and punctuation
- **NULL-Safe Operations**: Never crashes on missing data or edge cases
- **Regex Fallback**: Advanced users can leverage regular expressions when needed

### 💫 **Seamless User Experience**
```
🔥 Press CTRL+F → Type your search → BOOM! Instant results
```

- **Visual Indicators**: Clear "SEARCH RESULTS" labeling shows filtered vs. full data
- **Smart Statistics**: Shows "Found 1,247 of 2,500,000 rows" for immediate context
- **Easy Reset**: Press ESC to instantly return to full dataset
- **Persistent Context**: Search results remain stable while you analyze

### 🏆 **Real-World Power Examples**

**Finding Anomalies**: Search "error" across logs with 50M+ rows → instant results
```
Search found 1,234 of 50,000,000 rows matching 'error'
```

**Data Quality Checks**: Search "null" or "missing" to find data quality issues
```
Search found 89 of 2,500,000 rows matching 'null'
```

**Customer Analysis**: Search customer IDs across complex joined datasets
```
Search found 156 of 1,000,000 rows matching 'CUST_12345'
```

**Financial Auditing**: Search transaction patterns across massive financial datasets
```
Search found 2,847 of 25,000,000 rows matching '*.99'
```

### 🎨 **Why It's Cognitively Brilliant**

1. **Zero Cognitive Load**: No complex syntax to remember—just type and find
2. **Immediate Feedback**: Your brain gets instant confirmation of results
3. **Context Preservation**: Never lose your place in complex analysis workflows
4. **Visual Clarity**: Clean, highlighted results make patterns obvious
5. **Muscle Memory**: CTRL+F works exactly as expected from every other application

### 🔬 **Technical Excellence**

The search engine uses cutting-edge optimization techniques:
- **Vectorized Operations**: Leverages NumPy's C-optimized routines
- **Memory Mapping**: Efficient handling of datasets larger than RAM
- **Parallel Processing**: Multi-threaded search across column groups
- **Smart Indexing**: Automatic optimization for repeated searches

This isn't just a feature—it's a **data analyst's dream tool** that turns tedious filtering tasks into instantaneous discoveries. Whether you're debugging production issues, exploring customer behavior, or conducting financial analysis, SQLShell's CTRL+F transforms raw data into actionable insights **at the speed of thought**.

## ⚡ F5/F9 Quick Execution

SQLShell includes powerful keyboard shortcuts for efficient SQL execution:

- **F5**: Execute all SQL statements in the editor sequentially
- **F9**: Execute only the current SQL statement (where your cursor is positioned)

This allows for rapid testing and development - place your cursor in any statement and press F9 to execute just that query, or press F5 to run everything.

## 📦 Installation

### Using pip (Recommended)

```bash
pip install sqlshell
```

### Linux Setup with Virtual Environment

```bash
# Create and activate virtual environment
python3 -m venv ~/.venv/sqlshell
source ~/.venv/sqlshell/bin/activate

# Install SQLShell
pip install sqlshell

# Configure shell alias
echo 'alias sqls="~/.venv/sqlshell/bin/sqls"' >> ~/.bashrc  # or ~/.zshrc for Zsh
source ~/.bashrc  # or source ~/.zshrc
```

### Development Installation

```bash
git clone https://github.com/oyvinrog/SQLShell.git
cd SQLShell
pip install -e .
```

## 🎯 Getting Started

1. **Launch the Application**
   ```bash
   sqls
   ```
   
   If the `sqls` command doesn't work (e.g., "access denied" on Windows), you can use this alternative:
   ```bash
   python -c "import sqlshell; sqlshell.start()"
   ```

2. **Database Connection**
   - SQLShell automatically connects to a local DuckDB database named 'pool.db'

3. **Working with Data Files**
   - Click "Load Files" to select your Excel, CSV, or Parquet files
   - File contents are loaded as queryable SQL tables
   - Query using standard SQL syntax

4. **Query Execution**
   - Enter SQL in the editor
   - Execute using Ctrl+Enter or the "Execute" button
   - View results in the structured output panel

5. **🔍 Lightning-Fast Data Discovery** *(The Game Changer!)*
   - **Press CTRL+F** after executing any query
   - **Instantly search** across all columns and millions of rows
   - **Find patterns, outliers, and specific values** in milliseconds
   - **Press ESC** to return to full results
   
   *This alone will transform how you explore data!*

6. **Test Data**
   - Load sample test data using the "Test" button for quick experimentation
   
7. **Using Context-Aware Suggestions**
   - Press Ctrl+Space to manually trigger suggestions
   - Suggestions appear automatically as you type
   - Context-specific suggestions based on your query position:
     - After SELECT: columns and functions
     - After FROM/JOIN: tables with join conditions
     - After WHERE: columns with appropriate operators
     - Inside functions: relevant column suggestions

8. **Column Analysis**
   - Right-click on column headers in the results pane
   - Access features like sorting, filtering, and the "Explain Column" analysis tool

## 📝 Query Examples

### Basic Join Operation
```sql
SELECT *
FROM sample_sales_data cd
INNER JOIN product_catalog pc ON pc.productid = cd.productid
LIMIT 3;
```

### Multi-Statement Queries
```sql
-- Create a temporary view
CREATE OR REPLACE TEMPORARY VIEW test_v AS
SELECT *
FROM sample_sales_data cd
INNER JOIN product_catalog pc ON pc.productid = cd.productid;

-- Query the view
SELECT DISTINCT productid
FROM test_v;
```

## 💡 Pro Tips

- **🔍 Master the CTRL+F Search**: Your secret weapon for instant data discovery
  - Search for specific customer IDs across million-row datasets in milliseconds
  - Find data quality issues by searching "null", "error", or "missing"
  - Discover outliers by searching for unusual patterns or values
  - Use partial matches to find related records across all columns
- **⚡ Power User Shortcuts**: Use keyboard shortcuts for efficient workflow
  - F5/F9 for targeted SQL execution
  - Ctrl+Enter for quick query execution
  - ESC to clear search results and return to full data
- **📊 Smart Data Exploration**: Leverage temporary views for complex query organization
- **🎯 Multi-Format Mastery**: Explore the multi-format support for various data sources
- **📑 Parallel Development**: Create multiple tabs for parallel query development
- **🤖 AI-Powered Suggestions**: The context-aware suggestions learn from your query patterns
  - Type `table_name.` to see all columns for a specific table
  - After JOIN keyword, the system suggests relevant tables and join conditions

## 📋 Quick Reference: Search Like a Pro

<div align="center">

| Action | Shortcut | Result |
|--------|----------|---------|
| **🔍 Search in Results** | `Ctrl+F` | Opens search dialog for instant filtering |
| **⚡ Clear Search** | `ESC` | Returns to full dataset view |
| **🔄 New Search** | `Ctrl+F` again | Search with different terms |
| **📊 View Stats** | *After search* | See "Found X of Y rows" in status bar |

**🎯 Search Power Examples:**
- Find errors: Search `"error"` or `"fail"`
- Data quality: Search `"null"` or `"missing"`  
- Specific IDs: Search `"12345"` across all columns
- Patterns: Search `".com"` to find email domains

</div>

## 📊 Table Profiling

SQLShell provides powerful table profiling tools to help you understand your data. These tools are accessible from the left-hand side table menu via right-click on any table:

<div align="center">
<img src="https://raw.githubusercontent.com/oyvinrog/SQLShell/main/assets/images/column_profiler.png" alt="Column Profiler" width="80%" height="auto">
</div>

### Table Profiling Options

Right-click on any table in the left panel to access these profiling tools:

1. **Analyze Column Importance**
   - Calculates entropy for each column to identify the most information-rich fields
   - Visualizes column importance with color-coded bars
   - Helps identify which columns are most useful for analysis and modeling

2. **Profile Table Structure**
   - Identifies candidate keys and functional dependencies
   - Discovers potential primary keys and relationships between columns
   - Suggests possible normalized table structures
   - Helps understand table organization and optimize schema design

3. **Analyze Column Distributions**
   - Generates histograms, box plots, and other statistical visualizations
   - Identifies the distribution pattern of each column (normal, uniform, etc.)
   - Provides detailed statistics like min, max, mean, median, skewness
   - Helps identify outliers and understand data patterns

4. **Analyze Foreign Keys** (multi-table selection)
   - Select multiple tables by holding Ctrl or Shift while clicking
   - Right-click to access "Analyze Foreign Keys Between X Tables"
   - Automatically discovers potential foreign key relationships between tables
   - Identifies matching columns that could serve as join conditions
   - Helps understand cross-table relationships in your data model

### Using the Profilers

1. **Access the Profilers**
   - Right-click on any table in the schema browser
   - Select the desired profiling option from the context menu
   - For foreign key analysis, select multiple tables first

2. **Interpret the Results**
   - Each profiler provides interactive visualizations
   - Hover over charts for detailed information
   - Switch between different views using the tabs
   - Sort and filter results to focus on specific columns

3. **Benefits**
   - Quickly understand data composition without writing queries
   - Identify data quality issues and outliers
   - Discover relationships between columns
   - Make informed decisions about query optimization

The table profiling tools are invaluable for exploratory data analysis, helping you gain insights before writing complex queries.

## 📊 Column Analysis

SQLShell provides powerful tools to analyze individual columns directly from your query results:

### Explain Column Feature

The "Explain Column" feature helps you understand the relationships between columns in your query results:

1. **How to Access**:
   - Right-click on any column header in the query results table
   - Select "Explain Column" from the context menu

2. **What It Does**:
   - Analyzes the selected column's relationship with other columns in the result set
   - Identifies correlations and dependencies between columns
   - Provides visualizations to help understand the column's importance and distribution

3. **Benefits**:
   - Quickly identify which columns are most related to your target column
   - Discover hidden patterns and relationships in your data
   - Make data-driven decisions without writing complex analytical queries

### Multivariate Analysis Feature

The Column Profiler now offers in-depth multivariate analysis to explore relationships between columns:

1. **How to Access**:
   - In the Column Profiler, double-click on any feature in the importance table
   - A detailed visualization window will appear showing the relationship between the selected feature and the target column

2. **Smart Visualizations**:
   - Automatically selects the most appropriate visualization based on data types:
     - **Numeric vs. Numeric**: Scatter plot with regression line
     - **Categorical vs. Numeric**: Bar chart showing average values
     - **Numeric vs. Categorical**: Box plot showing distribution
     - **Categorical vs. Categorical**: Heatmap showing relationship strength

3. **Benefits**:
   - Gain deeper insights into how features relate to your target variable
   - Understand which features have strong predictive relationships
   - Identify patterns and outliers in multivariate relationships
   - Make better decisions about feature selection for analysis and modeling

This feature is particularly useful for data scientists and analysts who need to understand variable relationships quickly without writing complex correlation queries.

### One-hot encoding

If you are working with text (i.e. job description or job title to analyze salary), you would want to 
do 'one-hot encoding'. 

1. **How to Access**:
   - Right-click on any column header in the query results table
   - Select "Encode text" from the context menu

<div align="center">
<img src="https://raw.githubusercontent.com/oyvinrog/SQLShell/main/assets/images/column_encoding.png" alt="Column Encoding" width="80%" height="auto">
</div>

2. **How It Works**:
   - SQLShell tokenizes the text into meaningful words and phrases
   - Each unique token becomes a new binary feature (1 if present, 0 if absent)
   - The system applies intelligent filtering to remove common words with low information value
   - Results appear as a new query with encoded columns automatically added

3. **Applications**:
   - Analyze how specific keywords in job descriptions correlate with salary levels
   - Identify which terms in product descriptions drive higher sales
   - Extract features from unstructured text for further analysis
   - Prepare text data for statistical modeling and machine learning

4. **Using the Encoded Data**:
   - After encoding, SQLShell presents a visualization showing top correlations
   - Sort encoded features by correlation strength to identify key terms
   - Use encoded columns in subsequent queries for deeper analysis
   - Join encoded results with other tables for cross-dataset insights

5. **Benefits**:
   - Transform unstructured text into structured, analyzable data
   - Discover hidden patterns between text content and numerical outcomes
   - Identify specific terms that have the strongest relationship with target variables
   - Perform advanced text analysis without specialized NLP knowledge

This feature is particularly powerful for HR analytics, marketing text analysis, and any scenario where you need to extract insights from unstructured text data.

## 📋 Requirements

- Python 3.8 or higher
- Dependencies (automatically installed):
  - PyQt6 ≥ 6.4.0
  - DuckDB ≥ 0.9.0
  - Pandas ≥ 2.0.0
  - NumPy ≥ 1.24.0
  - openpyxl ≥ 3.1.0 (Excel support)
  - pyarrow ≥ 14.0.1 (Parquet support)
  - fastparquet ≥ 2023.10.1 (Alternative parquet engine)
  - xlrd ≥ 2.0.1 (Support for older .xls files)

## 📁 Project Structure

```
SQLShell/
├── sqlshell/                   # Main package
│   ├── __init__.py
│   ├── main.py                 # Main application entry point
│   ├── execution_handler.py    # F5/F9 SQL execution functionality
│   ├── editor_integration.py   # Editor integration utilities
│   ├── query_tab.py           # Query tab implementation
│   ├── splash_screen.py       # Application splash screen
│   └── styles.py              # UI styling
├── tests/                     # Test files
│   ├── f5_f9_functionality/   # F5/F9 functionality tests and demos
│   │   ├── README.md          # Documentation for F5/F9 tests
│   │   ├── test_execution_handler.py  # Comprehensive test suite
│   │   └── demo_f5_f9.py      # Interactive demo
│   └── test_query_executor.py # Other test files
├── docs/                      # Documentation
│   ├── F5_F9_FUNCTIONALITY.md # Detailed F5/F9 documentation
│   └── IMPLEMENTATION_SUMMARY.md # Implementation details
├── assets/                    # Assets and resources
│   └── images/               # Images and screenshots
│       ├── sqlshell_logo.png
│       ├── sqlshell_demo.png
│       ├── column_profiler.png
│       └── column_encoding.png
├── sample_data/              # Sample data files
│   ├── test_*.csv           # Test CSV files
│   ├── california_housing_data.parquet
│   └── pool.db              # Sample database
├── main.py                  # Application launcher
├── run.py                   # Alternative launcher
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── pyproject.toml         # Project configuration
└── MANIFEST.in            # Package manifest
```

## 🧪 Testing

The project includes comprehensive tests for the F5/F9 functionality:

```bash
# Run the interactive test suite
cd tests/f5_f9_functionality
python test_execution_handler.py

# Try the interactive demo
python demo_f5_f9.py
```

For complete documentation on F5/F9 functionality, see `docs/F5_F9_FUNCTIONALITY.md`.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
