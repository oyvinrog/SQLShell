import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_sales_data(num_records=1000):
    """Create sample sales data"""
    # Generate random dates within the last year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    dates = pd.date_range(start=start_date, end=end_date, periods=num_records)
    
    # Generate random data
    data = {
        'orderid': range(1, num_records + 1),
        'orderdate': dates,
        'customerid': np.random.randint(1, 101, num_records),
        'productid': np.random.randint(1, 51, num_records),
        'quantity': np.random.randint(1, 11, num_records),
        'unitprice': np.random.uniform(10.0, 1000.0, num_records).round(2)
    }
    
    return pd.DataFrame(data)

def create_customer_data(num_customers=100):
    """Create sample customer data"""
    # Generate random customer data
    data = {
        'customerid': range(1, num_customers + 1),
        'customername': [f"Customer {i}" for i in range(1, num_customers + 1)],
        'email': [f"customer{i}@example.com" for i in range(1, num_customers + 1)],
        'country': np.random.choice(['USA', 'UK', 'Canada', 'Australia', 'Germany'], num_customers),
        'joindate': pd.date_range(start='2020-01-01', periods=num_customers).tolist()
    }
    
    return pd.DataFrame(data)

def create_product_data(num_products=50):
    """Create sample product data"""
    categories = ['Electronics', 'Books', 'Clothing', 'Home & Garden', 'Sports']
    
    # Generate random product data
    data = {
        'productid': range(1, num_products + 1),
        'productname': [f"Product {i}" for i in range(1, num_products + 1)],
        'category': np.random.choice(categories, num_products),
        'baseprice': np.random.uniform(5.0, 500.0, num_products).round(2),
        'instock': np.random.choice([True, False], num_products, p=[0.8, 0.2])
    }
    
    return pd.DataFrame(data) 