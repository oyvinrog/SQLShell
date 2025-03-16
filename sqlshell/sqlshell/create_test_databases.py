import pandas as pd
import sqlite3
import duckdb
import os

# Define paths
TEST_DATA_DIR = 'test_data'
SQLITE_DB_PATH = os.path.join(TEST_DATA_DIR, 'test.db')
DUCKDB_PATH = os.path.join(TEST_DATA_DIR, 'test.duckdb')

def load_source_data():
    """Load the source Excel and Parquet files."""
    sales_df = pd.read_excel(os.path.join(TEST_DATA_DIR, 'sample_sales_data.xlsx'))
    customer_df = pd.read_parquet(os.path.join(TEST_DATA_DIR, 'customer_data.parquet'))
    product_df = pd.read_excel(os.path.join(TEST_DATA_DIR, 'product_catalog.xlsx'))
    return sales_df, customer_df, product_df

def create_sqlite_database():
    """Create SQLite database with the test data."""
    # Remove existing database if it exists
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
    
    # Load data
    sales_df, customer_df, product_df = load_source_data()
    
    # Create connection and write tables
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        sales_df.to_sql('sales', conn, index=False)
        customer_df.to_sql('customers', conn, index=False)
        product_df.to_sql('products', conn, index=False)
        
        # Create indexes for better performance
        conn.execute('CREATE INDEX idx_sales_customer ON sales(CustomerID)')
        conn.execute('CREATE INDEX idx_sales_product ON sales(ProductID)')
    
    print(f"Created SQLite database at {SQLITE_DB_PATH}")

def create_duckdb_database():
    """Create DuckDB database with the test data."""
    # Remove existing database if it exists
    if os.path.exists(DUCKDB_PATH):
        os.remove(DUCKDB_PATH)
    
    # Load data
    sales_df, customer_df, product_df = load_source_data()
    
    # Create connection and write tables
    with duckdb.connect(DUCKDB_PATH) as conn:
        conn.execute("CREATE TABLE sales AS SELECT * FROM sales_df")
        conn.execute("CREATE TABLE customers AS SELECT * FROM customer_df")
        conn.execute("CREATE TABLE products AS SELECT * FROM product_df")
        
        # Create indexes for better performance
        conn.execute('CREATE INDEX idx_sales_customer ON sales(CustomerID)')
        conn.execute('CREATE INDEX idx_sales_product ON sales(ProductID)')
    
    print(f"Created DuckDB database at {DUCKDB_PATH}")

def verify_databases():
    """Verify the databases were created correctly by running test queries."""
    # Test SQLite
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        sales_count = pd.read_sql("SELECT COUNT(*) as count FROM sales", conn).iloc[0]['count']
        print(f"\nSQLite verification:")
        print(f"Sales records: {sales_count}")
        
        # Test a join query
        sample_query = """
        SELECT 
            p.Category,
            COUNT(*) as NumOrders,
            ROUND(SUM(s.TotalAmount), 2) as TotalRevenue
        FROM sales s
        JOIN products p ON s.ProductID = p.ProductID
        GROUP BY p.Category
        LIMIT 3
        """
        print("\nSample SQLite query result:")
        print(pd.read_sql(sample_query, conn))
    
    # Test DuckDB
    with duckdb.connect(DUCKDB_PATH) as conn:
        sales_count = conn.execute("SELECT COUNT(*) as count FROM sales").fetchone()[0]
        print(f"\nDuckDB verification:")
        print(f"Sales records: {sales_count}")
        
        # Test the same join query
        print("\nSample DuckDB query result:")
        print(conn.execute(sample_query).df())

if __name__ == '__main__':
    print("Creating test databases...")
    create_sqlite_database()
    create_duckdb_database()
    verify_databases() 