import pandas as pd
import numpy as np
from typing import Union, Optional
import re


def search(dataframe: pd.DataFrame, text: str, case_sensitive: bool = False, regex: bool = False) -> pd.DataFrame:
    """
    Search for text across all columns in a DataFrame efficiently.
    
    Args:
        dataframe: The pandas DataFrame to search in
        text: The text to search for
        case_sensitive: Whether the search should be case-sensitive (default: False)
        regex: Whether to treat the search text as a regular expression (default: False)
    
    Returns:
        DataFrame containing only the rows that have a match in any column
    """
    if dataframe.empty:
        return dataframe
    
    if not text:
        return dataframe
    
    # Convert search text based on case sensitivity
    search_text = text if case_sensitive else text.lower()
    
    # Create a boolean mask for matching rows
    mask = pd.Series([False] * len(dataframe), index=dataframe.index)
    
    # Search through each column
    for column in dataframe.columns:
        # Convert column to string, handling NaN values
        col_str = dataframe[column].astype(str)
        
        if not case_sensitive:
            col_str = col_str.str.lower()
        
        if regex:
            try:
                # Use regex search
                flags = 0 if case_sensitive else re.IGNORECASE
                column_mask = col_str.str.contains(search_text, regex=True, na=False, flags=flags)
            except re.error:
                # If regex is invalid, fall back to literal search
                column_mask = col_str.str.contains(search_text, regex=False, na=False)
        else:
            # Use literal string search (faster for non-regex)
            column_mask = col_str.str.contains(search_text, regex=False, na=False)
        
        # Combine with overall mask using OR operation
        mask = mask | column_mask
    
    return dataframe[mask]


def search_optimized(dataframe: pd.DataFrame, text: str, case_sensitive: bool = False) -> pd.DataFrame:
    """
    Optimized version of search for very large datasets.
    Uses vectorized operations for better performance.
    
    Args:
        dataframe: The pandas DataFrame to search in
        text: The text to search for
        case_sensitive: Whether the search should be case-sensitive (default: False)
    
    Returns:
        DataFrame containing only the rows that have a match in any column
    """
    if dataframe.empty or not text:
        return dataframe if dataframe.empty else dataframe
    
    # Convert search text based on case sensitivity
    search_text = text if case_sensitive else text.lower()
    
    # Convert all columns to string and concatenate with separator
    # This allows for vectorized search across all columns at once
    separator = '|'  # Use a separator that's unlikely to appear in data
    
    # Handle case sensitivity by converting to lowercase if needed
    if case_sensitive:
        combined = dataframe.astype(str).apply(lambda x: separator.join(x), axis=1)
    else:
        combined = dataframe.astype(str).apply(lambda x: separator.join(x).lower(), axis=1)
    
    # Search in the combined string
    mask = combined.str.contains(search_text, regex=False, na=False)
    
    return dataframe[mask]
