"""
Clipboard data parsing utilities for SQLShell.
Handles detection and parsing of tabular data from clipboard.
"""

import re
import pandas as pd
import io
from typing import Optional, Tuple


class ClipboardDataParser:
    """Parses clipboard text and detects if it contains tabular data."""
    
    # Minimum requirements to consider text as tabular data
    MIN_ROWS = 1
    MIN_COLUMNS = 2
    
    # Common delimiters in order of preference
    DELIMITERS = ['\t', ',', ';', '|']
    
    @staticmethod
    def is_likely_data(text: str) -> bool:
        """
        Quick check to determine if clipboard text looks like tabular data.
        
        Args:
            text: Clipboard text to analyze
            
        Returns:
            True if the text appears to be tabular data
        """
        if not text or not text.strip():
            return False
        
        lines = text.strip().split('\n')
        
        # Need at least one row
        if len(lines) < ClipboardDataParser.MIN_ROWS:
            return False
        
        # Check if lines have consistent delimiters
        for delimiter in ClipboardDataParser.DELIMITERS:
            first_line_count = lines[0].count(delimiter)
            if first_line_count >= 1:  # At least 2 columns
                # Check consistency across rows (allow some variance)
                consistent = True
                for line in lines[1:min(10, len(lines))]:  # Check first 10 rows
                    if line.strip():  # Skip empty lines
                        line_count = line.count(delimiter)
                        # Allow small variance for edge cases
                        if abs(line_count - first_line_count) > 1:
                            consistent = False
                            break
                if consistent:
                    return True
        
        return False
    
    @staticmethod
    def detect_delimiter(text: str) -> str:
        """
        Detect the most likely delimiter in the text.
        
        Args:
            text: Text to analyze
            
        Returns:
            The detected delimiter (defaults to tab)
        """
        lines = text.strip().split('\n')
        if not lines:
            return '\t'
        
        # Count occurrences of each delimiter in first few rows
        delimiter_scores = {}
        sample_lines = lines[:min(10, len(lines))]
        
        for delimiter in ClipboardDataParser.DELIMITERS:
            counts = [line.count(delimiter) for line in sample_lines if line.strip()]
            if counts:
                avg_count = sum(counts) / len(counts)
                # Calculate consistency (lower variance = better)
                variance = sum((c - avg_count) ** 2 for c in counts) / len(counts) if len(counts) > 1 else 0
                
                # Score based on average count and consistency
                # Higher count and lower variance = better
                if avg_count >= 1:
                    delimiter_scores[delimiter] = avg_count / (1 + variance)
        
        if not delimiter_scores:
            return '\t'
        
        # Return delimiter with highest score
        return max(delimiter_scores, key=delimiter_scores.get)
    
    @staticmethod
    def detect_header(df: pd.DataFrame) -> bool:
        """
        Try to detect if the first row is a header row.
        
        Args:
            df: DataFrame with first row potentially being header
            
        Returns:
            True if first row appears to be a header
        """
        if df.empty or len(df) < 2:
            return True  # Assume header if only 1 row
        
        first_row = df.iloc[0]
        rest_of_data = df.iloc[1:]
        
        # Check 1: Headers are typically strings
        first_row_all_strings = all(
            isinstance(val, str) or pd.isna(val) 
            for val in first_row
        )
        
        # Check 2: Headers usually don't contain pure numbers
        first_row_no_pure_numbers = True
        for val in first_row:
            if pd.notna(val):
                try:
                    float(str(val).replace(',', '').replace(' ', ''))
                    first_row_no_pure_numbers = False
                    break
                except ValueError:
                    pass
        
        # Check 3: Check if data rows have different types than header
        # (e.g., header is strings, data is numbers)
        type_mismatch = False
        for col_idx in range(len(df.columns)):
            header_val = first_row.iloc[col_idx]
            if pd.isna(header_val):
                continue
                
            # Check if subsequent rows have different types
            for row_idx in range(min(5, len(rest_of_data))):
                data_val = rest_of_data.iloc[row_idx, col_idx]
                if pd.isna(data_val):
                    continue
                    
                # If header is string-like and data is numeric
                try:
                    float(str(data_val).replace(',', '').replace(' ', ''))
                    try:
                        float(str(header_val).replace(',', '').replace(' ', ''))
                    except ValueError:
                        type_mismatch = True
                        break
                except ValueError:
                    pass
            
            if type_mismatch:
                break
        
        # Check 4: Headers often contain certain patterns
        header_patterns = ['id', 'name', 'date', 'time', 'type', 'status', 'count', 
                          'amount', 'price', 'value', 'total', 'col', 'column', 
                          'field', 'key', 'index', 'num', 'code', 'description']
        has_header_pattern = False
        for val in first_row:
            if pd.notna(val) and isinstance(val, str):
                val_lower = str(val).lower()
                if any(pattern in val_lower for pattern in header_patterns):
                    has_header_pattern = True
                    break
        
        # Decision logic:
        # Strong indicators: type mismatch or header patterns
        if type_mismatch or has_header_pattern:
            return True
        
        # Weak indicators: all strings and no pure numbers
        if first_row_all_strings and first_row_no_pure_numbers:
            return True
        
        return False
    
    @staticmethod
    def parse_clipboard_data(text: str) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Parse clipboard text into a DataFrame.
        
        Args:
            text: Clipboard text to parse
            
        Returns:
            Tuple of (DataFrame or None, status message)
        """
        if not text or not text.strip():
            return None, "Clipboard is empty"
        
        # Check if it looks like data
        if not ClipboardDataParser.is_likely_data(text):
            return None, "Clipboard content doesn't appear to be tabular data"
        
        # Detect delimiter
        delimiter = ClipboardDataParser.detect_delimiter(text)
        
        try:
            # First pass: read without header to analyze
            df_no_header = pd.read_csv(
                io.StringIO(text),
                sep=delimiter,
                header=None,
                dtype=str,  # Read as strings initially for analysis
                on_bad_lines='warn',
                skip_blank_lines=True
            )
            
            if df_no_header.empty:
                return None, "No data could be parsed from clipboard"
            
            # Check if we have enough columns
            if len(df_no_header.columns) < ClipboardDataParser.MIN_COLUMNS:
                return None, f"Data has only {len(df_no_header.columns)} column(s). Expected at least {ClipboardDataParser.MIN_COLUMNS}."
            
            # Detect if first row is header
            has_header = ClipboardDataParser.detect_header(df_no_header)
            
            # Re-read with appropriate header setting
            df = pd.read_csv(
                io.StringIO(text),
                sep=delimiter,
                header=0 if has_header else None,
                on_bad_lines='warn',
                skip_blank_lines=True
            )
            
            # Generate column names if no header
            if not has_header:
                df.columns = [f'column_{i+1}' for i in range(len(df.columns))]
            else:
                # Clean up column names
                df.columns = [
                    str(col).strip() if pd.notna(col) else f'column_{i+1}'
                    for i, col in enumerate(df.columns)
                ]
            
            # Try to infer better dtypes
            df = df.infer_objects()
            
            # Convert numeric-looking strings to numbers
            for col in df.columns:
                try:
                    # Try numeric conversion
                    numeric_col = pd.to_numeric(df[col], errors='coerce')
                    if numeric_col.notna().sum() > 0.5 * len(df):  # If >50% are valid numbers
                        df[col] = numeric_col
                except Exception:
                    pass
            
            delimiter_name = {'\t': 'tab', ',': 'comma', ';': 'semicolon', '|': 'pipe'}.get(delimiter, delimiter)
            header_msg = "with header" if has_header else "without header"
            
            return df, f"Parsed {len(df)} rows × {len(df.columns)} columns ({delimiter_name}-separated, {header_msg})"
            
        except Exception as e:
            return None, f"Error parsing data: {str(e)}"
    
    @staticmethod
    def get_data_preview(df: pd.DataFrame, max_rows: int = 5) -> str:
        """
        Get a preview string of the DataFrame.
        
        Args:
            df: DataFrame to preview
            max_rows: Maximum rows to show
            
        Returns:
            Preview string
        """
        if df is None or df.empty:
            return "No data"
        
        preview_df = df.head(max_rows)
        return preview_df.to_string(index=False)

