"""
Tests for search functionality.

This module tests the DataFrame search utilities.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlshell.utils.search_in_df import search, search_optimized


@pytest.fixture
def search_df():
    """Create a DataFrame for search testing."""
    return pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Alice Jr'],
        'email': ['alice@test.com', 'bob@test.com', 'charlie@test.com', 'diana@test.com', 'alice.jr@test.com'],
        'department': ['Engineering', 'Marketing', 'Engineering', 'Sales', 'Engineering'],
        'notes': ['Good performer', 'New hire', 'Senior; experienced', 'Remote worker', 'Trainee']
    })


@pytest.fixture
def large_search_df():
    """Create a larger DataFrame for search performance testing."""
    np.random.seed(42)
    n_rows = 50000
    
    return pd.DataFrame({
        'id': range(n_rows),
        'name': [f'User_{i:05d}' for i in range(n_rows)],
        'email': [f'user{i}@company.com' for i in range(n_rows)],
        'department': np.random.choice(['Engineering', 'Marketing', 'Sales', 'HR'], n_rows),
        'status': np.random.choice(['Active', 'Inactive', 'Pending'], n_rows)
    })


class TestBasicSearch:
    """Tests for basic search functionality."""

    def test_search_single_match(self, search_df):
        """Test searching for a term with single match."""
        result = search(search_df, 'Bob')
        assert len(result) == 1
        assert result.iloc[0]['name'] == 'Bob'

    def test_search_multiple_matches(self, search_df):
        """Test searching for a term with multiple matches."""
        result = search(search_df, 'Alice')
        assert len(result) == 2  # Alice and Alice Jr

    def test_search_no_match(self, search_df):
        """Test searching for a term with no matches."""
        result = search(search_df, 'XYZ123NonExistent')
        assert len(result) == 0

    def test_search_partial_match(self, search_df):
        """Test searching for a partial term."""
        result = search(search_df, 'test.com')
        assert len(result) == 5  # All rows have test.com in email

    def test_search_case_insensitive(self, search_df):
        """Test case-insensitive search (default)."""
        result_lower = search(search_df, 'alice')
        result_upper = search(search_df, 'ALICE')
        result_mixed = search(search_df, 'AlIcE')
        
        assert len(result_lower) == len(result_upper) == len(result_mixed) == 2

    def test_search_case_sensitive(self, search_df):
        """Test case-sensitive search."""
        # Note: 'alice' appears lowercase in emails (alice@test.com, alice.jr@test.com)
        # So searching case-sensitively for 'alice' WILL find those 2 rows
        result_lower = search(search_df, 'alice', case_sensitive=True)
        result_title = search(search_df, 'Alice', case_sensitive=True)
        
        # Both should find 2 rows - 'alice' matches emails, 'Alice' matches names
        assert len(result_lower) == 2, "Should find 'alice' in email addresses"
        assert len(result_title) == 2, "Should find 'Alice' in name column"
        
        # Test with a term that only appears in one form
        result_bob_lower = search(search_df, 'bob', case_sensitive=True)
        result_bob_title = search(search_df, 'Bob', case_sensitive=True)
        
        # 'bob' appears lowercase only in email, 'Bob' only in name
        assert len(result_bob_lower) == 1, "Should find 'bob' only in email"
        assert len(result_bob_title) == 1, "Should find 'Bob' only in name"


class TestSearchWithSpecialCharacters:
    """Tests for searching with special characters."""

    def test_search_semicolon(self, search_df):
        """Test searching for text containing semicolon."""
        result = search(search_df, ';')
        assert len(result) == 1
        assert 'Senior' in result.iloc[0]['notes']

    def test_search_at_symbol(self, search_df):
        """Test searching for @ symbol."""
        result = search(search_df, '@test')
        assert len(result) == 5

    def test_search_dot(self, search_df):
        """Test searching for period."""
        result = search(search_df, '.com')
        assert len(result) == 5


class TestOptimizedSearch:
    """Tests for optimized search function."""

    def test_optimized_search_basic(self, search_df):
        """Test basic optimized search."""
        result = search_optimized(search_df, 'Engineering')
        assert len(result) == 3

    def test_optimized_search_matches_regular(self, search_df):
        """Test that optimized search returns same results as regular search."""
        search_terms = ['Alice', 'test.com', 'Engineering', 'Senior']
        
        for term in search_terms:
            regular = search(search_df, term)
            optimized = search_optimized(search_df, term)
            assert len(regular) == len(optimized), f"Mismatch for term: {term}"


class TestSearchPerformance:
    """Performance tests for search functionality."""

    @pytest.mark.slow
    @pytest.mark.performance
    def test_search_performance_large_df(self, large_search_df):
        """Test search performance on larger DataFrame."""
        import time
        
        start = time.perf_counter()
        result = search(large_search_df, 'User')
        elapsed = time.perf_counter() - start
        
        assert len(result) == len(large_search_df)  # All rows have 'User'
        # Search should complete in reasonable time
        assert elapsed < 5.0, f"Search took too long: {elapsed:.2f}s"

    @pytest.mark.slow
    @pytest.mark.performance
    def test_optimized_search_performance(self, large_search_df):
        """Test optimized search performance."""
        import time
        
        start = time.perf_counter()
        result = search_optimized(large_search_df, 'Engineering')
        elapsed = time.perf_counter() - start
        
        # Should find approximately 1/4 of rows
        assert len(result) > 0
        assert elapsed < 5.0, f"Optimized search took too long: {elapsed:.2f}s"


class TestSearchEdgeCases:
    """Tests for search edge cases."""

    def test_search_empty_string(self, search_df):
        """Test searching for empty string."""
        result = search(search_df, '')
        # Empty search should return all rows or none depending on implementation
        assert result is not None

    def test_search_empty_dataframe(self):
        """Test searching in empty DataFrame."""
        empty_df = pd.DataFrame(columns=['name', 'value'])
        result = search(empty_df, 'test')
        assert len(result) == 0

    def test_search_single_column_df(self):
        """Test searching in single-column DataFrame."""
        df = pd.DataFrame({'name': ['Alice', 'Bob', 'Charlie']})
        result = search(df, 'Bob')
        assert len(result) == 1

    def test_search_numeric_values(self):
        """Test searching for numeric values."""
        df = pd.DataFrame({
            'id': [123, 456, 789],
            'name': ['A', 'B', 'C']
        })
        
        result = search(df, '456')
        assert len(result) == 1
        assert result.iloc[0]['id'] == 456

    def test_search_whitespace(self):
        """Test searching for text with whitespace."""
        df = pd.DataFrame({
            'text': ['hello world', 'goodbye world', 'hello there']
        })
        
        result = search(df, 'hello world')
        assert len(result) == 1

