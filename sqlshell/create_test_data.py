import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Set random seed for reproducibility
np.random.seed(42)

# Define output directory
OUTPUT_DIR = 'test_data'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_california_housing_data(output_file='california_housing_data.parquet'):
    """Use the real world california housing dataset"""
    # Load the dataset
    df = pd.read_csv('https://raw.githubusercontent.com/ageron/handson-ml/master/datasets/housing/housing.csv')
    
    # Save to Parquet
    df.to_parquet(output_file)
    return df

def create_large_customer_data(num_customers=1_000_000, chunk_size=100_000, output_file='large_customer_data.parquet'):
    """Create a large customer dataset """
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
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    return df


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

def create_large_numbers_data(num_records=100):
    """Create a dataset with very large numbers for testing and visualization."""
    
    # Generate random IDs
    ids = range(1, num_records + 1)
    
    # Create different columns with large numbers
    data = {
        'ID': ids,
        'Date': pd.date_range(start='2023-01-01', periods=num_records),
        'SmallValue': np.random.randint(1, 1000, num_records),
        'MediumValue': np.random.randint(10000, 9999999, num_records),
        'LargeValue': [int(str(np.random.randint(1, 999)) + str(np.random.randint(0, 9999999)).zfill(7) + 
                          str(np.random.randint(0, 9999)).zfill(4)) for _ in range(num_records)],
        'VeryLargeValue': [int(str(np.random.randint(100, 999)) + str(np.random.randint(1000000, 9999999)) + 
                             str(np.random.randint(1000000, 9999999))) for _ in range(num_records)],
        'MassiveValue': [int('1' + ''.join([str(np.random.randint(0, 10)) for _ in range(15)])) for _ in range(num_records)],
        'Category': np.random.choice(['A', 'B', 'C', 'D', 'E'], num_records),
        'IsActive': np.random.choice([True, False], num_records, p=[0.8, 0.2])
    }
    
    # Create exponential values for scientific notation
    data['ExponentialValue'] = [float(f"{np.random.randint(1, 10)}.{np.random.randint(1, 100):02d}e{np.random.randint(10, 20)}") 
                              for _ in range(num_records)]
    
    # Create monetary values (with decimals)
    data['Revenue'] = [np.random.randint(1000000, 9999999999) + np.random.random() for _ in range(num_records)]
    data['Budget'] = [np.random.randint(10000000, 999999999) + np.random.random() for _ in range(num_records)]
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Round monetary values to 2 decimal places
    df['Revenue'] = df['Revenue'].round(2)
    df['Budget'] = df['Budget'].round(2)
    
    return df 