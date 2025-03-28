import os
from sqlshell import create_test_data

# Create test data directory if it doesn't exist
os.makedirs('test_data', exist_ok=True)

# Generate large numbers dataset
print("Generating large numbers dataset...")
large_numbers_df = create_test_data.create_large_numbers_data(100)

# Display sample of the large numbers
print("\nSample of large values:")
print(large_numbers_df[['LargeValue', 'VeryLargeValue', 'MassiveValue']].head())

# Save to Excel
print("\nSaving to Excel...")
excel_path = 'test_data/large_numbers.xlsx'
large_numbers_df.to_excel(excel_path, index=False)
print(f"Dataset saved to {excel_path}")

print("\nMedium value example:", large_numbers_df['MediumValue'].iloc[0])
print("Large value example:", large_numbers_df['LargeValue'].iloc[0])
print("Very large value example:", large_numbers_df['VeryLargeValue'].iloc[0])
print("Massive value example:", large_numbers_df['MassiveValue'].iloc[0])
print("Exponential value example:", large_numbers_df['ExponentialValue'].iloc[0]) 