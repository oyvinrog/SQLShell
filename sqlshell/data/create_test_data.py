import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Set random seed for reproducibility
np.random.seed(42)

# Define output directory
OUTPUT_DIR = 'test_data'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_sales_data(num_records=1000):
    # Generate dates for the last 365 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    dates = [start_date + timedelta(days=x) for x in range(366)]
    random_dates = np.random.choice(dates, num_records)

    # Create product data
    products = ['Laptop', 'Smartphone', 'Tablet', 'Monitor', 'Keyboard', 'Mouse', 'Headphones', 'Printer']
    product_prices = {
        'Laptop': (800, 2000),
        'Smartphone': (400, 1200),
        'Tablet': (200, 800),
        'Monitor': (150, 500),
        'Keyboard': (20, 150),
        'Mouse': (10, 80),
        'Headphones': (30, 300),
        'Printer': (100, 400)
    }

    # Generate random data
    data = {
        'OrderID': range(1, num_records + 1),
        'Date': random_dates,
        'ProductID': np.random.randint(1, len(products) + 1, num_records),  # Changed to ProductID for joining
        'Quantity': np.random.randint(1, 11, num_records),
        'CustomerID': np.random.randint(1, 201, num_records),
        'Region': np.random.choice(['North', 'South', 'East', 'West'], num_records)
    }

    # Calculate prices based on product
    product_list = [products[pid-1] for pid in data['ProductID']]
    data['Price'] = [np.random.uniform(product_prices[p][0], product_prices[p][1]) 
                     for p in product_list]
    data['TotalAmount'] = [price * qty for price, qty in zip(data['Price'], data['Quantity'])]

    # Create DataFrame
    df = pd.DataFrame(data)

    # Round numerical columns
    df['Price'] = df['Price'].round(2)
    df['TotalAmount'] = df['TotalAmount'].round(2)

    # Sort by Date
    return df.sort_values('Date')

def create_customer_data(num_customers=200):
    # Generate customer data
    data = {
        'CustomerID': range(1, num_customers + 1),
        'FirstName': [f'Customer{i}' for i in range(1, num_customers + 1)],
        'LastName': [f'Lastname{i}' for i in range(1, num_customers + 1)],
        'Email': [f'customer{i}@example.com' for i in range(1, num_customers + 1)],
        'JoinDate': [datetime.now() - timedelta(days=np.random.randint(1, 1000)) 
                     for _ in range(num_customers)],
        'CustomerType': np.random.choice(['Regular', 'Premium', 'VIP'], num_customers),
        'CreditScore': np.random.randint(300, 851, num_customers)
    }
    
    return pd.DataFrame(data)

def create_product_data():
    # Create detailed product information
    products = {
        'ProductID': range(1, 9),
        'ProductName': ['Laptop', 'Smartphone', 'Tablet', 'Monitor', 'Keyboard', 'Mouse', 'Headphones', 'Printer'],
        'Category': ['Computers', 'Mobile', 'Mobile', 'Accessories', 'Accessories', 'Accessories', 'Audio', 'Peripherals'],
        'Brand': ['TechPro', 'MobileX', 'TabletCo', 'ViewMax', 'TypeMaster', 'ClickPro', 'SoundMax', 'PrintPro'],
        'StockQuantity': np.random.randint(50, 500, 8),
        'MinPrice': [800, 400, 200, 150, 20, 10, 30, 100],
        'MaxPrice': [2000, 1200, 800, 500, 150, 80, 300, 400],
        'Weight_kg': [2.5, 0.2, 0.5, 3.0, 0.8, 0.1, 0.3, 5.0],
        'WarrantyMonths': [24, 12, 12, 36, 12, 12, 24, 12]
    }
    
    return pd.DataFrame(products)

if __name__ == '__main__':
    # Create and save sales data
    sales_df = create_sales_data()
    sales_output = os.path.join(OUTPUT_DIR, 'sample_sales_data.xlsx')
    sales_df.to_excel(sales_output, index=False)
    print(f"Created sales data in '{sales_output}'")
    print(f"Number of sales records: {len(sales_df)}")
    
    # Create and save customer data as parquet
    customer_df = create_customer_data()
    customer_output = os.path.join(OUTPUT_DIR, 'customer_data.parquet')
    customer_df.to_parquet(customer_output, index=False)
    print(f"\nCreated customer data in '{customer_output}'")
    print(f"Number of customers: {len(customer_df)}")
    
    # Create and save product data
    product_df = create_product_data()
    product_output = os.path.join(OUTPUT_DIR, 'product_catalog.xlsx')
    product_df.to_excel(product_output, index=False)
    print(f"\nCreated product catalog in '{product_output}'")
    print(f"Number of products: {len(product_df)}")
    
    # Print sample queries
    print("\nSample SQL queries for joining the data:")
    print("""
    -- Join sales with customer data
    SELECT s.*, c.FirstName, c.LastName, c.CustomerType
    FROM test_data.sample_sales_data s
    JOIN test_data.customer_data c ON s.CustomerID = c.CustomerID;
    
    -- Join sales with product data
    SELECT s.*, p.ProductName, p.Category, p.Brand
    FROM test_data.sample_sales_data s
    JOIN test_data.product_catalog p ON s.ProductID = p.ProductID;
    
    -- Three-way join with aggregation
    SELECT 
        p.Category,
        c.CustomerType,
        COUNT(*) as NumOrders,
        SUM(s.TotalAmount) as TotalRevenue,
        AVG(s.Quantity) as AvgQuantity
    FROM test_data.sample_sales_data s
    JOIN test_data.customer_data c ON s.CustomerID = c.CustomerID
    JOIN test_data.product_catalog p ON s.ProductID = p.ProductID
    GROUP BY p.Category, c.CustomerType
    ORDER BY p.Category, c.CustomerType;
    """) 