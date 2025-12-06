import pandas as pd
import numpy as np
import time
import unittest
import sys
import os

# Add the parent directory to the path to import the search module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlshell.utils.search_in_df import search, search_optimized


class TestSearchPerformance(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up test data once for the entire test class."""
        print("Creating test dataset with 1 million rows and 20 columns...")
        start_time = time.time()
        
        # Set random seed for reproducibility
        np.random.seed(42)
        
        # Create 1 million rows with 20 columns
        cls.n_rows = 1_000_000
        cls.n_cols = 20
        
        # Generate diverse data types
        data = {}
        
        # String columns with various patterns
        data['name'] = [f"User_{i:06d}" for i in range(cls.n_rows)]
        data['email'] = [f"user{i}@{'company' if i % 3 == 0 else 'personal'}.com" for i in range(cls.n_rows)]
        data['city'] = np.random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia'], cls.n_rows)
        data['department'] = np.random.choice(['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Operations'], cls.n_rows)
        data['status'] = np.random.choice(['Active', 'Inactive', 'Pending', 'Suspended'], cls.n_rows)
        
        # Numeric columns
        data['age'] = np.random.randint(18, 80, cls.n_rows)
        data['salary'] = np.random.randint(30000, 200000, cls.n_rows)
        data['employee_id'] = range(cls.n_rows)
        data['score'] = np.random.uniform(0, 100, cls.n_rows).round(2)
        data['rating'] = np.random.uniform(1, 5, cls.n_rows).round(1)
        
        # Mixed columns
        data['product_code'] = [f"PRD-{np.random.randint(1000, 9999)}-{chr(65 + i % 26)}" for i in range(cls.n_rows)]
        data['description'] = [f"Product description for item {i} with various features" for i in range(cls.n_rows)]
        data['notes'] = [f"Important notes about record {i}" if i % 10 == 0 else "" for i in range(cls.n_rows)]
        
        # Date-like strings
        data['join_date'] = pd.date_range('2020-01-01', periods=cls.n_rows, freq='1H').strftime('%Y-%m-%d')
        data['last_login'] = pd.date_range('2023-01-01', periods=cls.n_rows, freq='2H').strftime('%Y-%m-%d %H:%M:%S')
        
        # Fill remaining columns with random data
        for i in range(15, cls.n_cols):
            col_name = f'column_{i}'
            if i % 3 == 0:
                data[col_name] = np.random.choice(['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon'], cls.n_rows)
            elif i % 3 == 1:
                data[col_name] = np.random.randint(0, 1000, cls.n_rows)
            else:
                data[col_name] = [f"Value_{j}_{i}" for j in range(cls.n_rows)]
        
        cls.df = pd.DataFrame(data)
        
        setup_time = time.time() - start_time
        print(f"Dataset created in {setup_time:.2f} seconds")
        print(f"Dataset shape: {cls.df.shape}")
        print(f"Memory usage: {cls.df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
        print()
    
    def measure_search_performance(self, search_func, search_text, description):
        """Measure performance of a search function."""
        print(f"Testing {description}")
        print(f"Search text: '{search_text}'")
        
        start_time = time.perf_counter()
        result = search_func(self.df, search_text)
        end_time = time.perf_counter()
        
        elapsed_time = end_time - start_time
        rows_found = len(result)
        
        print(f"Time taken: {elapsed_time:.4f} seconds")
        print(f"Rows found: {rows_found:,}")
        print(f"Performance: {self.n_rows / elapsed_time:,.0f} rows/second")
        print("-" * 50)
        
        return result, elapsed_time
    
    def test_search_common_word(self):
        """Test searching for a common word."""
        print("=" * 60)
        print("TEST 1: Search for common word 'User'")
        print("=" * 60)
        
        # Test regular search
        result1, time1 = self.measure_search_performance(
            search, "User", "Regular search function"
        )
        
        # Test optimized search
        result2, time2 = self.measure_search_performance(
            search_optimized, "User", "Optimized search function"
        )
        
        # Verify results are the same
        self.assertEqual(len(result1), len(result2), "Both search methods should return the same number of rows")
        
        # Performance comparison
        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"Speedup factor: {speedup:.2f}x")
        print()
    
    def test_search_specific_pattern(self):
        """Test searching for a specific pattern."""
        print("=" * 60)
        print("TEST 2: Search for specific pattern 'Engineering'")
        print("=" * 60)
        
        # Test regular search
        result1, time1 = self.measure_search_performance(
            search, "Engineering", "Regular search function"
        )
        
        # Test optimized search
        result2, time2 = self.measure_search_performance(
            search_optimized, "Engineering", "Optimized search function"
        )
        
        # Verify results
        self.assertEqual(len(result1), len(result2), "Both search methods should return the same number of rows")
        self.assertGreater(len(result1), 0, "Should find some engineering records")
        
        # Performance comparison
        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"Speedup factor: {speedup:.2f}x")
        print()
    
    def test_search_numeric_value(self):
        """Test searching for a numeric value."""
        print("=" * 60)
        print("TEST 3: Search for numeric value '12345'")
        print("=" * 60)
        
        # Test regular search
        result1, time1 = self.measure_search_performance(
            search, "12345", "Regular search function"
        )
        
        # Test optimized search
        result2, time2 = self.measure_search_performance(
            search_optimized, "12345", "Optimized search function"
        )
        
        # Verify results
        self.assertEqual(len(result1), len(result2), "Both search methods should return the same number of rows")
        
        # Performance comparison
        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"Speedup factor: {speedup:.2f}x")
        print()
    
    def test_search_rare_pattern(self):
        """Test searching for a rare pattern."""
        print("=" * 60)
        print("TEST 4: Search for rare pattern 'XYZ999'")
        print("=" * 60)
        
        # Test regular search
        result1, time1 = self.measure_search_performance(
            search, "XYZ999", "Regular search function"
        )
        
        # Test optimized search
        result2, time2 = self.measure_search_performance(
            search_optimized, "XYZ999", "Optimized search function"
        )
        
        # Verify results
        self.assertEqual(len(result1), len(result2), "Both search methods should return the same number of rows")
        
        # Performance comparison
        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"Speedup factor: {speedup:.2f}x")
        print()
    
    def test_search_case_sensitivity(self):
        """Test case-sensitive vs case-insensitive search."""
        print("=" * 60)
        print("TEST 5: Case sensitivity test with 'user'")
        print("=" * 60)
        
        # Case-insensitive search (default)
        result1, time1 = self.measure_search_performance(
            lambda df, text: search(df, text, case_sensitive=False), 
            "user", "Case-insensitive search"
        )
        
        # Case-sensitive search
        result2, time2 = self.measure_search_performance(
            lambda df, text: search(df, text, case_sensitive=True), 
            "user", "Case-sensitive search"
        )
        
        # Case-insensitive should find more results
        self.assertGreaterEqual(len(result1), len(result2), 
                               "Case-insensitive search should find at least as many results")
        print()
    
    def test_memory_efficiency(self):
        """Test memory usage during search operations."""
        print("=" * 60)
        print("TEST 6: Memory efficiency test")
        print("=" * 60)
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Measure memory before search
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform search
        start_time = time.perf_counter()
        result = search_optimized(self.df, "User")
        end_time = time.perf_counter()
        
        # Measure memory after search
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"Memory before search: {memory_before:.2f} MB")
        print(f"Memory after search: {memory_after:.2f} MB")
        print(f"Memory increase: {memory_after - memory_before:.2f} MB")
        print(f"Search time: {end_time - start_time:.4f} seconds")
        print(f"Rows found: {len(result):,}")
        print()


def run_performance_benchmark():
    """Run the performance benchmark."""
    print("DataFrame Search Performance Benchmark")
    print("=" * 60)
    print("Testing search performance on 1 million rows with 20 columns")
    print("=" * 60)
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSearchPerformance)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    # Run the benchmark
    run_performance_benchmark() 