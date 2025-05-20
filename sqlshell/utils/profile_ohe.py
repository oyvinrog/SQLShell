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

def get_ohe(dataframe: pd.DataFrame, column: str, binary_format: str = "numeric") -> pd.DataFrame:
    """
    Create one-hot encoded columns based on the content of the specified column.
    Automatically detects whether the column contains text data or categorical data.
    
    Args:
        dataframe (pd.DataFrame): Input dataframe
        column (str): Name of the column to process
        binary_format (str): Format for encoding - "numeric" for 1/0 or "text" for "Yes"/"No"
        
    Returns:
        pd.DataFrame: Original dataframe with additional one-hot encoded columns
    """
    # Check if column exists
    if column not in dataframe.columns:
        raise ValueError(f"Column '{column}' not found in dataframe")
    
    # Check binary format is valid
    if binary_format not in ["numeric", "text"]:
        raise ValueError("binary_format must be either 'numeric' or 'text'")
    
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
            if binary_format == "numeric":
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: 1 if isinstance(x, str) and word in str(x).lower() else 0
                )
            else:  # binary_format == "text"
                dataframe[column_name] = dataframe[column].apply(
                    lambda x: "Yes" if isinstance(x, str) and word in str(x).lower() else "No"
                )
    else:
        # Apply categorical one-hot encoding
        dataframe = get_categorical_ohe(dataframe, column, binary_format)
    
    return dataframe

def get_categorical_ohe(dataframe: pd.DataFrame, categorical_column: str, binary_format: str = "numeric") -> pd.DataFrame:
    """
    Create one-hot encoded columns for each unique category in a categorical column.
    
    Args:
        dataframe (pd.DataFrame): Input dataframe
        categorical_column (str): Name of the categorical column to process
        binary_format (str): Format for encoding - "numeric" for 1/0 or "text" for "Yes"/"No"
        
    Returns:
        pd.DataFrame: Original dataframe with additional one-hot encoded columns
    """
    # Check binary format is valid
    if binary_format not in ["numeric", "text"]:
        raise ValueError("binary_format must be either 'numeric' or 'text'")
    
    # Get unique categories
    categories = dataframe[categorical_column].dropna().unique()
    
    # Create one-hot encoded columns
    for category in categories:
        column_name = f'is_{category}'
        if binary_format == "numeric":
            dataframe[column_name] = dataframe[categorical_column].apply(
                lambda x: 1 if x == category else 0
            )
        else:  # binary_format == "text"
            dataframe[column_name] = dataframe[categorical_column].apply(
                lambda x: "Yes" if x == category else "No"
            )
    
    return dataframe

def test_ohe():
    """
    Test the one-hot encoding function with sample dataframes for both text and categorical data.
    Tests both numeric (1/0) and text (Yes/No) encoding formats.
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
    
    # Test numeric format (1/0)
    print("\n----- Testing Numeric Format (1/0) -----")
    # Apply one-hot encoding with numeric format
    text_result_numeric = get_ohe(text_df.copy(), 'text', binary_format="numeric")
    
    # Print results
    print("\nOriginal Text DataFrame:")
    print(text_df)
    print("\nDataFrame with Numeric One-Hot Encoded Columns (1/0):")
    print(text_result_numeric)
    
    # Verify that the function correctly identified this as text data
    has_columns = [col for col in text_result_numeric.columns if col.startswith('has_')]
    assert len(has_columns) > 0, "Text data was not correctly identified"
    
    # Verify that all OHE columns contain only 0s and 1s
    for col in has_columns:
        assert set(text_result_numeric[col].unique()).issubset({0, 1}), f"Column {col} contains invalid values"
    
    # Test text format (Yes/No)
    print("\n----- Testing Text Format (Yes/No) -----")
    # Apply one-hot encoding with text format
    text_result_text = get_ohe(text_df.copy(), 'text', binary_format="text")
    
    # Print results
    print("\nDataFrame with Text One-Hot Encoded Columns (Yes/No):")
    print(text_result_text)
    
    # Verify that all OHE columns contain only Yes and No
    has_columns_text = [col for col in text_result_text.columns if col.startswith('has_')]
    for col in has_columns_text:
        assert set(text_result_text[col].unique()).issubset({"Yes", "No"}), f"Column {col} contains invalid values"
    
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
    
    # Test numeric format (1/0)
    print("\n----- Testing Numeric Format (1/0) -----")
    # Apply one-hot encoding with numeric format
    cat_result_numeric = get_ohe(cat_df.copy(), 'category', binary_format="numeric")
    
    # Print results
    print("\nOriginal Categorical DataFrame:")
    print(cat_df)
    print("\nDataFrame with Numeric One-Hot Encoded Columns (1/0):")
    print(cat_result_numeric)
    
    # Verify that the function correctly identified this as categorical data
    is_columns = [col for col in cat_result_numeric.columns if col.startswith('is_')]
    assert len(is_columns) > 0, "Categorical data was not correctly identified"
    
    # Verify that we have the expected number of columns for categorical data
    unique_categories = len(cat_df['category'].unique())
    assert len(is_columns) == unique_categories, "Incorrect number of categorical columns"
    
    # Verify that all OHE columns contain only 0s and 1s
    for col in is_columns:
        assert set(cat_result_numeric[col].unique()).issubset({0, 1}), f"Column {col} contains invalid values"
    
    # Test text format (Yes/No)
    print("\n----- Testing Text Format (Yes/No) -----")
    # Apply one-hot encoding with text format
    cat_result_text = get_ohe(cat_df.copy(), 'category', binary_format="text")
    
    # Print results
    print("\nDataFrame with Text One-Hot Encoded Columns (Yes/No):")
    print(cat_result_text)
    
    # Verify that all OHE columns contain only Yes and No
    is_columns_text = [col for col in cat_result_text.columns if col.startswith('is_')]
    for col in is_columns_text:
        assert set(cat_result_text[col].unique()).issubset({"Yes", "No"}), f"Column {col} contains invalid values"
    
    print("\nCategorical data tests passed successfully!")

def test_categorical_ohe():
    """
    Test the categorical one-hot encoding function with a sample dataframe.
    Tests both numeric (1/0) and text (Yes/No) encoding formats.
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
    
    # Test numeric format (1/0)
    print("\n----- Testing Numeric Format (1/0) -----")
    # Apply categorical one-hot encoding with numeric format
    result_numeric = get_categorical_ohe(df.copy(), 'category', binary_format="numeric")
    
    # Print results
    print("\nOriginal DataFrame:")
    print(df)
    print("\nDataFrame with Numeric One-Hot Encoded Columns (1/0):")
    print(result_numeric)
    
    # Verify that we have the expected number of columns
    unique_categories = len(df['category'].unique())
    is_columns = [col for col in result_numeric.columns if col.startswith('is_')]
    assert len(is_columns) == unique_categories, "Incorrect number of categorical columns"
    
    # Verify that all OHE columns contain only 0s and 1s
    for col in is_columns:
        assert set(result_numeric[col].unique()).issubset({0, 1}), f"Column {col} contains invalid values"
    
    # Test text format (Yes/No)
    print("\n----- Testing Text Format (Yes/No) -----")
    # Apply categorical one-hot encoding with text format
    result_text = get_categorical_ohe(df.copy(), 'category', binary_format="text")
    
    # Print results
    print("\nDataFrame with Text One-Hot Encoded Columns (Yes/No):")
    print(result_text)
    
    # Verify that all OHE columns contain only Yes and No
    is_columns_text = [col for col in result_text.columns if col.startswith('is_')]
    for col in is_columns_text:
        assert set(result_text[col].unique()).issubset({"Yes", "No"}), f"Column {col} contains invalid values"
    
    print("\nAll categorical tests passed successfully!")

# Add visualization functionality
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                           QTableWidget, QTableWidgetItem, QLabel, QPushButton,
                           QComboBox, QSplitter, QTabWidget, QScrollArea,
                           QFrame, QSizePolicy, QButtonGroup, QRadioButton,
                           QMessageBox, QHeaderView, QApplication)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

class OneHotEncodingVisualization(QMainWindow):
    # Add signal to notify when encoding should be applied
    encodingApplied = pyqtSignal(pd.DataFrame)
    
    def __init__(self, original_df, encoded_df, encoded_column, binary_format="numeric"):
        super().__init__()
        self.original_df = original_df
        self.encoded_df = encoded_df
        self.encoded_column = encoded_column
        self.binary_format = binary_format
        self.setWindowTitle(f"One-Hot Encoding Visualization - {encoded_column}")
        self.setGeometry(100, 100, 1000, 800)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main layout
        main_layout = QVBoxLayout(main_widget)
        
        # Title
        title_label = QLabel(f"One-Hot Encoding Analysis: {encoded_column}")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Description
        description = "One-hot encoding transforms categorical data into a binary matrix format where each category becomes a separate binary column."
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # Format selector
        format_layout = QHBoxLayout()
        format_label = QLabel("Encoding Format:")
        self.format_selector = QComboBox()
        self.format_selector.addItems(["Numeric (1/0)", "Text (Yes/No)"])
        self.format_selector.setCurrentIndex(0 if binary_format == "numeric" else 1)
        self.format_selector.currentIndexChanged.connect(self.change_format)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_selector)
        format_layout.addStretch(1)
        main_layout.addLayout(format_layout)
        
        # Splitter to divide the screen
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter, 1)
        
        # Top widget: Data view
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Create tab widget for different views
        tab_widget = QTabWidget()
        
        # Tab 1: Original data
        original_tab = QWidget()
        original_layout = QVBoxLayout(original_tab)
        original_table = self.create_table_from_df(self.original_df)
        original_layout.addWidget(original_table)
        tab_widget.addTab(original_tab, "Original Data")
        
        # Tab 2: Encoded data
        encoded_tab = QWidget()
        encoded_layout = QVBoxLayout(encoded_tab)
        encoded_table = self.create_table_from_df(self.encoded_df)
        encoded_layout.addWidget(encoded_table)
        tab_widget.addTab(encoded_tab, "Encoded Data")
        
        top_layout.addWidget(tab_widget)
        splitter.addWidget(top_widget)
        
        # Bottom widget: Visualizations
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Visualization title
        viz_title = QLabel("Visualization")
        viz_title.setFont(title_font)
        bottom_layout.addWidget(viz_title)
        
        # Create matplotlib figure
        self.figure = plt.figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        bottom_layout.addWidget(self.canvas)
        
        # Visualization type selector
        viz_selector_layout = QHBoxLayout()
        viz_selector_label = QLabel("Visualization Type:")
        self.viz_selector = QComboBox()
        self.viz_selector.addItems(["Value Counts", "Correlation Heatmap"])
        self.viz_selector.currentIndexChanged.connect(self.update_visualization)
        viz_selector_layout.addWidget(viz_selector_label)
        viz_selector_layout.addWidget(self.viz_selector)
        viz_selector_layout.addStretch(1)
        bottom_layout.addLayout(viz_selector_layout)
        
        # Add Apply Button
        apply_layout = QHBoxLayout()
        apply_layout.addStretch(1)
        
        self.apply_button = QPushButton("Apply Encoding")
        self.apply_button.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:pressed {
                background-color: #1F618D;
            }
        """)
        self.apply_button.setMinimumWidth(150)
        self.apply_button.clicked.connect(self.apply_encoding)
        apply_layout.addWidget(self.apply_button)
        
        bottom_layout.addLayout(apply_layout)
        
        splitter.addWidget(bottom_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([300, 500])
        
        # Create initial visualization
        self.update_visualization()
    
    def create_table_from_df(self, df):
        """Create a table widget from a dataframe"""
        table = QTableWidget()
        table.setRowCount(min(100, len(df)))  # Limit to 100 rows for performance
        table.setColumnCount(len(df.columns))
        
        # Set headers
        table.setHorizontalHeaderLabels(df.columns)
        
        # Fill data
        for row in range(min(100, len(df))):
            for col, col_name in enumerate(df.columns):
                value = str(df.iloc[row, col])
                item = QTableWidgetItem(value)
                table.setItem(row, col, item)
        
        # Optimize appearance
        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        return table
    
    def update_visualization(self):
        """Update the visualization based on the selected type"""
        viz_type = self.viz_selector.currentText()
        
        # Clear previous plot
        self.figure.clear()
        
        # Get the encoded columns (those starting with 'is_' or 'has_')
        is_columns = [col for col in self.encoded_df.columns if col.startswith('is_')]
        has_columns = [col for col in self.encoded_df.columns if col.startswith('has_')]
        encoded_columns = is_columns + has_columns
        
        if viz_type == "Value Counts":
            # Create value counts visualization
            ax = self.figure.add_subplot(111)
            
            # Get value counts from original column
            value_counts = self.original_df[self.encoded_column].value_counts()
            
            # Plot
            if len(value_counts) > 15:
                # For high cardinality, show top 15
                value_counts.nlargest(15).plot(kind='barh', ax=ax)
                ax.set_title(f"Top 15 Values in {self.encoded_column}")
            else:
                value_counts.plot(kind='barh', ax=ax)
                ax.set_title(f"Value Counts in {self.encoded_column}")
            
            ax.set_xlabel("Count")
            ax.set_ylabel(self.encoded_column)
            
        elif viz_type == "Correlation Heatmap":
            # Create correlation heatmap for one-hot encoded columns
            if len(encoded_columns) > 0:
                ax = self.figure.add_subplot(111)
                
                # Get subset with just the encoded columns
                encoded_subset = self.encoded_df[encoded_columns]
                
                # Calculate correlation matrix
                corr_matrix = encoded_subset.corr()
                
                # Create heatmap
                sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', linewidths=0.5, ax=ax)
                ax.set_title(f"Correlation Between Encoded Features")
            else:
                # No encoded columns found
                ax = self.figure.add_subplot(111)
                ax.text(0.5, 0.5, "No encoded columns found", 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes)
                ax.axis('off')
        
        # Update the canvas
        self.canvas.draw()
    
    def apply_encoding(self):
        """Apply the encoded dataframe to the main window"""
        reply = QMessageBox.question(
            self, 
            "Apply Encoding", 
            "Are you sure you want to apply this encoding to the original table?\n\n"
            "This will add the one-hot encoded columns to the current result table.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Emit signal with the encoded DataFrame
            self.encodingApplied.emit(self.encoded_df)
            QMessageBox.information(
                self,
                "Encoding Applied",
                "The one-hot encoding has been applied to the table."
            )
    
    def change_format(self):
        """Change the binary format and reapply encoding"""
        # Get the selected format
        selected_format = "numeric" if self.format_selector.currentIndex() == 0 else "text"
        
        # Only update if format has changed
        if selected_format != self.binary_format:
            # Update format
            self.binary_format = selected_format
            
            # Reapply encoding
            self.encoded_df = get_ohe(self.original_df.copy(), self.encoded_column, self.binary_format)
            
            # Update tables
            tab_widget = self.findChild(QTabWidget)
            if tab_widget:
                # Update encoded data tab
                encoded_tab = tab_widget.widget(1)
                if encoded_tab:
                    # Clear old layout
                    for i in reversed(range(encoded_tab.layout().count())): 
                        encoded_tab.layout().itemAt(i).widget().setParent(None)
                    
                    # Add new table
                    encoded_table = self.create_table_from_df(self.encoded_df)
                    encoded_tab.layout().addWidget(encoded_table)
            
            # Update visualization
            self.update_visualization()
            
            # Show confirmation
            QMessageBox.information(
                self,
                "Format Changed",
                f"Encoding format changed to {selected_format}"
            )

def visualize_ohe(df, column, binary_format="numeric"):
    """
    Visualize the one-hot encoding of a column in a dataframe.
    
    Args:
        df (pd.DataFrame): The original dataframe
        column (str): The column to encode and visualize
        binary_format (str): Format for encoding - "numeric" for 1/0 or "text" for "Yes"/"No"
        
    Returns:
        QMainWindow: The visualization window
    """
    # Create a copy to avoid modifying the original
    original_df = df.copy()
    
    # Apply one-hot encoding
    encoded_df = get_ohe(original_df, column, binary_format)
    
    # Create and show the visualization
    vis = OneHotEncodingVisualization(original_df, encoded_df, column, binary_format)
    vis.show()
    
    return vis

if __name__ == "__main__":
    # Run tests
    test_ohe()
    test_categorical_ohe()
    
    # Test the visualization with both formats
    import sys
    from PyQt6.QtWidgets import QApplication
    
    if QApplication.instance() is None:
        app = QApplication(sys.argv)
    
        # Create a sample dataframe
        data = {
            'category': ['red', 'blue', 'green', 'red', 'yellow', 'blue'],
            'text': [
                'The quick brown fox',
                'A lazy dog',
                'Brown fox jumps',
                'Quick brown fox',
                'Lazy dog sleeps',
                'Fox and dog'
            ]
        }
        df = pd.DataFrame(data)
        
        # Show visualization with numeric format
        vis_numeric = visualize_ohe(df, 'category', binary_format="numeric")
        
        # Show visualization with text format
        vis_text = visualize_ohe(df, 'text', binary_format="text")
        
        # Start the application
        sys.exit(app.exec())
