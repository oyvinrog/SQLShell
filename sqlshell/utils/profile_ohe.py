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

def get_ohe(dataframe: pd.DataFrame, text_column: str) -> pd.DataFrame:
    """
    Create one-hot encoded columns for the most frequent words in a text column.
    
    Args:
        dataframe (pd.DataFrame): Input dataframe
        text_column (str): Name of the text column to process
        
    Returns:
        pd.DataFrame: Original dataframe with additional one-hot encoded columns
    """
    # Get stopwords
    stop_words = set(stopwords.words('english'))
    
    # Tokenize and count words
    word_counts = {}
    for text in dataframe[text_column]:
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
        dataframe[column_name] = dataframe[text_column].apply(
            lambda x: 1 if isinstance(x, str) and word in x.lower() else 0
        )
    
    return dataframe

def test_ohe():
    """
    Test the one-hot encoding function with a sample dataframe.
    """
    # Create sample data
    data = {
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
    df = pd.DataFrame(data)
    
    # Apply one-hot encoding
    result_df = get_ohe(df, 'text')
    
    # Print results
    print("\nOriginal DataFrame:")
    print(df)
    print("\nDataFrame with One-Hot Encoded Columns:")
    print(result_df)
    
    # Verify that we have the expected number of columns
    expected_columns = len(df.columns) + 10  # original columns + 10 OHE columns
    assert len(result_df.columns) == expected_columns, "Incorrect number of columns"
    
    # Verify that all OHE columns contain only 0s and 1s
    ohe_columns = [col for col in result_df.columns if col.startswith('has_')]
    for col in ohe_columns:
        assert set(result_df[col].unique()).issubset({0, 1}), f"Column {col} contains invalid values"
    
    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    test_ohe()
