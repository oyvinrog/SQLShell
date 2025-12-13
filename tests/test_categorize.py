"""
Tests for the Categorize feature.

Tests include:
- Numerical binning with different methods
- Categorical grouping
- Auto-detection
- Edge cases
- Integration with visualization
"""

import pytest
import pandas as pd
import numpy as np
import warnings

from sqlshell.utils.profile_categorize import (
    categorize_numerical,
    categorize_categorical,
    auto_categorize,
    _detect_column_type,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def numerical_df():
    """DataFrame with numerical column for binning."""
    np.random.seed(42)
    return pd.DataFrame({
        'id': range(100),
        'age': np.random.randint(18, 80, 100),
        'salary': np.random.uniform(30000, 150000, 100)
    })


@pytest.fixture
def categorical_df():
    """DataFrame with high-cardinality categorical column."""
    countries = (
        ['USA'] * 30 +
        ['UK'] * 20 +
        ['Canada'] * 15 +
        ['Germany'] * 10 +
        ['France'] * 8 +
        ['Spain'] * 5 +
        ['Italy'] * 4 +
        ['Japan'] * 3 +
        ['China'] * 3 +
        ['India'] * 2
    )
    return pd.DataFrame({
        'id': range(len(countries)),
        'country': countries
    })


@pytest.fixture
def edge_case_df():
    """DataFrame with edge cases."""
    return pd.DataFrame({
        'all_nulls': [None] * 10,
        'single_value': [42] * 10,
        'two_values': [1, 2] * 5,
        'with_nulls': [1, 2, None, 4, 5, None, 7, 8, None, 10]
    })


# ============================================================================
# Tests for Column Type Detection
# ============================================================================

class TestColumnTypeDetection:
    """Test column type detection."""

    def test_detects_integer_as_numerical(self, numerical_df):
        """Test that integer columns are detected as numerical."""
        col_type = _detect_column_type(numerical_df['age'])
        assert col_type == 'numerical'

    def test_detects_float_as_numerical(self, numerical_df):
        """Test that float columns are detected as numerical."""
        col_type = _detect_column_type(numerical_df['salary'])
        assert col_type == 'numerical'

    def test_detects_string_as_categorical(self, categorical_df):
        """Test that string columns are detected as categorical."""
        col_type = _detect_column_type(categorical_df['country'])
        assert col_type == 'categorical'

    def test_detects_few_unique_numeric_as_categorical(self):
        """Test that numeric columns with few unique values are detected as categorical."""
        df = pd.DataFrame({'category': [1, 2, 3, 1, 2, 3] * 20})
        col_type = _detect_column_type(df['category'])
        # Should be categorical due to low unique/total ratio
        assert col_type == 'categorical'


# ============================================================================
# Tests for Numerical Binning
# ============================================================================

class TestNumericalBinning:
    """Test binning of numerical columns."""

    def test_quantile_binning_default(self, numerical_df):
        """Test default quantile binning with 5 bins."""
        result = categorize_numerical(numerical_df, 'age')
        assert 'age_binned' in result.columns
        assert result['age_binned'].nunique() <= 5
        # Check all original rows preserved
        assert len(result) == len(numerical_df)

    def test_equal_width_binning(self, numerical_df):
        """Test equal-width binning."""
        result = categorize_numerical(numerical_df, 'age', method='equal_width', n_bins=4)
        assert 'age_binned' in result.columns
        assert result['age_binned'].nunique() <= 4

    def test_jenks_binning(self, numerical_df):
        """Test Jenks natural breaks."""
        result = categorize_numerical(numerical_df, 'salary', method='jenks', n_bins=5)
        assert 'salary_binned' in result.columns

    def test_auto_method_selection(self, numerical_df):
        """Test automatic method selection."""
        result = categorize_numerical(numerical_df, 'age', method='auto')
        assert 'age_binned' in result.columns

    def test_custom_bin_count(self, numerical_df):
        """Test custom number of bins."""
        for n_bins in [3, 7, 10]:
            result = categorize_numerical(numerical_df, 'age', n_bins=n_bins)
            unique_bins = result['age_binned'].nunique()
            # Should be <= n_bins (could be less due to min_bin_size)
            assert unique_bins <= n_bins

    def test_bin_labels_are_strings(self, numerical_df):
        """Test that bin labels are strings."""
        result = categorize_numerical(numerical_df, 'age')
        sample_label = result['age_binned'].iloc[0]
        assert isinstance(sample_label, str)

    def test_preserves_original_column(self, numerical_df):
        """Test that original column is preserved."""
        result = categorize_numerical(numerical_df, 'age')
        assert 'age' in result.columns
        assert 'age_binned' in result.columns
        # Original values unchanged
        pd.testing.assert_series_equal(result['age'], numerical_df['age'])

    def test_handles_nulls_in_data(self):
        """Test that NaN values are handled properly."""
        df = pd.DataFrame({'val': [1, 2, None, 4, 5, None, 7, 8, None, 10]})
        result = categorize_numerical(df, 'val')
        # NaN should be labeled as "Missing"
        assert 'Missing' in result['val_binned'].values
        # All values should have a label
        assert result['val_binned'].notna().all()


# ============================================================================
# Tests for Categorical Grouping
# ============================================================================

class TestCategoricalGrouping:
    """Test grouping of categorical columns."""

    def test_top_5_grouping_default(self, categorical_df):
        """Test default top-5 grouping."""
        result = categorize_categorical(categorical_df, 'country')
        assert 'country_grouped' in result.columns
        # Should have 6 categories: top 5 + "Other"
        unique_vals = result['country_grouped'].unique()
        assert len(unique_vals) <= 6
        assert 'Other' in unique_vals

    def test_custom_top_n(self, categorical_df):
        """Test custom top-N grouping."""
        for top_n in [3, 7, 10]:
            result = categorize_categorical(categorical_df, 'country', top_n=top_n)
            unique_vals = result['country_grouped'].unique()
            # top_n + "Other" (or less if fewer unique values)
            assert len(unique_vals) <= top_n + 1

    def test_no_other_when_few_categories(self):
        """Test that 'Other' is not created when categories <= top_n."""
        df = pd.DataFrame({'category': ['A', 'B', 'C'] * 10})
        result = categorize_categorical(df, 'category', top_n=5)
        # Only 3 categories, all should be kept
        assert 'Other' not in result['category_grouped'].values

    def test_frequency_based_selection(self, categorical_df):
        """Test that most frequent categories are selected."""
        result = categorize_categorical(categorical_df, 'country', top_n=3)
        top_3 = categorical_df['country'].value_counts().head(3).index.tolist()
        kept_categories = result['country_grouped'].unique()
        # All top 3 should be in kept categories
        for cat in top_3:
            assert cat in kept_categories

    def test_preserves_original_column(self, categorical_df):
        """Test that original column is preserved."""
        result = categorize_categorical(categorical_df, 'country')
        assert 'country' in result.columns
        assert 'country_grouped' in result.columns
        pd.testing.assert_series_equal(result['country'], categorical_df['country'])

    def test_handles_null_values(self):
        """Test handling of null values in categorical data."""
        df = pd.DataFrame({'cat': ['A', 'B', None, 'C', 'A', None, 'B']})
        result = categorize_categorical(df, 'cat', top_n=2)
        # Nulls should be labeled as "Missing"
        assert 'Missing' in result['cat_grouped'].values


# ============================================================================
# Tests for Auto-Detection
# ============================================================================

class TestAutoDetection:
    """Test automatic detection of column type."""

    def test_detects_numerical(self, numerical_df):
        """Test auto-detection of numerical columns."""
        result, cat_type = auto_categorize(numerical_df, 'age')
        assert cat_type == 'binned'
        assert 'age_binned' in result.columns

    def test_detects_categorical(self, categorical_df):
        """Test auto-detection of categorical columns."""
        result, cat_type = auto_categorize(categorical_df, 'country')
        assert cat_type == 'grouped'
        assert 'country_grouped' in result.columns

    def test_respects_kwargs_for_numerical(self, numerical_df):
        """Test that kwargs are passed to numerical categorization."""
        result, cat_type = auto_categorize(numerical_df, 'age', n_bins=3)
        assert cat_type == 'binned'
        assert result['age_binned'].nunique() <= 3

    def test_respects_kwargs_for_categorical(self, categorical_df):
        """Test that kwargs are passed to categorical categorization."""
        result, cat_type = auto_categorize(categorical_df, 'country', top_n=3)
        assert cat_type == 'grouped'
        # Should have at most 4 categories (top 3 + "Other" + possibly "Missing")
        assert result['country_grouped'].nunique() <= 4


# ============================================================================
# Tests for Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_all_nulls_raises_warning(self, edge_case_df):
        """Test handling of all-null columns."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = categorize_numerical(edge_case_df, 'all_nulls')
            # Should have warning
            assert len(w) > 0
            # Result should have "Missing" label
            assert 'Missing' in result['all_nulls_binned'].values

    def test_single_unique_value(self, edge_case_df):
        """Test handling of single unique value."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = categorize_numerical(edge_case_df, 'single_value')
            # Should have warning
            assert len(w) > 0
            # Should create single category
            assert result['single_value_binned'].nunique() == 1

    def test_too_many_bins_requested(self):
        """Test requesting more bins than unique values."""
        # Column with only 3 unique values
        df = pd.DataFrame({'val': [1, 2, 3] * 10})
        result = categorize_numerical(df, 'val', n_bins=10)
        # Should auto-reduce to <= 3 bins
        assert result['val_binned'].nunique() <= 3

    def test_empty_dataframe(self):
        """Test handling of empty dataframe."""
        df = pd.DataFrame({'col': []})
        with pytest.raises(ValueError):
            categorize_numerical(df, 'col')

    def test_column_not_found_numerical(self, numerical_df):
        """Test error when column doesn't exist."""
        with pytest.raises(KeyError):
            categorize_numerical(numerical_df, 'nonexistent_column')

    def test_column_not_found_categorical(self, categorical_df):
        """Test error when column doesn't exist."""
        with pytest.raises(KeyError):
            categorize_categorical(categorical_df, 'nonexistent_column')

    def test_column_not_found_auto(self, numerical_df):
        """Test error when column doesn't exist in auto mode."""
        with pytest.raises(KeyError):
            auto_categorize(numerical_df, 'nonexistent_column')


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the complete workflow."""

    def test_binning_preserves_dataframe_integrity(self, numerical_df):
        """Test that binning doesn't corrupt dataframe."""
        result = categorize_numerical(numerical_df, 'age')
        # Same number of rows
        assert len(result) == len(numerical_df)
        # All original columns present
        for col in numerical_df.columns:
            assert col in result.columns
        # New column added
        assert 'age_binned' in result.columns

    def test_grouping_preserves_dataframe_integrity(self, categorical_df):
        """Test that grouping doesn't corrupt dataframe."""
        result = categorize_categorical(categorical_df, 'country')
        assert len(result) == len(categorical_df)
        for col in categorical_df.columns:
            assert col in result.columns
        assert 'country_grouped' in result.columns

    def test_multiple_categorizations(self, numerical_df):
        """Test applying multiple categorizations."""
        result = categorize_numerical(numerical_df, 'age')
        result = categorize_numerical(result, 'salary')
        assert 'age_binned' in result.columns
        assert 'salary_binned' in result.columns
        assert len(result) == len(numerical_df)

    def test_mixed_numerical_and_categorical(self):
        """Test categorizing both numerical and categorical columns."""
        df = pd.DataFrame({
            'age': range(20, 70, 5),
            'country': ['USA', 'UK', 'Canada'] * 3 + ['Germany']
        })
        result1 = categorize_numerical(df, 'age', n_bins=3)
        result2 = categorize_categorical(result1, 'country', top_n=2)
        assert 'age_binned' in result2.columns
        assert 'country_grouped' in result2.columns
        assert len(result2) == len(df)

    def test_large_dataframe_performance(self):
        """Test performance with larger dataframe."""
        np.random.seed(42)
        df = pd.DataFrame({
            'value': np.random.randn(10000)
        })
        # Should complete without error
        result = categorize_numerical(df, 'value', n_bins=5)
        assert len(result) == 10000
        assert 'value_binned' in result.columns

    def test_auto_categorize_returns_correct_tuple(self, numerical_df):
        """Test that auto_categorize returns (df, type) tuple."""
        result, cat_type = auto_categorize(numerical_df, 'age')
        assert isinstance(result, pd.DataFrame)
        assert cat_type in ['binned', 'grouped']
        assert len(result) == len(numerical_df)


# ============================================================================
# Tests for Specific Binning Methods
# ============================================================================

class TestBinningMethods:
    """Test specific binning methods."""

    def test_quantile_prevents_empty_bins(self):
        """Test that quantile binning prevents empty bins."""
        np.random.seed(42)
        # Skewed data with outliers
        df = pd.DataFrame({
            'skewed': np.concatenate([
                np.random.normal(10, 1, 90),
                np.random.normal(100, 5, 10)
            ])
        })
        result = categorize_numerical(df, 'skewed', method='quantile', n_bins=5)
        # Should have bins with roughly equal counts
        counts = result['skewed_binned'].value_counts()
        # No bin should be empty
        assert all(counts > 0)

    def test_freedman_diaconis_method(self, numerical_df):
        """Test Freedman-Diaconis binning method."""
        result = categorize_numerical(numerical_df, 'age', method='freedman_diaconis')
        assert 'age_binned' in result.columns
        # Should create some reasonable number of bins
        assert 2 <= result['age_binned'].nunique() <= 10

    def test_sturges_method(self, numerical_df):
        """Test Sturges' rule binning method."""
        result = categorize_numerical(numerical_df, 'age', method='sturges')
        assert 'age_binned' in result.columns
        # Sturges: k = 1 + log2(n), for n=100, k ≈ 8
        assert 2 <= result['age_binned'].nunique() <= 10


# ============================================================================
# Tests for Custom Parameters
# ============================================================================

class TestCustomParameters:
    """Test custom parameter handling."""

    def test_custom_other_label(self, categorical_df):
        """Test custom 'Other' label for categorical grouping."""
        result = categorize_categorical(categorical_df, 'country', top_n=3, other_label='Rest')
        assert 'Rest' in result['country_grouped'].values
        assert 'Other' not in result['country_grouped'].values

    def test_min_bin_size_parameter(self):
        """Test min_bin_size parameter."""
        df = pd.DataFrame({'val': [1, 2, 3, 4, 5, 100, 101, 102, 103, 104]})
        # With high min_bin_size, bins may be merged
        result = categorize_numerical(df, 'val', n_bins=5, min_bin_size=3)
        assert 'val_binned' in result.columns
        # Number of bins might be reduced due to min_bin_size
        assert result['val_binned'].nunique() <= 5
