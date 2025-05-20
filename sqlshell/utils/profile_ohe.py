import pandas as pd
import numpy as np
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
# Download punkt_tab explicitly as required by the punkt tokenizer
try:
    nltk.data.find('tokenizers/punkt_tab/english')
except LookupError:
    nltk.download('punkt_tab')

def get_ohe(dataframe: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Create one-hot encoded columns based on the content of the specified column.
    Automatically detects whether the column contains text data or categorical data.
    
    Args:
        dataframe (pd.DataFrame): Input dataframe
        column (str): Name of the column to process
        
    Returns:
        pd.DataFrame: Original dataframe with additional one-hot encoded columns
    """
    # Check if column exists
    if column not in dataframe.columns:
        raise ValueError(f"Column '{column}' not found in dataframe")
    
    # Check if the column appears to be categorical or text
    # Heuristic: If average string length > 15 or contains spaces, treat as text
    is_text = False
    
    # Filter out non-string values
    string_values = dataframe[column].dropna().astype(str)
    if not len(string_values):
        return dataframe  # Nothing to process
        
    # Check for spaces and average length
    contains_spaces = any(' ' in str(val) for val in string_values)
    avg_length = string_values.str.len().mean()
    
    if contains_spaces or avg_length > 15:
        is_text = True
    
    # Apply appropriate encoding
    if is_text:
        # Apply text-based one-hot encoding
        # Get stopwords
        stop_words = set(stopwords.words('english'))
        
        # Tokenize and count words
        word_counts = {}
        for text in dataframe[column]:
            if isinstance(text, str):
                # Tokenize and convert to lowercase
                words = word_tokenize(text.lower())
                # Remove stopwords and count
                words = [word for word in words if word not in stop_words and word.isalnum()]
                for word in words:
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        # Get top 10 most frequent words
        top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_words = [word for word, _ in top_words]
        
        # Create one-hot encoded columns
        for word in top_words:
            column_name = f'has_{word}'
            dataframe[column_name] = dataframe[column].apply(
                lambda x: 1 if isinstance(x, str) and word in str(x).lower() else 0
            )
    else:
        # Apply categorical one-hot encoding
        dataframe = get_categorical_ohe(dataframe, column)
    
    return dataframe

def get_categorical_ohe(dataframe: pd.DataFrame, categorical_column: str) -> pd.DataFrame:
    """
    Create one-hot encoded columns for each unique category in a categorical column.
    
    Args:
        dataframe (pd.DataFrame): Input dataframe
        categorical_column (str): Name of the categorical column to process
        
    Returns:
        pd.DataFrame: Original dataframe with additional one-hot encoded columns
    """
    # Get unique categories
    categories = dataframe[categorical_column].dropna().unique()
    
    # Create one-hot encoded columns
    for category in categories:
        column_name = f'is_{category}'
        dataframe[column_name] = dataframe[categorical_column].apply(
            lambda x: 1 if x == category else 0
        )
    
    return dataframe

def test_ohe():
    """
    Test the one-hot encoding function with sample dataframes for both text and categorical data.
    """
    print("\n===== Testing Text Data One-Hot Encoding =====")
    # Create sample text data
    text_data = {
        'text': [
            'The quick brown fox jumps over the lazy dog',
            'A quick brown dog runs in the park',
            'The lazy cat sleeps all day',
            'A brown fox and a lazy dog play together',
            'The quick cat chases the mouse',
            'A lazy dog sleeps in the sun',
            'The brown fox is quick and clever',
            'A cat and a dog are best friends',
            'The quick mouse runs from the cat',
            'A lazy fox sleeps in the shade'
        ]
    }
    
    # Create dataframe
    text_df = pd.DataFrame(text_data)
    
    # Get the original column count
    original_col_count = len(text_df.columns)
    
    # Apply one-hot encoding
    text_result_df = get_ohe(text_df, 'text')
    
    # Print results
    print("\nOriginal Text DataFrame:")
    print(text_df)
    print("\nDataFrame with One-Hot Encoded Columns:")
    print(text_result_df)
    
    # Verify that the function correctly identified this as text data
    has_columns = [col for col in text_result_df.columns if col.startswith('has_')]
    assert len(has_columns) > 0, "Text data was not correctly identified"
    
    # Verify that all OHE columns contain only 0s and 1s
    for col in has_columns:
        assert set(text_result_df[col].unique()).issubset({0, 1}), f"Column {col} contains invalid values"
    
    print("\nText data tests passed successfully!")
    
    print("\n===== Testing Categorical Data One-Hot Encoding =====")
    # Create sample data with categorical values
    categorical_data = {
        'category': [
            'red', 'blue', 'green', 'red', 'yellow',
            'blue', 'green', 'red', 'yellow', 'blue'
        ]
    }
    
    # Create dataframe
    cat_df = pd.DataFrame(categorical_data)
    
    # Get the original column count
    cat_original_col_count = len(cat_df.columns)
    
    # Apply one-hot encoding (should automatically detect categorical data)
    cat_result_df = get_ohe(cat_df, 'category')
    
    # Print results
    print("\nOriginal Categorical DataFrame:")
    print(cat_df)
    print("\nDataFrame with Categorical One-Hot Encoded Columns:")
    print(cat_result_df)
    
    # Verify that the function correctly identified this as categorical data
    is_columns = [col for col in cat_result_df.columns if col.startswith('is_')]
    assert len(is_columns) > 0, "Categorical data was not correctly identified"
    
    # Verify that we have the expected number of columns for categorical data
    unique_categories = len(cat_df['category'].unique())
    assert len(is_columns) == unique_categories, "Incorrect number of categorical columns"
    
    # Verify that all OHE columns contain only 0s and 1s
    for col in is_columns:
        assert set(cat_result_df[col].unique()).issubset({0, 1}), f"Column {col} contains invalid values"
    
    print("\nCategorical data tests passed successfully!")

def test_categorical_ohe():
    """
    Test the categorical one-hot encoding function with a sample dataframe.
    """
    # Create sample data with categorical values
    data = {
        'category': [
            'red', 'blue', 'green', 'red', 'yellow',
            'blue', 'green', 'red', 'yellow', 'blue'
        ]
    }
    
    # Create dataframe
    df = pd.DataFrame(data)
    
    # Get the original column count
    original_col_count = len(df.columns)
    
    # Apply categorical one-hot encoding
    result_df = get_categorical_ohe(df, 'category')
    
    # Print results
    print("\nOriginal DataFrame:")
    print(df)
    print("\nDataFrame with Categorical One-Hot Encoded Columns:")
    print(result_df)
    
    # Verify that we have the expected number of columns
    unique_categories = len(df['category'].unique())
    is_columns = [col for col in result_df.columns if col.startswith('is_')]
    assert len(is_columns) == unique_categories, "Incorrect number of categorical columns"
    
    # Verify that all OHE columns contain only 0s and 1s
    for col in is_columns:
        assert set(result_df[col].unique()).issubset({0, 1}), f"Column {col} contains invalid values"
    
    print("\nAll categorical tests passed successfully!")

if __name__ == "__main__":
    test_ohe()
    test_categorical_ohe()
