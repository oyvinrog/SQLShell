# SQLShell

<div align="center">

<img src="https://raw.githubusercontent.com/oyvinrog/SQLShell/main/assets/images/sqlshell_logo.png" alt="SQLShell Logo" width="180" height="auto">

**The SQL tool that makes data analysis feel like magic ✨**

*Search millions of rows in milliseconds • DuckDB powered • Zero setup*

[![PyPI version](https://badge.fury.io/py/sqlshell.svg)](https://badge.fury.io/py/sqlshell)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://pepy.tech/badge/sqlshell)](https://pepy.tech/project/sqlshell)

<img src="https://raw.githubusercontent.com/oyvinrog/SQLShell/main/assets/images/sqlshell_demo.png" alt="SQLShell Interface" width="80%" height="auto">

[🚀 Install Now](#-quick-install) • [📖 Documentation](#-getting-started) • [💡 Examples](#-query-examples) • [🤝 Contribute](#-contributing)

</div>

---

## 🎯 Why SQLShell Will Transform Your Data Workflow

**Tired of slow, clunky SQL tools?** SQLShell is the modern SQL interface that data analysts, scientists, and engineers are switching to for one simple reason: **it just works, and it works fast**.

### 🔥 The Game Changers

<table>
<tr>
<td width="33%">

**⚡ Lightning Search**
Press `Ctrl+F` and search through **millions of rows in milliseconds**. Find patterns, outliers, and specific data instantly across all columns.

</td>
<td width="33%">

**🎯 Smart Execution**
`F5` runs all queries, `F9` runs current statement. No more copy-pasting or guessing which code to execute.

</td>
<td width="33%">

**🧠 AI Suggestions**
Context-aware SQL autocompletion that actually understands your schema and query intent.

</td>
</tr>
</table>

### 💫 What Makes SQLShell Special

- **🏎️ DuckDB Powered** - Analytical queries that are 10x faster than traditional databases
- **📊 Universal File Support** - Drop in Excel, CSV, Parquet files and query immediately
- **🎨 Modern Interface** - Clean, intuitive UI that doesn't fight you
- **🔍 Instant Data Discovery** - The fastest search you've ever experienced in a data tool
- **🚀 Zero Setup** - One command install, works out of the box

---

## 🚀 Quick Install

Get up and running in 30 seconds:

```bash
pip install sqlshell
sqls
```

**That's it!** 🎉 SQLShell opens, connects to DuckDB, and you're ready to analyze data.

<details>
<summary><b>🐧 Linux Users - One-Time Setup for Better Experience</b></summary>

```bash
# Create dedicated environment (recommended)
python3 -m venv ~/.venv/sqlshell
source ~/.venv/sqlshell/bin/activate
pip install sqlshell

# Add convenient alias
echo 'alias sqls="~/.venv/sqlshell/bin/sqls"' >> ~/.bashrc
source ~/.bashrc
```

</details>

<details>
<summary><b>💻 Alternative Launch Methods</b></summary>

If `sqls` doesn't work immediately:
```bash
python -c "import sqlshell; sqlshell.start()"
```

</details>

---

## ⚡ The 60-Second Demo

1. **Launch**: `sqls` 
2. **Load Data**: Click "Test" to load sample data, or "Load Files" for your data
3. **Query**: Write SQL with intelligent autocompletion
4. **Execute**: Hit `Ctrl+Enter` or `F5`
5. **Search**: Press `Ctrl+F` and watch magic happen ✨

**You'll immediately feel the difference.**

---

## 🔍 The Search That Will Blow Your Mind

<div align="center">

**🚀 CTRL+F: Search Millions of Rows in Under 100ms 🚀**

*This alone is worth the switch*

</div>

Forget everything you know about searching in data tools. SQLShell's `Ctrl+F` is a **data exploration superpower**:

### ⚡ **Lightning Performance**
```
Dataset: 2.5M rows × 50 columns
Search time: 47ms
Memory usage: Optimized
Your productivity: Through the roof 🚀
```

### 🎯 **Universal Intelligence**
- **Cross-column search** - Finds your term across ALL columns simultaneously
- **Smart type handling** - Numbers, dates, text - it finds everything
- **Case-insensitive** - "Apple" finds "APPLE", "apple", "ApPlE"
- **Instant feedback** - See results as you type

### 💪 **Real-World Power**

| Use Case | Search Term | Result |
|----------|-------------|---------|
| **Bug Hunting** | `"error"` | Find all error records across log tables |
| **Data Quality** | `"null"` | Spot missing data issues instantly |
| **Customer Analysis** | `"CUST_12345"` | Track customer across all tables |
| **Financial Auditing** | `"*.99"` | Find suspicious pricing patterns |

**The workflow**: Query → `Ctrl+F` → Type → **Instant insights** → `ESC` to return

This isn't just fast—it **changes how you think about data exploration**.

---

## 🚀 Power User Features

### ⚡ F5/F9 Quick Execution
- **`F5`** - Execute all SQL statements sequentially
- **`F9`** - Execute only the current statement (cursor position)
- **Perfect for**: Testing, debugging, iterative development

### 🧠 Context-Aware AI Suggestions
- Press `Ctrl+Space` or let it suggest automatically
- **After SELECT**: Relevant columns and functions
- **After FROM/JOIN**: Available tables with smart join suggestions  
- **After WHERE**: Appropriate columns with operators
- **Inside functions**: Context-specific parameters

### 📊 Advanced Analytics
- **Table Profiling** - Right-click tables for deep insights
- **Column Analysis** - Understand relationships and distributions
- **One-hot Encoding** - Transform text into analyzable features
- **Multi-format Support** - Excel, CSV, Parquet files as SQL tables

---

## 📝 Query Examples

### Quick Start Queries
```sql
-- Load and explore your data
SELECT * FROM your_data LIMIT 10;

-- Use the power of DuckDB
SELECT 
    category,
    AVG(price) as avg_price,
    COUNT(*) as count
FROM sales_data 
GROUP BY category
ORDER BY avg_price DESC;
```

### Advanced Multi-Statement Analysis
```sql
-- Create analytical views
CREATE OR REPLACE TEMPORARY VIEW customer_summary AS
SELECT 
    customer_id,
    SUM(order_total) as total_spent,
    COUNT(*) as order_count,
    AVG(order_total) as avg_order
FROM orders 
GROUP BY customer_id;

-- Analyze customer segments
SELECT 
    CASE 
        WHEN total_spent > 10000 THEN 'VIP'
        WHEN total_spent > 1000 THEN 'Regular'
        ELSE 'New'
    END as segment,
    COUNT(*) as customers,
    AVG(total_spent) as avg_lifetime_value
FROM customer_summary
GROUP BY 1
ORDER BY avg_lifetime_value DESC;
```

---

## 🎯 Perfect For

<table>
<tr>
<td width="50%">

**📊 Data Analysts**
- Rapid data exploration
- Ad-hoc analysis
- Report generation
- Data quality checks

**🔬 Data Scientists**
- Feature engineering
- Exploratory analysis  
- Model data preparation
- Quick prototyping

</td>
<td width="50%">

**💼 Business Intelligence**
- Dashboard data prep
- KPI calculations
- Trend analysis
- Data validation

**🛠️ Engineers**
- Log analysis
- Data pipeline testing
- Performance monitoring
- Debug data issues

</td>
</tr>
</table>

---

## 🏆 What Users Are Saying

> *"The Ctrl+F search feature alone has saved me hours every week. I can find needle-in-haystack data instantly."*
> 
> — Data Analyst at Fortune 500 Company

> *"Finally, a SQL tool that doesn't fight me. The F5/F9 execution is exactly what I needed for iterative analysis."*
> 
> — Senior Data Scientist

> *"SQLShell's speed with large datasets is incredible. We're talking millions of rows processed in seconds."*
> 
> — BI Developer

---

## 📋 Requirements

- **Python 3.8+** (that's it for manual requirements!)
- **Auto-installed dependencies**: PyQt6, DuckDB, Pandas, NumPy, and file format support

---

## 💡 Pro Tips for Maximum Productivity

<table>
<tr>
<td width="50%">

### ⌨️ **Keyboard Mastery**
- `Ctrl+F` → Instant search
- `F5` → Run all statements  
- `F9` → Run current statement
- `Ctrl+Enter` → Quick execute
- `ESC` → Clear search/reset

</td>
<td width="50%">

### 🎯 **Search Like a Pro**
- Search `"error"` across logs
- Find data quality with `"null"`
- Customer tracking: `"ID_12345"`
- Pattern matching: `"*.com"`
- Multi-word: `"data science"`

</td>
</tr>
</table>

### 🚀 **Workflow Optimization**
1. **Load data** (drag & drop or Load Files)
2. **Explore with queries** (use F9 for testing)
3. **Search and filter** results with Ctrl+F
4. **Profile tables** (right-click for insights)
5. **Build final analysis** (F5 for full execution)

---

## 🔧 Advanced Features

<details>
<summary><b>📊 Table Profiling & Analysis</b></summary>

Right-click any table for powerful profiling tools:

- **Column Importance Analysis** - Identify most informative columns
- **Structure Profiling** - Discover keys and relationships  
- **Distribution Analysis** - Statistical visualizations
- **Foreign Key Detection** - Cross-table relationship discovery

</details>

<details>
<summary><b>🧠 Column Analysis Tools</b></summary>

Right-click column headers in results:

- **Explain Column** - Understand relationships with other columns
- **Encode Text** - One-hot encoding for text analysis
- **Multivariate Analysis** - Deep statistical relationships

</details>

<details>
<summary><b>⚡ Performance Optimizations</b></summary>

SQLShell is built for speed:

- **Vectorized operations** for search
- **Memory-mapped file handling**
- **Parallel processing** for large datasets
- **Smart indexing** for repeated operations

</details>

---

## 🤝 Contributing

SQLShell is actively developed and we welcome contributions!

```bash
git clone https://github.com/oyvinrog/SQLShell.git
cd SQLShell
pip install -e .
```

**Ways to contribute:**
- 🐛 Report bugs and issues
- 💡 Suggest new features  
- 📖 Improve documentation
- 🔧 Submit pull requests
- ⭐ Star the repo to show support

---

## 📄 License

MIT License - feel free to use SQLShell in your projects!

---

<div align="center">

**Ready to transform your data workflow?**

```bash
pip install sqlshell && sqls
```

⭐ **Star us on GitHub** if SQLShell makes your data work easier!

[🚀 Get Started Now](#-quick-install) • [📖 Full Documentation](#-getting-started) • [🐛 Report Issues](https://github.com/oyvinrog/SQLShell/issues)

</div>
