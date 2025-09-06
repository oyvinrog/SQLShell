#!/usr/bin/env python3
"""
Test script to verify the multiple table deletion functionality.
This script tests the DatabaseManager's remove_multiple_tables method
and the overall functionality without needing the full GUI.
"""

import tempfile
import pandas as pd
from sqlshell.db.database_manager import DatabaseManager


def test_multiple_table_deletion():
    """Test the multiple table deletion functionality"""
    print("Testing multiple table deletion functionality...")
    
    # Create a temporary database
    db_manager = DatabaseManager()
    
    # Create some test data
    test_data1 = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35]
    })
    
    test_data2 = pd.DataFrame({
        'product_id': [1, 2, 3],
        'product_name': ['Widget A', 'Widget B', 'Widget C'],
        'price': [10.99, 15.99, 20.99]
    })
    
    test_data3 = pd.DataFrame({
        'order_id': [1, 2, 3],
        'customer_id': [1, 2, 3],
        'total': [100.50, 250.75, 500.00]
    })
    
    # Create temporary CSV files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f1:
        test_data1.to_csv(f1.name, index=False)
        users_file = f1.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f2:
        test_data2.to_csv(f2.name, index=False)
        products_file = f2.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f3:
        test_data3.to_csv(f3.name, index=False)
        orders_file = f3.name
    
    try:
        # Load the test data as tables
        db_manager.load_file(users_file)
        db_manager.load_file(products_file)
        db_manager.load_file(orders_file)
        
        # Get table names (they'll be based on the temp file names)
        table_names = list(db_manager.loaded_tables.keys())
        print(f"Loaded tables: {table_names}")
        
        # Test: Try to delete some tables (but not all)
        tables_to_delete = table_names[:2]  # Delete first 2 tables
        print(f"Attempting to delete tables: {tables_to_delete}")
        
        # Call the multiple table deletion method
        successful, failed = db_manager.remove_multiple_tables(tables_to_delete)
        
        print(f"Successfully deleted: {successful}")
        print(f"Failed to delete: {failed}")
        
        # Verify the tables were actually removed
        remaining_tables = list(db_manager.loaded_tables.keys())
        print(f"Remaining tables: {remaining_tables}")
        
        # Test: Try to delete non-existent tables
        print("\nTesting deletion of non-existent tables...")
        fake_tables = ['non_existent_table1', 'non_existent_table2']
        successful2, failed2 = db_manager.remove_multiple_tables(fake_tables)
        
        print(f"Successfully deleted (fake): {successful2}")
        print(f"Failed to delete (fake): {failed2}")
        
        # Test: Delete all remaining tables
        print("\nDeleting all remaining tables...")
        remaining_tables = list(db_manager.loaded_tables.keys())
        if remaining_tables:
            successful3, failed3 = db_manager.remove_multiple_tables(remaining_tables)
            print(f"Successfully deleted remaining: {successful3}")
            print(f"Failed to delete remaining: {failed3}")
        
        final_tables = list(db_manager.loaded_tables.keys())
        print(f"Final remaining tables: {final_tables}")
        
        # Validate results
        assert len(successful) == 2, f"Expected 2 successful deletions, got {len(successful)}"
        assert len(failed) == 0, f"Expected 0 failed deletions, got {len(failed)}"
        assert len(failed2) == 2, f"Expected 2 failed deletions for fake tables, got {len(failed2)}"
        assert len(successful2) == 0, f"Expected 0 successful deletions for fake tables, got {len(successful2)}"
        assert len(final_tables) == 0, f"Expected 0 final tables, got {len(final_tables)}"
        
        print("\n✅ All tests passed! Multiple table deletion functionality works correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up temporary files
        import os
        try:
            os.unlink(users_file)
            os.unlink(products_file)
            os.unlink(orders_file)
        except:
            pass


if __name__ == "__main__":
    test_multiple_table_deletion()