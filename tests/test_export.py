"""
Tests for export functionality.

This module tests the ExportManager and data export capabilities.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path


@pytest.fixture
def export_manager(db_manager):
    """Create an ExportManager instance with a database manager."""
    from sqlshell.db.export_manager import ExportManager
    return ExportManager(db_manager)


@pytest.fixture
def export_df():
    """Create a DataFrame for export testing."""
    return pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
        'value': [100.5, 200.75, 300.25, 400.0, 500.5],
        'active': [True, False, True, True, False]
    })


class TestExportToCSV:
    """Tests for CSV export functionality using pandas directly."""

    def test_export_csv_basic(self, export_df, temp_dir):
        """Test basic CSV export using pandas."""
        output_path = temp_dir / "output.csv"
        export_df.to_csv(output_path, index=False)
        
        assert output_path.exists()
        
        # Verify content
        loaded = pd.read_csv(output_path)
        assert len(loaded) == len(export_df)
        assert list(loaded.columns) == list(export_df.columns)

    def test_export_csv_with_index(self, export_df, temp_dir):
        """Test CSV export with index."""
        output_path = temp_dir / "output_idx.csv"
        export_df.to_csv(output_path, index=True)
        
        loaded = pd.read_csv(output_path)
        # Index column should be present (Unnamed: 0)
        assert len(loaded.columns) == len(export_df.columns) + 1

    def test_export_csv_custom_separator(self, export_df, temp_dir):
        """Test CSV export with custom separator."""
        output_path = temp_dir / "output.tsv"
        export_df.to_csv(output_path, index=False, sep='\t')
        
        loaded = pd.read_csv(output_path, sep='\t')
        assert len(loaded) == len(export_df)


class TestExportToExcel:
    """Tests for Excel export functionality."""

    def test_export_excel_basic(self, export_manager, export_df, temp_dir):
        """Test basic Excel export using ExportManager."""
        output_path = temp_dir / "output.xlsx"
        table_name, metadata = export_manager.export_to_excel(export_df, str(output_path))
        
        assert output_path.exists()
        assert table_name is not None
        assert metadata['row_count'] == len(export_df)
        
        loaded = pd.read_excel(output_path)
        assert len(loaded) == len(export_df)

    def test_export_excel_with_sheet_name(self, export_df, temp_dir):
        """Test Excel export with custom sheet name using pandas."""
        output_path = temp_dir / "output.xlsx"
        export_df.to_excel(output_path, sheet_name="MyData", index=False)
        
        loaded = pd.read_excel(output_path, sheet_name="MyData")
        assert len(loaded) == len(export_df)


class TestExportToParquet:
    """Tests for Parquet export functionality."""

    def test_export_parquet_basic(self, export_manager, export_df, temp_dir):
        """Test basic Parquet export using ExportManager."""
        output_path = temp_dir / "output.parquet"
        table_name, metadata = export_manager.export_to_parquet(export_df, str(output_path))
        
        assert output_path.exists()
        assert table_name is not None
        assert metadata['row_count'] == len(export_df)
        
        loaded = pd.read_parquet(output_path)
        assert len(loaded) == len(export_df)
        assert list(loaded.columns) == list(export_df.columns)

    def test_export_parquet_preserves_types(self, export_df, temp_dir):
        """Test that Parquet export preserves data types."""
        output_path = temp_dir / "output.parquet"
        export_df.to_parquet(output_path, index=False)
        
        loaded = pd.read_parquet(output_path)
        
        # Check that types are preserved
        assert loaded['id'].dtype == export_df['id'].dtype
        assert loaded['active'].dtype == export_df['active'].dtype


class TestExportEdgeCases:
    """Tests for export edge cases."""

    def test_export_empty_dataframe(self, temp_dir):
        """Test exporting an empty DataFrame."""
        empty_df = pd.DataFrame(columns=['a', 'b', 'c'])
        output_path = temp_dir / "empty.csv"
        
        empty_df.to_csv(output_path, index=False)
        
        loaded = pd.read_csv(output_path)
        assert len(loaded) == 0
        assert list(loaded.columns) == ['a', 'b', 'c']

    def test_export_with_nulls(self, temp_dir, df_with_nulls):
        """Test exporting DataFrame with null values."""
        output_path = temp_dir / "nulls.csv"
        df_with_nulls.to_csv(output_path, index=False)
        
        loaded = pd.read_csv(output_path)
        assert loaded['name'].isna().sum() == 2

    def test_export_large_dataframe(self, export_manager, temp_dir, large_sample_df):
        """Test exporting a large DataFrame using ExportManager."""
        output_path = temp_dir / "large.parquet"
        table_name, metadata = export_manager.export_to_parquet(large_sample_df, str(output_path))
        
        loaded = pd.read_parquet(output_path)
        assert len(loaded) == len(large_sample_df)

    def test_export_special_characters(self, temp_dir):
        """Test exporting data with special characters."""
        df = pd.DataFrame({
            'name': ["O'Brien", 'Test "quoted"', 'Line\nBreak'],
            'value': [1, 2, 3]
        })
        
        output_path = temp_dir / "special.csv"
        df.to_csv(output_path, index=False)
        
        loaded = pd.read_csv(output_path)
        assert len(loaded) == 3

