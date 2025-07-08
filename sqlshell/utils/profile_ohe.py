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

def get_ohe(dataframe: pd.DataFrame, column: str, binary_format: str = "numeric", 
           algorithm: str = "basic") -> pd.DataFrame:
    """
    Create one-hot encoded columns based on the content of the specified column.
    Automatically detects whether the column contains text data or categorical data.
    
    Args:
        dataframe (pd.DataFrame): Input dataframe
        column (str): Name of the column to process
        binary_format (str): Format for encoding - "numeric" for 1/0 or "text" for "Yes"/"No"
        algorithm (str): Algorithm to use - "basic", "advanced", or "comprehensive"
        
    Returns:
        pd.DataFrame: Original dataframe with additional one-hot encoded columns
    """
    # Check if column exists
    if column not in dataframe.columns:
        raise ValueError(f"Column '{column}' not found in dataframe")
    
    # Check binary format is valid
    if binary_format not in ["numeric", "text"]:
        raise ValueError("binary_format must be either 'numeric' or 'text'")
    
    # Check algorithm is valid
    if algorithm not in ["basic", "advanced", "comprehensive"]:
        raise ValueError("algorithm must be 'basic', 'advanced', or 'comprehensive'")
    
    # Use advanced algorithms if requested
    if algorithm in ["advanced", "comprehensive"]:
        try:
            # Try relative import first
            try:
                from .profile_ohe_advanced import get_advanced_ohe
            except ImportError:
                # Fall back to direct import
                import sys
                import os
                sys.path.insert(0, os.path.dirname(__file__))
                from profile_ohe_advanced import get_advanced_ohe
            
            return get_advanced_ohe(dataframe, column, binary_format, 
                                  analysis_type=algorithm, max_features=20)
        except ImportError as e:
            print(f"Advanced algorithms not available ({e}). Using basic approach.")
            algorithm = "basic"
    
    # Original basic algorithm
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

# Add visualization functionality
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                           QTableWidget, QTableWidgetItem, QLabel, QPushButton,
                           QComboBox, QSplitter, QTabWidget, QScrollArea,
                           QFrame, QSizePolicy, QButtonGroup, QRadioButton,
                           QMessageBox, QHeaderView, QApplication, QTextEdit)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

class OneHotEncodingVisualization(QMainWindow):
    # Add signal to notify when encoding should be applied
    encodingApplied = pyqtSignal(pd.DataFrame)
    
    def __init__(self, original_df, encoded_df, encoded_column, binary_format="numeric", algorithm="basic"):
        super().__init__()
        self.original_df = original_df
        self.encoded_df = encoded_df
        self.encoded_column = encoded_column
        self.binary_format = binary_format
        self.algorithm = algorithm
        self.setWindowTitle(f"One-Hot Encoding Visualization - {encoded_column}")
        self.setGeometry(100, 100, 1200, 900)
        
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
        
        # Control panel
        control_layout = QHBoxLayout()
        
        # Algorithm selector
        algorithm_label = QLabel("Algorithm:")
        self.algorithm_selector = QComboBox()
        self.algorithm_selector.addItems(["Basic (Frequency)", "Advanced (Academic)", "Comprehensive (All Methods)"])
        current_index = {"basic": 0, "advanced": 1, "comprehensive": 2}.get(algorithm, 0)
        self.algorithm_selector.setCurrentIndex(current_index)
        self.algorithm_selector.currentIndexChanged.connect(self.change_algorithm)
        control_layout.addWidget(algorithm_label)
        control_layout.addWidget(self.algorithm_selector)
        
        # Format selector
        format_label = QLabel("Encoding Format:")
        self.format_selector = QComboBox()
        self.format_selector.addItems(["Numeric (1/0)", "Text (Yes/No)"])
        self.format_selector.setCurrentIndex(0 if binary_format == "numeric" else 1)
        self.format_selector.currentIndexChanged.connect(self.change_format)
        control_layout.addWidget(format_label)
        control_layout.addWidget(self.format_selector)
        control_layout.addStretch(1)
        
        main_layout.addLayout(control_layout)
        
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
        
        # Tab 3: Algorithm insights (new)
        insights_tab = QWidget()
        insights_layout = QVBoxLayout(insights_tab)
        self.insights_text = QTextEdit()
        self.insights_text.setReadOnly(True)
        insights_layout.addWidget(self.insights_text)
        tab_widget.addTab(insights_tab, "Algorithm Insights")
        
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
        self.figure = plt.figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        bottom_layout.addWidget(self.canvas)
        
        # Visualization type selector
        viz_selector_layout = QHBoxLayout()
        viz_selector_label = QLabel("Visualization Type:")
        self.viz_selector = QComboBox()
        viz_options = ["Value Counts", "Correlation Heatmap"]
        if algorithm in ["advanced", "comprehensive"]:
            viz_options.append("Feature Type Analysis")
        self.viz_selector.addItems(viz_options)
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
        splitter.setSizes([400, 500])
        
        # Update insights and visualization
        self.update_insights()
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
            if len(encoded_columns) > 1:
                ax = self.figure.add_subplot(111)
                
                # Get subset with just the encoded columns
                encoded_subset = self.encoded_df[encoded_columns]
                
                # Calculate correlation matrix
                corr_matrix = encoded_subset.corr()
                
                # Create heatmap
                if len(encoded_columns) > 10:
                    # For many features, don't show annotations
                    sns.heatmap(corr_matrix, cmap='coolwarm', linewidths=0.5, ax=ax, 
                               annot=False, center=0)
                else:
                    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', linewidths=0.5, 
                               ax=ax, fmt='.2f', center=0)
                
                ax.set_title(f"Correlation Between Encoded Features ({self.algorithm.title()} Algorithm)")
            else:
                # No encoded columns found
                ax = self.figure.add_subplot(111)
                ax.text(0.5, 0.5, "Need at least 2 features for correlation analysis", 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes)
                ax.axis('off')
        
        elif viz_type == "Feature Type Analysis" and self.algorithm in ["advanced", "comprehensive"]:
            # Create feature type analysis for advanced algorithms
            ax = self.figure.add_subplot(111)
            
            # Group features by type
            feature_types = {}
            for col in encoded_columns:
                if 'topic_lda' in col:
                    feature_types.setdefault('LDA Topics', []).append(col)
                elif 'topic_nmf' in col:
                    feature_types.setdefault('NMF Topics', []).append(col)
                elif 'semantic_cluster' in col:
                    feature_types.setdefault('Semantic Clusters', []).append(col)
                elif 'domain_' in col:
                    feature_types.setdefault('Domain Concepts', []).append(col)
                elif 'ngram_' in col:
                    feature_types.setdefault('Key N-grams', []).append(col)
                elif 'entity_' in col:
                    feature_types.setdefault('Named Entities', []).append(col)
                else:
                    feature_types.setdefault('Basic Features', []).append(col)
            
            # Create bar chart of feature types
            types = list(feature_types.keys())
            counts = [len(feature_types[t]) for t in types]
            
            bars = ax.bar(types, counts, color=['#3498DB', '#E74C3C', '#2ECC71', '#F39C12', '#9B59B6', '#1ABC9C', '#34495E'][:len(types)])
            ax.set_title(f"Feature Types Created by {self.algorithm.title()} Algorithm")
            ax.set_ylabel("Number of Features")
            ax.set_xlabel("Feature Type")
            
            # Add value labels on bars
            for bar, count in zip(bars, counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{count}', ha='center', va='bottom')
            
            # Rotate x-axis labels if needed
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        # Update the canvas
        plt.tight_layout()
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
            
            # Reapply encoding with current algorithm
            self.encoded_df = get_ohe(self.original_df.copy(), self.encoded_column, 
                                     self.binary_format, self.algorithm)
            
            # Update all tabs
            self.update_all_tabs()
            
            # Show confirmation
            QMessageBox.information(
                self,
                "Format Changed",
                f"Encoding format changed to {selected_format}"
            )

    def change_algorithm(self):
        """Change the algorithm and reapply encoding"""
        algorithm_map = {0: "basic", 1: "advanced", 2: "comprehensive"}
        selected_algorithm = algorithm_map[self.algorithm_selector.currentIndex()]
        
        # Only update if algorithm has changed
        if selected_algorithm != self.algorithm:
            self.algorithm = selected_algorithm
            
            # Reapply encoding with new algorithm
            self.encoded_df = get_ohe(self.original_df.copy(), self.encoded_column, 
                                     self.binary_format, self.algorithm)
            
            # Update all tabs
            self.update_all_tabs()
            
            # Show confirmation
            QMessageBox.information(
                self,
                "Algorithm Changed",
                f"Encoding algorithm changed to {selected_algorithm.title()}"
            )
    
    def update_all_tabs(self):
        """Update all tabs when encoding changes"""
        # Update encoded data tab
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
        
        # Update insights
        self.update_insights()
        
        # Update visualization options
        self.update_viz_options()
        
        # Update visualization
        self.update_visualization()
    
    def update_viz_options(self):
        """Update visualization options based on current algorithm"""
        current_viz = self.viz_selector.currentText()
        self.viz_selector.clear()
        
        viz_options = ["Value Counts", "Correlation Heatmap"]
        if self.algorithm in ["advanced", "comprehensive"]:
            viz_options.append("Feature Type Analysis")
        
        self.viz_selector.addItems(viz_options)
        
        # Try to keep the same visualization if possible
        for i, option in enumerate(viz_options):
            if option == current_viz:
                self.viz_selector.setCurrentIndex(i)
                break
    
    def update_insights(self):
        """Update the algorithm insights tab"""
        new_columns = [col for col in self.encoded_df.columns if col.startswith('has_')]
        
        insights = f"""
=== {self.algorithm.title()} Algorithm Insights ===

Dataset Overview:
• Total records: {len(self.encoded_df)}
• Original column: {self.encoded_column}
• Features created: {len(new_columns)}
• Binary format: {self.binary_format}

Algorithm Details:
"""
        
        if self.algorithm == "basic":
            insights += """
Basic Frequency Algorithm:
• Uses simple word frequency analysis
• Extracts top 10 most common words/categories
• Good for: Simple categorical data, basic text analysis
• Limitations: Misses semantic relationships, synonyms, themes

How it works:
1. Tokenizes text and removes stopwords
2. Counts word frequencies
3. Creates binary features for most frequent words
4. Fast and lightweight approach
"""
        elif self.algorithm == "advanced":
            insights += """
Advanced Academic Algorithm:
• Uses sophisticated NLP and ML techniques:
  - Topic Modeling (LDA & NMF)
  - Semantic clustering with TF-IDF
  - N-gram extraction
  - Named Entity Recognition (if available)
• Good for: Complex text analysis, theme detection
• Benefits: Captures semantic relationships, identifies topics

How it works:
1. Applies multiple academic algorithms in parallel
2. Extracts latent topics using probabilistic models
3. Groups semantically related words into clusters
4. Identifies key phrases and entities
5. Creates features based on conceptual understanding
"""
        elif self.algorithm == "comprehensive":
            insights += """
Comprehensive Analysis:
• Combines ALL available methods:
  - Topic Modeling (LDA & NMF)
  - Semantic clustering
  - N-gram extraction
  - Named Entity Recognition
  - Domain-specific concept detection
• Best for: Research, detailed analysis, maximum insight
• Benefits: Most complete semantic understanding

How it works:
1. Runs all advanced algorithms simultaneously
2. Extracts maximum number of meaningful features
3. Identifies cross-cutting themes and relationships
4. Provides richest feature representation
5. Ideal for discovering hidden patterns
"""
        
        # Add feature breakdown
        if new_columns:
            insights += f"""
Features Created ({len(new_columns)} total):
"""
            
            # Group features by type for advanced algorithms
            if self.algorithm in ["advanced", "comprehensive"]:
                feature_types = {}
                for col in new_columns:
                    if 'topic_lda' in col:
                        feature_types.setdefault('LDA Topics', []).append(col)
                    elif 'topic_nmf' in col:
                        feature_types.setdefault('NMF Topics', []).append(col)
                    elif 'semantic_cluster' in col:
                        feature_types.setdefault('Semantic Clusters', []).append(col)
                    elif 'domain_' in col:
                        feature_types.setdefault('Domain Concepts', []).append(col)
                    elif 'ngram_' in col:
                        feature_types.setdefault('Key N-grams', []).append(col)
                    elif 'entity_' in col:
                        feature_types.setdefault('Named Entities', []).append(col)
                    else:
                        feature_types.setdefault('Basic Features', []).append(col)
                
                for ftype, features in feature_types.items():
                    insights += f"\n{ftype} ({len(features)}):\n"
                    for feature in features[:5]:  # Show first 5
                        coverage = self.calculate_coverage(feature)
                        insights += f"  • {feature}: {coverage:.1f}% coverage\n"
                    if len(features) > 5:
                        insights += f"  ... and {len(features) - 5} more\n"
            else:
                # Basic algorithm - show all features
                for feature in new_columns[:10]:  # Show first 10
                    coverage = self.calculate_coverage(feature)
                    insights += f"• {feature}: {coverage:.1f}% coverage\n"
                if len(new_columns) > 10:
                    insights += f"... and {len(new_columns) - 10} more\n"
        
        # Add recommendations
        insights += f"""
Recommendations:
"""
        if self.algorithm == "basic":
            insights += """
• Consider upgrading to Advanced for better semantic understanding
• Good for simple categorical data and quick analysis
• May miss important relationships in complex text data
"""
        elif self.algorithm == "advanced":
            insights += """
• Excellent balance of sophistication and performance
• Captures most important semantic relationships
• Good for production use and detailed analysis
"""
        elif self.algorithm == "comprehensive":
            insights += """
• Maximum insight extraction from your data
• Best for research and exploratory analysis
• Use correlation analysis to identify redundant features
• Consider feature selection for production deployment
"""
        
        self.insights_text.setPlainText(insights)
    
    def calculate_coverage(self, feature_name):
        """Calculate the coverage percentage of a feature"""
        if self.binary_format == "numeric":
            return (self.encoded_df[feature_name] == 1).sum() / len(self.encoded_df) * 100
        else:
            return (self.encoded_df[feature_name] == "Yes").sum() / len(self.encoded_df) * 100

def visualize_ohe(df, column, binary_format="numeric", algorithm="basic"):
    """
    Visualize the one-hot encoding of a column in a dataframe.
    
    Args:
        df (pd.DataFrame): The original dataframe
        column (str): The column to encode and visualize
        binary_format (str): Format for encoding - "numeric" for 1/0 or "text" for "Yes"/"No"
        algorithm (str): Algorithm to use - "basic", "advanced", or "comprehensive"
        
    Returns:
        QMainWindow: The visualization window
    """
    # Create a copy to avoid modifying the original
    original_df = df.copy()
    
    # Apply one-hot encoding with selected algorithm
    encoded_df = get_ohe(original_df, column, binary_format, algorithm)
    
    # Create and show the visualization
    vis = OneHotEncodingVisualization(original_df, encoded_df, column, binary_format, algorithm)
    vis.show()
    
    return vis


def test_ohe():
    """
    Test the one-hot encoding function with sample dataframes for both text and categorical data.
    Tests both numeric (1/0) and text (Yes/No) encoding formats and different algorithms.
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
    
    # Test basic algorithm
    print("\n----- Testing Basic Algorithm -----")
    basic_result = get_ohe(text_df.copy(), 'text', binary_format="numeric", algorithm="basic")
    basic_features = [col for col in basic_result.columns if col.startswith('has_')]
    print(f"Basic algorithm created {len(basic_features)} features")
    
    # Test advanced algorithm
    print("\n----- Testing Advanced Algorithm -----")
    try:
        advanced_result = get_ohe(text_df.copy(), 'text', binary_format="numeric", algorithm="advanced")
        advanced_features = [col for col in advanced_result.columns if col.startswith('has_')]
        print(f"Advanced algorithm created {len(advanced_features)} features")
    except Exception as e:
        print(f"Advanced algorithm failed: {e}")
    
    # Test comprehensive algorithm
    print("\n----- Testing Comprehensive Algorithm -----")
    try:
        comprehensive_result = get_ohe(text_df.copy(), 'text', binary_format="numeric", algorithm="comprehensive")
        comprehensive_features = [col for col in comprehensive_result.columns if col.startswith('has_')]
        print(f"Comprehensive algorithm created {len(comprehensive_features)} features")
    except Exception as e:
        print(f"Comprehensive algorithm failed: {e}")
    
    print("\nText data tests completed!")


def test_advanced_ai_example():
    """Test with AI-related text to demonstrate semantic understanding"""
    print("\n===== Testing AI/ML Text Analysis =====")
    
    ai_data = {
        'description': [
            "Machine learning engineer developing neural networks for computer vision",
            "AI researcher working on natural language processing and transformers", 
            "Data scientist implementing deep learning algorithms for analytics",
            "Software engineer building recommendation systems with collaborative filtering",
            "ML ops engineer deploying artificial intelligence models to production"
        ]
    }
    
    df = pd.DataFrame(ai_data)
    
    print("Testing different algorithms on AI-related text:")
    
    # Test all algorithms
    for algorithm in ["basic", "advanced", "comprehensive"]:
        print(f"\n--- {algorithm.title()} Algorithm ---")
        try:
            result = get_ohe(df.copy(), 'description', algorithm=algorithm)
            features = [col for col in result.columns if col.startswith('has_')]
            print(f"Created {len(features)} features")
            
            # Show AI-related features
            ai_features = [f for f in features if any(term in f.lower() for term in ['ai', 'machine', 'learning', 'neural', 'deep'])]
            if ai_features:
                print(f"AI-related features found: {len(ai_features)}")
                for feature in ai_features[:3]:  # Show first 3
                    print(f"  • {feature}")
            else:
                print("No explicit AI-related features in names (may be captured in topics)")
                
        except Exception as e:
            print(f"Failed: {e}")
    
    print("\nAI example test completed!")


if __name__ == "__main__":
    # Run tests
    test_ohe()
    test_advanced_ai_example()
    
    # Test the visualization with different algorithms
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
        
        # Show visualization with advanced algorithm
        vis = visualize_ohe(df, 'text', binary_format="numeric", algorithm="advanced")
        
        # Start the application
        sys.exit(app.exec())
