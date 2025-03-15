import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set random seed for reproducibility
np.random.seed(42)

# Generate sample data
num_records = 1000

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
    'Product': np.random.choice(products, num_records),
    'Quantity': np.random.randint(1, 11, num_records),
    'CustomerID': np.random.randint(1, 201, num_records),
    'Region': np.random.choice(['North', 'South', 'East', 'West'], num_records)
}

# Calculate prices based on product
data['Price'] = [np.random.uniform(product_prices[p][0], product_prices[p][1]) 
                 for p in data['Product']]
data['TotalAmount'] = [price * qty for price, qty in zip(data['Price'], data['Quantity'])]

# Create DataFrame
df = pd.DataFrame(data)

# Round numerical columns
df['Price'] = df['Price'].round(2)
df['TotalAmount'] = df['TotalAmount'].round(2)

# Sort by Date
df = df.sort_values('Date')

# Save to Excel
output_file = 'sample_sales_data.xlsx'
df.to_excel(output_file, index=False)

print(f"Created sample sales data in '{output_file}'")
print(f"Number of records: {len(df)}")
print("\nSample data preview:")
print(df.head())
print("\nData summary:")
print(df.describe()) 