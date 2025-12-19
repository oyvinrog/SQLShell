"""
Tests for DataFrame search performance.

This module contains two types of tests:
1. Quick functional tests (using 10k rows) - run with normal test suite
2. Full benchmark tests (using 1M rows) - marked as 'slow' and 'performance'

To run only quick tests: pytest -m "not slow"
To run full benchmarks: pytest -m "slow" tests/test_search_performance.py
"""

import pandas as pd
import numpy as np
import time
import pytest
import sys
import os

# Add the parent directory to the path to import the search module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlshell.utils.search_in_df import search, search_optimized


# ==============================================================================
# Fixtures for test data
# ==============================================================================

def create_test_dataframe(n_rows: int, n_cols: int = 20):
    """Create a test DataFrame with specified number of rows.
    
    Args:
        n_rows: Number of rows to generate
        n_cols: Number of columns (default 20)
    
    Returns:
        Tuple of (DataFrame, n_rows)
    """
    np.random.seed(42)
    
    data = {}
    
    # String columns with various patterns
    data['name'] = [f"User_{i:06d}" for i in range(n_rows)]
    data['email'] = [f"user{i}@{'company' if i % 3 == 0 else 'personal'}.com" for i in range(n_rows)]
    data['city'] = np.random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia'], n_rows)
    data['department'] = np.random.choice(['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Operations'], n_rows)
    data['status'] = np.random.choice(['Active', 'Inactive', 'Pending', 'Suspended'], n_rows)
    
    # Numeric columns
    data['age'] = np.random.randint(18, 80, n_rows)
    data['salary'] = np.random.randint(30000, 200000, n_rows)
    data['employee_id'] = range(n_rows)
    data['score'] = np.random.uniform(0, 100, n_rows).round(2)
    data['rating'] = np.random.uniform(1, 5, n_rows).round(1)
    
    # Mixed columns
    data['product_code'] = [f"PRD-{np.random.randint(1000, 9999)}-{chr(65 + i % 26)}" for i in range(n_rows)]
    data['description'] = [f"Product description for item {i} with various features" for i in range(n_rows)]
    data['notes'] = [f"Important notes about record {i}" if i % 10 == 0 else "" for i in range(n_rows)]
    
    # Date-like strings (use 'h' instead of deprecated 'H')
    data['join_date'] = pd.date_range('2020-01-01', periods=n_rows, freq='1h').strftime('%Y-%m-%d')
    data['last_login'] = pd.date_range('2023-01-01', periods=n_rows, freq='2h').strftime('%Y-%m-%d %H:%M:%S')
    
    # Fill remaining columns with random data
    for i in range(15, n_cols):
        col_name = f'column_{i}'
        if i % 3 == 0:
            data[col_name] = np.random.choice(['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon'], n_rows)
        elif i % 3 == 1:
            data[col_name] = np.random.randint(0, 1000, n_rows)
        else:
            data[col_name] = [f"Value_{j}_{i}" for j in range(n_rows)]
    
    return pd.DataFrame(data), n_rows


@pytest.fixture(scope="module")
def small_df():
    """Create a small DataFrame for quick functional tests (10k rows)."""
    return create_test_dataframe(10_000)


@pytest.fixture(scope="module")
def large_df():
    """Create a large DataFrame for performance tests (50k rows).
    
    Reduced from 1M rows for faster test execution while still testing
    performance characteristics. For full benchmarks, modify this value.
    """
    return create_test_dataframe(50_000)


# ==============================================================================
# Quick Functional Tests (using 10k rows) - Run with normal test suite
# ==============================================================================

class TestSearchFunctionality:
    """Quick functional tests for search functions using smaller dataset."""
    
    def test_search_common_word(self, small_df):
        """Test searching for a common word returns expected results."""
        df, n_rows = small_df
        
        result1 = search(df, "User")
        result2 = search_optimized(df, "User")
        
        # Both methods should return the same results
        assert len(result1) == len(result2), "Both search methods should return the same number of rows"
        assert len(result1) > 0, "Should find matches for 'User'"
    
    def test_search_specific_pattern(self, small_df):
        """Test searching for a specific pattern."""
        df, n_rows = small_df
        
        result1 = search(df, "Engineering")
        result2 = search_optimized(df, "Engineering")
        
        assert len(result1) == len(result2), "Both search methods should return the same number of rows"
        assert len(result1) > 0, "Should find some engineering records"
    
    def test_search_numeric_value(self, small_df):
        """Test searching for a numeric value."""
        df, n_rows = small_df
        
        result1 = search(df, "12345")
        result2 = search_optimized(df, "12345")
        
        assert len(result1) == len(result2), "Both search methods should return the same number of rows"
    
    def test_search_rare_pattern(self, small_df):
        """Test searching for a rare pattern."""
        df, n_rows = small_df
        
        result1 = search(df, "XYZ999")
        result2 = search_optimized(df, "XYZ999")
        
        assert len(result1) == len(result2), "Both search methods should return the same number of rows"
    
    def test_search_case_sensitivity(self, small_df):
        """Test case-sensitive vs case-insensitive search."""
        df, n_rows = small_df
        
        result_insensitive = search(df, "user", case_sensitive=False)
        result_sensitive = search(df, "user", case_sensitive=True)
        
        # Case-insensitive should find more results (or equal)
        assert len(result_insensitive) >= len(result_sensitive), \
            "Case-insensitive search should find at least as many results"


# ==============================================================================
# Full Benchmark Tests (using 1M rows) - Marked as slow/performance
# ==============================================================================

@pytest.mark.slow
@pytest.mark.performance
class TestSearchPerformance:
    """Performance tests using 50k row dataset.
    
    These tests are marked as 'slow' and 'performance' and are skipped by default.
    Run with: pytest -m slow tests/test_search_performance.py
    
    Note: Dataset size reduced from 1M to 50k rows for faster execution while
    still testing performance characteristics. For full benchmarks, modify
    the large_df fixture.
    """
    
    @staticmethod
    def measure_search_performance(df, n_rows, search_func, search_text, description):
        """Measure performance of a search function."""
        print(f"Testing {description}")
        print(f"Search text: '{search_text}'")
        
        start_time = time.perf_counter()
        result = search_func(df, search_text)
        end_time = time.perf_counter()
        
        elapsed_time = end_time - start_time
        rows_found = len(result)
        
        print(f"Time taken: {elapsed_time:.4f} seconds")
        print(f"Rows found: {rows_found:,}")
        print(f"Performance: {n_rows / elapsed_time:,.0f} rows/second")
        print("-" * 50)
        
        return result, elapsed_time
    
    def test_search_common_word(self, large_df):
        """Benchmark searching for a common word on large dataset."""
        df, n_rows = large_df
        
        print("=" * 60)
        print(f"BENCHMARK: Search for common word 'User' on {n_rows:,} rows")
        print("=" * 60)
        
        result1, time1 = self.measure_search_performance(
            df, n_rows, search, "User", "Regular search function"
        )
        result2, time2 = self.measure_search_performance(
            df, n_rows, search_optimized, "User", "Optimized search function"
        )
        
        assert len(result1) == len(result2), "Both search methods should return the same number of rows"
        
        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"Speedup factor: {speedup:.2f}x")
    
    def test_search_specific_pattern(self, large_df):
        """Benchmark searching for a specific pattern on large dataset."""
        df, n_rows = large_df
        
        print("=" * 60)
        print(f"BENCHMARK: Search for pattern 'Engineering' on {n_rows:,} rows")
        print("=" * 60)
        
        result1, time1 = self.measure_search_performance(
            df, n_rows, search, "Engineering", "Regular search function"
        )
        result2, time2 = self.measure_search_performance(
            df, n_rows, search_optimized, "Engineering", "Optimized search function"
        )
        
        assert len(result1) == len(result2), "Both search methods should return the same number of rows"
        assert len(result1) > 0, "Should find some engineering records"
        
        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"Speedup factor: {speedup:.2f}x")
    
    def test_search_numeric_value(self, large_df):
        """Benchmark searching for a numeric value on large dataset."""
        df, n_rows = large_df
        
        print("=" * 60)
        print(f"BENCHMARK: Search for numeric value '12345' on {n_rows:,} rows")
        print("=" * 60)
        
        result1, time1 = self.measure_search_performance(
            df, n_rows, search, "12345", "Regular search function"
        )
        result2, time2 = self.measure_search_performance(
            df, n_rows, search_optimized, "12345", "Optimized search function"
        )
        
        assert len(result1) == len(result2), "Both search methods should return the same number of rows"
        
        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"Speedup factor: {speedup:.2f}x")
    
    def test_search_rare_pattern(self, large_df):
        """Benchmark searching for a rare pattern on large dataset."""
        df, n_rows = large_df
        
        print("=" * 60)
        print(f"BENCHMARK: Search for rare pattern 'XYZ999' on {n_rows:,} rows")
        print("=" * 60)
        
        result1, time1 = self.measure_search_performance(
            df, n_rows, search, "XYZ999", "Regular search function"
        )
        result2, time2 = self.measure_search_performance(
            df, n_rows, search_optimized, "XYZ999", "Optimized search function"
        )
        
        assert len(result1) == len(result2), "Both search methods should return the same number of rows"
        
        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"Speedup factor: {speedup:.2f}x")
    
    def test_search_case_sensitivity(self, large_df):
        """Benchmark case sensitivity performance on large dataset."""
        df, n_rows = large_df
        
        print("=" * 60)
        print(f"BENCHMARK: Case sensitivity test with 'user' on {n_rows:,} rows")
        print("=" * 60)
        
        result1, time1 = self.measure_search_performance(
            df, n_rows,
            lambda df, text: search(df, text, case_sensitive=False),
            "user", "Case-insensitive search"
        )
        result2, time2 = self.measure_search_performance(
            df, n_rows,
            lambda df, text: search(df, text, case_sensitive=True),
            "user", "Case-sensitive search"
        )
        
        assert len(result1) >= len(result2), \
            "Case-insensitive search should find at least as many results"
    
    def test_memory_efficiency(self, large_df):
        """Benchmark memory usage during search operations on large dataset."""
        import psutil
        import os as os_module
        
        df, n_rows = large_df
        
        print("=" * 60)
        print(f"BENCHMARK: Memory efficiency test on {n_rows:,} rows")
        print("=" * 60)
        
        process = psutil.Process(os_module.getpid())
        
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.perf_counter()
        result = search_optimized(df, "User")
        end_time = time.perf_counter()
        
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"Memory before search: {memory_before:.2f} MB")
        print(f"Memory after search: {memory_after:.2f} MB")
        print(f"Memory increase: {memory_after - memory_before:.2f} MB")
        print(f"Search time: {end_time - start_time:.4f} seconds")
        print(f"Rows found: {len(result):,}")


# ==============================================================================
# Standalone benchmark runner
# ==============================================================================

def run_performance_benchmark():
    """Run the full performance benchmark standalone."""
    print("DataFrame Search Performance Benchmark")
    print("=" * 60)
    print("Testing search performance on 1 million rows with 20 columns")
    print("=" * 60)
    print()
    
    print("Creating test dataset...")
    df, n_rows = create_test_dataframe(1_000_000)
    print(f"Dataset shape: {df.shape}")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    print()
    
    # Run benchmarks
    test_instance = TestSearchPerformance()
    test_instance.test_search_common_word((df, n_rows))
    print()
    test_instance.test_search_specific_pattern((df, n_rows))
    print()
    test_instance.test_search_numeric_value((df, n_rows))
    print()
    test_instance.test_search_rare_pattern((df, n_rows))
    print()
    test_instance.test_search_case_sensitivity((df, n_rows))
    print()
    test_instance.test_memory_efficiency((df, n_rows))


if __name__ == '__main__':
    run_performance_benchmark()
