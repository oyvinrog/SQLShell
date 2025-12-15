"""
Tests for clipboard data parsing functionality.

This module tests the ClipboardDataParser utility for detecting and parsing
tabular data from clipboard text.
"""

import pytest
import pandas as pd
import numpy as np

from sqlshell.utils.clipboard_data_parser import ClipboardDataParser


# ==============================================================================
# Test Data Fixtures
# ==============================================================================

@pytest.fixture
def tsv_with_header():
    """Tab-separated values with header row."""
    return """name\tage\tcity
John\t25\tNew York
Jane\t30\tLos Angeles
Bob\t35\tChicago"""


@pytest.fixture
def csv_with_header():
    """Comma-separated values with header row."""
    return """id,product,price
1,Apple,1.50
2,Banana,0.75
3,Orange,2.00"""


@pytest.fixture
def csv_without_header():
    """Comma-separated values without header row (all numeric)."""
    return """1,100,50.5
2,200,75.3
3,300,100.0"""


@pytest.fixture
def tsv_without_header():
    """Tab-separated values without header row."""
    return """1\t100\t50.5
2\t200\t75.3
3\t300\t100.0"""


@pytest.fixture
def semicolon_separated():
    """Semicolon-separated values with header."""
    return """name;value;date
Alice;100;2024-01-01
Bob;200;2024-01-02
Charlie;300;2024-01-03"""


@pytest.fixture
def pipe_separated():
    """Pipe-separated values with header."""
    return """id|name|status
1|Active User|active
2|Inactive User|inactive
3|Pending User|pending"""


@pytest.fixture
def non_tabular_text():
    """Plain text that is not tabular data."""
    return """This is just some regular text.
Not a table at all.
Just random sentences."""


@pytest.fixture
def single_column_data():
    """Data with only one column (should be rejected)."""
    return """apple
banana
cherry
date"""


@pytest.fixture
def empty_text():
    """Empty or whitespace-only text."""
    return "   \n  \n   "


@pytest.fixture
def mixed_types_data():
    """Data with mixed types in columns."""
    return """id,name,score,active
1,Alice,95.5,true
2,Bob,87.3,false
3,Charlie,92.1,true"""


@pytest.fixture
def data_with_nulls():
    """Data with null/empty values."""
    return """name,value,category
Alice,100,A
Bob,,B
,300,
Diana,400,D"""


@pytest.fixture
def quoted_csv():
    """CSV with quoted fields containing commas."""
    return '''name,address,phone
"Smith, John","123 Main St, Apt 4","555-1234"
"Doe, Jane","456 Oak Ave","555-5678"'''


@pytest.fixture
def excel_style_tsv():
    """TSV data as typically copied from Excel."""
    return """Product\tQuantity\tUnit Price\tTotal
Widget A\t10\t$5.99\t$59.90
Widget B\t25\t$3.49\t$87.25
Widget C\t5\t$12.99\t$64.95"""


# ==============================================================================
# Test is_likely_data() function
# ==============================================================================

class TestIsLikelyData:
    """Tests for the is_likely_data() detection function."""

    def test_tsv_is_data(self, tsv_with_header):
        """TSV data should be recognized as likely data."""
        assert ClipboardDataParser.is_likely_data(tsv_with_header) is True

    def test_csv_is_data(self, csv_with_header):
        """CSV data should be recognized as likely data."""
        assert ClipboardDataParser.is_likely_data(csv_with_header) is True

    def test_semicolon_is_data(self, semicolon_separated):
        """Semicolon-separated data should be recognized as likely data."""
        assert ClipboardDataParser.is_likely_data(semicolon_separated) is True

    def test_pipe_is_data(self, pipe_separated):
        """Pipe-separated data should be recognized as likely data."""
        assert ClipboardDataParser.is_likely_data(pipe_separated) is True

    def test_plain_text_not_data(self, non_tabular_text):
        """Plain text should not be recognized as data."""
        assert ClipboardDataParser.is_likely_data(non_tabular_text) is False

    def test_single_column_not_data(self, single_column_data):
        """Single column data should not be recognized as data."""
        assert ClipboardDataParser.is_likely_data(single_column_data) is False

    def test_empty_text_not_data(self, empty_text):
        """Empty text should not be recognized as data."""
        assert ClipboardDataParser.is_likely_data(empty_text) is False

    def test_none_not_data(self):
        """None should not be recognized as data."""
        assert ClipboardDataParser.is_likely_data(None) is False

    def test_empty_string_not_data(self):
        """Empty string should not be recognized as data."""
        assert ClipboardDataParser.is_likely_data("") is False

    def test_single_line_with_tabs_is_data(self):
        """Single line with tabs should be recognized as data."""
        assert ClipboardDataParser.is_likely_data("a\tb\tc") is True

    def test_inconsistent_columns_not_data(self):
        """Data with very inconsistent column counts should not be recognized."""
        inconsistent = """a,b,c,d,e
1,2
x,y,z,w,v,u,t,s"""
        assert ClipboardDataParser.is_likely_data(inconsistent) is False


# ==============================================================================
# Test detect_delimiter() function
# ==============================================================================

class TestDetectDelimiter:
    """Tests for the detect_delimiter() function."""

    def test_detect_tab_delimiter(self, tsv_with_header):
        """Should detect tab as delimiter for TSV data."""
        assert ClipboardDataParser.detect_delimiter(tsv_with_header) == '\t'

    def test_detect_comma_delimiter(self, csv_with_header):
        """Should detect comma as delimiter for CSV data."""
        assert ClipboardDataParser.detect_delimiter(csv_with_header) == ','

    def test_detect_semicolon_delimiter(self, semicolon_separated):
        """Should detect semicolon as delimiter."""
        assert ClipboardDataParser.detect_delimiter(semicolon_separated) == ';'

    def test_detect_pipe_delimiter(self, pipe_separated):
        """Should detect pipe as delimiter."""
        assert ClipboardDataParser.detect_delimiter(pipe_separated) == '|'

    def test_tab_preferred_over_comma(self):
        """Tab should be preferred when both are present and consistent."""
        # This mimics data where column values contain commas
        data = "name\taddress\nJohn\t123 Main, Apt 4\nJane\t456 Oak, Suite 5"
        assert ClipboardDataParser.detect_delimiter(data) == '\t'


# ==============================================================================
# Test detect_header() function
# ==============================================================================

class TestDetectHeader:
    """Tests for the detect_header() function."""

    def test_detect_header_with_text_header(self):
        """Should detect header when first row is text and data is numeric."""
        df = pd.DataFrame([
            ['name', 'age', 'score'],
            ['Alice', '25', '95.5'],
            ['Bob', '30', '87.3']
        ])
        assert ClipboardDataParser.detect_header(df) is True

    def test_detect_no_header_all_numeric(self):
        """Should detect no header when all rows are numeric."""
        df = pd.DataFrame([
            ['1', '100', '50.5'],
            ['2', '200', '75.3'],
            ['3', '300', '100.0']
        ])
        assert ClipboardDataParser.detect_header(df) is False

    def test_detect_header_with_common_patterns(self):
        """Should detect header when first row contains common header patterns."""
        df = pd.DataFrame([
            ['user_id', 'count', 'total_amount'],
            ['1', '5', '100.50'],
            ['2', '3', '75.25']
        ])
        assert ClipboardDataParser.detect_header(df) is True

    def test_single_row_assumes_header(self):
        """Single row data should assume it has header."""
        df = pd.DataFrame([['col1', 'col2', 'col3']])
        assert ClipboardDataParser.detect_header(df) is True


# ==============================================================================
# Test parse_clipboard_data() function
# ==============================================================================

class TestParseClipboardData:
    """Tests for the main parse_clipboard_data() function."""

    def test_parse_tsv_with_header(self, tsv_with_header):
        """Should correctly parse TSV data with header."""
        df, message = ClipboardDataParser.parse_clipboard_data(tsv_with_header)
        
        assert df is not None
        assert len(df) == 3
        assert len(df.columns) == 3
        assert list(df.columns) == ['name', 'age', 'city']
        assert 'tab-separated' in message
        assert 'with header' in message

    def test_parse_csv_with_header(self, csv_with_header):
        """Should correctly parse CSV data with header."""
        df, message = ClipboardDataParser.parse_clipboard_data(csv_with_header)
        
        assert df is not None
        assert len(df) == 3
        assert list(df.columns) == ['id', 'product', 'price']
        assert 'comma-separated' in message

    def test_parse_csv_without_header(self, csv_without_header):
        """Should correctly parse CSV data without header and generate column names."""
        df, message = ClipboardDataParser.parse_clipboard_data(csv_without_header)
        
        assert df is not None
        assert len(df) == 3
        # Should have generated column names
        assert all(col.startswith('column_') for col in df.columns)
        assert 'without header' in message

    def test_parse_tsv_without_header(self, tsv_without_header):
        """Should correctly parse TSV data without header."""
        df, message = ClipboardDataParser.parse_clipboard_data(tsv_without_header)
        
        assert df is not None
        assert len(df) == 3
        assert 'without header' in message

    def test_parse_semicolon_data(self, semicolon_separated):
        """Should correctly parse semicolon-separated data."""
        df, message = ClipboardDataParser.parse_clipboard_data(semicolon_separated)
        
        assert df is not None
        assert len(df) == 3
        assert 'semicolon-separated' in message

    def test_parse_pipe_data(self, pipe_separated):
        """Should correctly parse pipe-separated data."""
        df, message = ClipboardDataParser.parse_clipboard_data(pipe_separated)
        
        assert df is not None
        assert len(df) == 3
        assert 'pipe-separated' in message

    def test_parse_empty_returns_none(self, empty_text):
        """Should return None for empty text."""
        df, message = ClipboardDataParser.parse_clipboard_data(empty_text)
        assert df is None

    def test_parse_non_tabular_returns_none(self, non_tabular_text):
        """Should return None for non-tabular text."""
        df, message = ClipboardDataParser.parse_clipboard_data(non_tabular_text)
        assert df is None
        assert "doesn't appear to be tabular" in message

    def test_parse_preserves_numeric_types(self, csv_with_header):
        """Numeric values should be converted to numeric types."""
        df, _ = ClipboardDataParser.parse_clipboard_data(csv_with_header)
        
        assert df is not None
        assert pd.api.types.is_numeric_dtype(df['id'])
        assert pd.api.types.is_numeric_dtype(df['price'])

    def test_parse_mixed_types(self, mixed_types_data):
        """Should handle data with mixed types in columns."""
        df, _ = ClipboardDataParser.parse_clipboard_data(mixed_types_data)
        
        assert df is not None
        assert len(df) == 3
        # id and score should be numeric
        assert pd.api.types.is_numeric_dtype(df['id'])
        assert pd.api.types.is_numeric_dtype(df['score'])

    def test_parse_data_with_nulls(self, data_with_nulls):
        """Should handle data with null/empty values."""
        df, _ = ClipboardDataParser.parse_clipboard_data(data_with_nulls)
        
        assert df is not None
        assert df['value'].isna().sum() == 1
        assert df['name'].isna().sum() == 1

    def test_parse_excel_style_data(self, excel_style_tsv):
        """Should parse data copied from Excel correctly."""
        df, message = ClipboardDataParser.parse_clipboard_data(excel_style_tsv)
        
        assert df is not None
        assert len(df) == 3
        assert 'tab-separated' in message
        assert 'Product' in df.columns

    def test_parse_returns_row_column_count_in_message(self, csv_with_header):
        """Message should contain row and column counts."""
        df, message = ClipboardDataParser.parse_clipboard_data(csv_with_header)
        
        assert '3 rows' in message
        assert '3 columns' in message


# ==============================================================================
# Test get_data_preview() function
# ==============================================================================

class TestGetDataPreview:
    """Tests for the get_data_preview() function."""

    def test_preview_basic(self, csv_with_header):
        """Should return a string preview of the data."""
        df, _ = ClipboardDataParser.parse_clipboard_data(csv_with_header)
        preview = ClipboardDataParser.get_data_preview(df)
        
        assert isinstance(preview, str)
        assert 'Apple' in preview
        assert 'Banana' in preview

    def test_preview_limits_rows(self):
        """Should limit rows in preview."""
        df = pd.DataFrame({
            'a': range(100),
            'b': range(100, 200)
        })
        preview = ClipboardDataParser.get_data_preview(df, max_rows=3)
        
        # Should only have first 3 values
        assert '0' in preview
        assert '1' in preview
        assert '2' in preview
        # Should not have later values
        assert '99' not in preview

    def test_preview_empty_df(self):
        """Should handle empty DataFrame."""
        preview = ClipboardDataParser.get_data_preview(None)
        assert preview == "No data"

    def test_preview_empty_dataframe(self):
        """Should handle empty DataFrame object."""
        df = pd.DataFrame()
        preview = ClipboardDataParser.get_data_preview(df)
        assert preview == "No data"


# ==============================================================================
# Test Edge Cases
# ==============================================================================

class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_unicode_data(self):
        """Should handle Unicode characters in data."""
        unicode_data = """name,city,country
José,São Paulo,Brasil
北京,Beijing,中国
München,Munich,Deutschland"""
        
        df, _ = ClipboardDataParser.parse_clipboard_data(unicode_data)
        
        assert df is not None
        assert len(df) == 3
        assert 'José' in df['name'].values

    def test_large_data(self):
        """Should handle larger datasets."""
        # Generate 1000 rows of data
        rows = ["id,value,category"]
        for i in range(1000):
            rows.append(f"{i},{i*10},cat_{i%5}")
        large_data = "\n".join(rows)
        
        df, message = ClipboardDataParser.parse_clipboard_data(large_data)
        
        assert df is not None
        assert len(df) == 1000
        assert '1000 rows' in message

    def test_whitespace_in_values(self):
        """Should preserve whitespace in values."""
        data = """name,description
Alice,This is a test
Bob,Another  test  with  spaces"""
        
        df, _ = ClipboardDataParser.parse_clipboard_data(data)
        
        assert df is not None
        assert 'Another  test  with  spaces' in df['description'].values

    def test_numeric_strings_as_text(self):
        """Should handle numeric strings that should stay as text."""
        data = """zip_code,phone,id
02134,555-1234,001
10001,555-5678,002"""
        
        df, _ = ClipboardDataParser.parse_clipboard_data(data)
        
        assert df is not None
        # These should be parsed, and id should be recognized as numeric
        assert len(df) == 2

    def test_windows_line_endings(self):
        """Should handle Windows-style CRLF line endings."""
        data = "name,value\r\nAlice,100\r\nBob,200\r\n"
        
        df, _ = ClipboardDataParser.parse_clipboard_data(data)
        
        assert df is not None
        assert len(df) == 2

    def test_trailing_newlines(self):
        """Should handle trailing newlines."""
        data = """name,value
Alice,100
Bob,200


"""
        df, _ = ClipboardDataParser.parse_clipboard_data(data)
        
        assert df is not None
        assert len(df) == 2

    def test_header_with_spaces(self):
        """Should handle headers with spaces."""
        data = """First Name,Last Name,Email Address
John,Doe,john@example.com
Jane,Smith,jane@example.com"""
        
        df, _ = ClipboardDataParser.parse_clipboard_data(data)
        
        assert df is not None
        assert 'First Name' in df.columns
        assert 'Email Address' in df.columns


# ==============================================================================
# Test Integration Scenarios
# ==============================================================================

class TestIntegrationScenarios:
    """Tests for real-world integration scenarios."""

    def test_copy_from_spreadsheet_numeric(self):
        """Simulate copying numeric data from a spreadsheet."""
        # Excel typically uses tabs
        spreadsheet_data = """Sales\tCost\tProfit
1000\t750\t250
2000\t1400\t600
1500\t1100\t400"""
        
        df, message = ClipboardDataParser.parse_clipboard_data(spreadsheet_data)
        
        assert df is not None
        assert len(df) == 3
        assert pd.api.types.is_numeric_dtype(df['Sales'])
        assert pd.api.types.is_numeric_dtype(df['Profit'])

    def test_copy_from_database_tool(self):
        """Simulate copying data from a database tool (often tab-separated)."""
        db_data = """user_id\tusername\tcreated_at
1\tadmin\t2024-01-01 10:00:00
2\tuser1\t2024-01-02 11:30:00
3\tuser2\t2024-01-03 14:45:00"""
        
        df, _ = ClipboardDataParser.parse_clipboard_data(db_data)
        
        assert df is not None
        assert 'user_id' in df.columns
        assert 'created_at' in df.columns

    def test_copy_from_web_table(self):
        """Simulate copying data from an HTML table (often tab-separated)."""
        web_data = """Product\tPrice\tStock
Laptop\t$999.99\t50
Phone\t$599.99\t100
Tablet\t$399.99\t75"""
        
        df, _ = ClipboardDataParser.parse_clipboard_data(web_data)
        
        assert df is not None
        assert len(df) == 3
        assert 'Product' in df.columns

