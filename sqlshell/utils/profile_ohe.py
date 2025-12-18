import pandas as pd
import numpy as np
import os
import sys

# Flag to track if NLTK is available
NLTK_AVAILABLE = False

def _setup_nltk_data_path():
    """Configure NLTK to find data in bundled location (for PyInstaller builds)"""
    import nltk
    
    # Check if running from a PyInstaller bundle
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        bundle_dir = sys._MEIPASS
        nltk_data_path = os.path.join(bundle_dir, 'nltk_data')
        if os.path.exists(nltk_data_path):
            nltk.data.path.insert(0, nltk_data_path)
    
    # Also check relative to the application
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    possible_paths = [
        os.path.join(app_dir, 'nltk_data'),
        os.path.join(os.path.dirname(app_dir), 'nltk_data'),
    ]
    for path in possible_paths:
        if os.path.exists(path) and path not in nltk.data.path:
            nltk.data.path.insert(0, path)

try:
    import nltk
    _setup_nltk_data_path()
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    
    # Try to find required NLTK data, download if missing
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True)
        except Exception:
            pass  # Download failed silently - NLTK features will be unavailable
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        try:
            nltk.download('stopwords', quiet=True)
        except Exception:
            pass  # Download failed silently - NLTK features will be unavailable
    try:
        nltk.data.find('tokenizers/punkt_tab/english')
    except LookupError:
        try:
            nltk.download('punkt_tab', quiet=True)
        except Exception:
            pass  # Download failed silently - NLTK features will be unavailable
    
    # Test if NLTK is actually working
    try:
        _ = stopwords.words('english')
        _ = word_tokenize("test")
        NLTK_AVAILABLE = True
    except Exception:
        NLTK_AVAILABLE = False
        
except ImportError:
    NLTK_AVAILABLE = False


def _simple_tokenize(text):
    """Simple fallback tokenizer when NLTK is not available"""
    import re
    # Simple word tokenization using regex
    return re.findall(r'\b[a-zA-Z]+\b', text.lower())


def _get_simple_stopwords():
    """Return a basic set of English stopwords when NLTK is not available"""
    return {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought',
        'used', 'it', 'its', 'this', 'that', 'these', 'those', 'i', 'me', 'my',
        'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
        'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her',
        'hers', 'herself', 'they', 'them', 'their', 'theirs', 'themselves',
        'what', 'which', 'who', 'whom', 'when', 'where', 'why', 'how', 'all',
        'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such',
        'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
        'just', 'also', 'now', 'here', 'there', 'then', 'once', 'if', 'because',
        'while', 'although', 'though', 'after', 'before', 'since', 'until', 'unless'
    }

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
        # Get stopwords (use NLTK if available, otherwise fallback)
        if NLTK_AVAILABLE:
            stop_words = set(stopwords.words('english'))
        else:
            stop_words = _get_simple_stopwords()
        
        # Tokenize and count words
        word_counts = {}
        for text in dataframe[column]:
            if isinstance(text, str):
                # Tokenize and convert to lowercase (use NLTK if available, otherwise fallback)
                if NLTK_AVAILABLE:
                    words = word_tokenize(text.lower())
                else:
                    words = _simple_tokenize(text)
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
                           QMessageBox, QHeaderView, QApplication, QTextEdit,
                           QDialog)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

class NumericTableItem(QTableWidgetItem):
    """Table item that sorts numerically using the stored value."""
    def __init__(self, value, fmt="{:.3f}"):
        display_value = fmt.format(value) if isinstance(value, (int, float, np.number)) else str(value)
        super().__init__(display_value)
        self._value = value

    def __lt__(self, other):
        try:
            return float(self._value) < float(other._value)
        except Exception:
            return super().__lt__(other)


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


def find_related_ohe_features(df, target_column, sample_size=2000, max_features=20):
    """
    Find one-hot encoded signals in other columns that help predict the target column.
    
    Returns a dictionary with ranked features and analysis metadata.
    """
    if target_column not in df.columns:
        raise ValueError(f"Column '{target_column}' not found in dataframe")
    
    if df.empty:
        raise ValueError("No data available to analyze")
    
    # Drop rows without the target to avoid noisy correlations
    df = df.dropna(subset=[target_column])
    total_rows = len(df)
    if total_rows == 0:
        raise ValueError(f"Column '{target_column}' has no non-null values to analyze")
    
    # Sample for speed on large datasets
    if len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)
    df = df.reset_index(drop=True)
    
    # Keep a copy of the sampled/cleaned data for drilldowns
    sample_df = df.copy()
    target_raw = sample_df[target_column].reset_index(drop=True)
    target_series = target_raw.copy()
    unique_target_values = target_series.dropna().nunique()
    if unique_target_values < 2:
        raise ValueError(f"Column '{target_column}' needs at least 2 distinct values for analysis")
    
    # Prepare target for correlation (bin dense numeric targets)
    target_discretized = False
    if pd.api.types.is_numeric_dtype(target_series) and unique_target_values > 15:
        try:
            target_series = pd.qcut(target_series, q=5, duplicates='drop')
        except Exception:
            # Fallback to equal-width bins
            target_series = pd.cut(target_series, bins=5, duplicates='drop')
        target_discretized = True
    
    # Ensure categorical targets can accept the placeholder before filling missing values
    if not pd.api.types.is_numeric_dtype(target_series):
        if pd.api.types.is_categorical_dtype(target_series):
            if "_MISSING_" not in target_series.cat.categories:
                target_series = target_series.cat.add_categories(["_MISSING_"])
        target_series = target_series.fillna("_MISSING_")
    
    if pd.api.types.is_numeric_dtype(target_series):
        target_numeric = pd.to_numeric(target_series, errors='coerce')
        target_numeric = target_numeric.fillna(target_numeric.mean())
    else:
        target_numeric = pd.Categorical(target_series).codes.astype(float)
        target_numeric = pd.Series(target_numeric, index=target_series.index)
    
    candidate_columns = [col for col in df.columns if col != target_column]
    results = []
    skipped_columns = []
    max_categories = 60  # Avoid exploding one-hot columns on very high-cardinality categoricals
    
    # Iterate over candidate feature columns
    for col in candidate_columns:
        series = df[col]
        non_null_unique = series.dropna().nunique()
        if non_null_unique < 2:
            continue
        
        string_values = None
        
        working_subset = df[[target_column, col]].copy()
        notes = []
        
        # Detect text-like columns so we don't skip them even with many unique values
        is_text = False
        try:
            string_values = series.dropna().astype(str)
            if len(string_values) > 0:
                sample_values = string_values.head(200)
                avg_length = sample_values.str.len().mean()
                contains_spaces = any(' ' in val for val in sample_values)
                if contains_spaces or (pd.notna(avg_length) and avg_length > 15):
                    is_text = True
        except Exception:
            # If detection fails, assume it's not text
            is_text = False
        
        # Prepare the column for one-hot encoding
        if pd.api.types.is_numeric_dtype(series):
            # Bin numeric data to make it suitable for OHE
            try:
                bins = min(4, max(2, series.dropna().nunique()))
                working_subset[col] = pd.qcut(series, q=bins, duplicates='drop').astype(str)
            except Exception:
                try:
                    bins = min(4, max(2, series.dropna().nunique()))
                    working_subset[col] = pd.cut(series, bins=bins, duplicates='drop').astype(str)
                except Exception as e:
                    skipped_columns.append((col, f"binning failed: {str(e)}"))
                    continue
            notes.append("numeric binned")
        else:
            unique_count = string_values.nunique() if string_values is not None else non_null_unique
            if not is_text and unique_count > max_categories:
                skipped_columns.append((col, f"high cardinality ({unique_count} unique values)"))
                continue
            if pd.api.types.is_categorical_dtype(series):
                # Ensure the special missing marker exists to avoid setitem errors
                if "_MISSING_" not in series.cat.categories:
                    series = series.cat.add_categories(["_MISSING_"])
                series = series.fillna("_MISSING_")
            else:
                series = series.fillna("_MISSING_")
            working_subset[col] = series
        
        # Apply basic OHE to the candidate column
        try:
            encoded_df = get_ohe(working_subset.copy(), col, binary_format="numeric", algorithm="basic")
        except Exception as e:
            skipped_columns.append((col, f"encoding failed: {str(e)}"))
            continue
        
        encoded_cols = [c for c in encoded_df.columns if c.startswith('has_') or c.startswith('is_')]
        if not encoded_cols:
            continue
        
        # Align target values and ensure numeric dtype
        encoded_df = encoded_df.reset_index(drop=True)
        target_aligned = target_numeric.reset_index(drop=True)
        
        for feature in encoded_cols:
            feature_series = pd.to_numeric(encoded_df[feature], errors='coerce').reset_index(drop=True)
            if feature_series.nunique() < 2:
                continue
            corr_val = feature_series.corr(target_aligned)
            if pd.isna(corr_val):
                continue
            
            coverage = float(feature_series.mean()) * 100.0  # Percentage of rows with feature=1
            results.append({
                "feature": feature,
                "source_column": col,
                "correlation": corr_val,
                "abs_correlation": abs(corr_val),
                "coverage": coverage,
                "note": "; ".join(notes) if notes else "",
                "feature_series": feature_series
            })
    
    # Rank by absolute correlation strength
    results = sorted(results, key=lambda x: x["abs_correlation"], reverse=True)
    if max_features:
        results = results[:max_features]
    
    return {
        "results": results,
        "sample_size": len(df),
        "total_rows": total_rows,
        "target_discretized": target_discretized,
        "columns_considered": len(candidate_columns),
        "skipped_columns": skipped_columns,
        "target_values": target_raw,
        "sample_df": sample_df
    }


def build_drilldown_query(table_name, source_column, feature_name):
    """Build a SELECT query for drilldown based on an encoded feature."""
    if not table_name:
        return None
    
    # Quote the column if it has special characters
    if any(ch in source_column for ch in (' ', '-', '.')):
        col_expr = f'"{source_column}"'
    else:
        col_expr = source_column
    
    if feature_name.startswith("has_"):
        token = feature_name[len("has_"):]
        token = token.replace("'", "''")
        condition = f"{col_expr} LIKE '%{token}%'"
    elif feature_name.startswith("is_"):
        token = feature_name[len("is_"):]
        token = token.replace("'", "''")
        condition = f"{col_expr} = '{token}'"
    else:
        token = feature_name.replace("'", "''")
        condition = f"{col_expr} = '{token}'"
    
    return f"SELECT *\nFROM {table_name}\nWHERE {condition}"


class RelatedOneHotEncodingsWindow(QMainWindow):
    """Simple window to display related one-hot encodings for a target column."""
    def __init__(self, target_column, analysis_result, table_name=None, drill_query_callback=None):
        super().__init__()
        self.setWindowTitle(f"Related One-Hot Encodings - {target_column}")
        self.setGeometry(120, 120, 900, 700)
        self.analysis_result = analysis_result
        self.target_column = target_column
        self.target_values = analysis_result.get("target_values")
        self.sample_df = analysis_result.get("sample_df")
        self.results = analysis_result.get("results", [])
        self.table_name = table_name
        self.drill_query_callback = drill_query_callback
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Summary text
        sampled_text = ""
        if analysis_result["sample_size"] < analysis_result["total_rows"]:
            sampled_text = f" (sampled {analysis_result['sample_size']:,} of {analysis_result['total_rows']:,} rows)"
        summary_label = QLabel(
            f"Analyzed {analysis_result['columns_considered']} columns{sampled_text} to find one-hot signals "
            f"that help predict '{target_column}'."
        )
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)
        
        if analysis_result["target_discretized"]:
            discretize_label = QLabel("Numeric target was auto-binned to make correlations meaningful.")
            discretize_label.setStyleSheet("color: #7F8C8D;")
            layout.addWidget(discretize_label)
        
        # Results table
        results = self.results
        self.table = QTableWidget(len(results), 5)
        self.table.setHorizontalHeaderLabels([
            "Rank", "Source Column", "Encoded Feature", "Correlation", "Coverage"
        ])
        
        for i, res in enumerate(results):
            rank_item = NumericTableItem(i + 1, fmt="{:.0f}")
            rank_item.setFlags(rank_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, rank_item)
            
            source_item = QTableWidgetItem(res["source_column"])
            source_item.setFlags(source_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 1, source_item)
            
            feature_item = QTableWidgetItem(res["feature"])
            feature_item.setToolTip(res.get("note", ""))
            feature_item.setFlags(feature_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 2, feature_item)
            
            corr_item = NumericTableItem(res["correlation"])
            corr_item.setFlags(corr_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 3, corr_item)
            
            coverage_item = NumericTableItem(res["coverage"], fmt="{:.1f}%")
            coverage_item.setFlags(coverage_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 4, coverage_item)
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.table.sortItems(3, Qt.SortOrder.DescendingOrder)
        self.table.cellDoubleClicked.connect(self.show_feature_drilldown)
        layout.addWidget(self.table, 1)
        
        # Additional context and skipped columns info
        notes = [
            "Higher absolute correlation means the encoded feature aligns strongly with the target classes.",
            "Coverage shows how often the encoded feature is present in the sampled data.",
            "Double-click any row to compare target values with and without that encoded feature."
        ]
        if analysis_result["skipped_columns"]:
            skipped_preview = ", ".join(f"{col} ({reason})" for col, reason in analysis_result["skipped_columns"][:3])
            more_skipped = ""
            if len(analysis_result["skipped_columns"]) > 3:
                more_skipped = f" ... and {len(analysis_result['skipped_columns']) - 3} more"
            notes.append(f"Skipped columns: {skipped_preview}{more_skipped}")
        
        notes_label = QLabel("\n".join(f"• {n}" for n in notes))
        notes_label.setWordWrap(True)
        notes_label.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(notes_label)

    def show_feature_drilldown(self, row, column):
        """Show a small bar chart comparing target values with/without the encoded feature."""
        results = self.results
        if not results:
            return
        
        # Use table values to find the correct result even after sorting
        source_text = self.table.item(row, 1).text() if self.table.item(row, 1) else None
        feature_text = self.table.item(row, 2).text() if self.table.item(row, 2) else None
        if not source_text or not feature_text:
            return
        res = next((r for r in results
                    if r.get("source_column") == source_text and r.get("feature") == feature_text),
                   None)
        if res is None:
            QMessageBox.information(self, "Drilldown Unavailable", "Could not match the selected feature.")
            return
        
        feature_series = res.get("feature_series")
        target_series = self.target_values
        source_col = res.get("source_column", "")
        feature_name = res.get("feature", "")
        
        if feature_series is None or target_series is None:
            QMessageBox.information(self, "Drilldown Unavailable", "Could not load data for this feature.")
            return
        
        # Align lengths defensively
        min_len = min(len(feature_series), len(target_series))
        feature_series = pd.to_numeric(feature_series[:min_len], errors='coerce').fillna(0)
        target_series = target_series[:min_len]
        
        mask_present = feature_series != 0
        mask_absent = ~mask_present
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{feature_name} vs {self.target_column}")
        dialog.resize(780, 540)
        layout = QVBoxLayout(dialog)
        
        fig = plt.Figure(figsize=(7.5, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        layout.addWidget(canvas)
        
        if pd.api.types.is_numeric_dtype(target_series):
            target_numeric = pd.to_numeric(target_series, errors='coerce')
            present_mean = target_numeric[mask_present].mean()
            absent_mean = target_numeric[mask_absent].mean()
            bars = ["Feature Present", "Feature Absent"]
            values = [present_mean, absent_mean]
            ax.bar(bars, values, color=["#2E86DE", "#95A5A6"])
            ax.set_ylabel(f"Average {self.target_column}")
            ax.set_title(f"{feature_name} (from {source_col})")
            for idx, val in enumerate(values):
                ax.text(idx, val, f"{val:.2f}", ha='center', va='bottom')
        else:
            # Compare distribution of top categories
            target_str = target_series.astype(str)
            present_counts = target_str[mask_present].value_counts(normalize=True).head(5)
            absent_counts = target_str[mask_absent].value_counts(normalize=True).head(5)
            categories = list(dict.fromkeys(list(present_counts.index) + list(absent_counts.index)))
            x = np.arange(len(categories))
            width = 0.4
            ax.bar(x - width/2, [present_counts.get(cat, 0) for cat in categories],
                   width, label="Feature Present", color="#2E86DE")
            ax.bar(x + width/2, [absent_counts.get(cat, 0) for cat in categories],
                   width, label="Feature Absent", color="#95A5A6")
            ax.set_xticks(x)
            ax.set_xticklabels(categories, rotation=30, ha='right')
            ax.set_ylabel("Share of rows")
            ax.set_title(f"{feature_name} (from {source_col})")
            ax.legend()
        
        fig.tight_layout()
        
        # Drilldown button to open matching rows in the editor
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        open_btn = QPushButton("Open matching rows in editor")
        open_btn.clicked.connect(lambda: self.run_drilldown_query(feature_name, source_col))
        button_layout.addWidget(open_btn)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        dialog.exec()

    def run_drilldown_query(self, feature_name, source_col):
        """Send a drilldown query to the main editor if possible."""
        if not self.drill_query_callback:
            QMessageBox.information(self, "Action Unavailable", "Cannot run query from here.")
            return
        
        query = build_drilldown_query(self.table_name, source_col, feature_name)
        if not query:
            QMessageBox.information(self, "Table Not Found", "Could not determine the source table to query.")
            return
        
        self.drill_query_callback(query)


def visualize_related_ohe(df, target_column, sample_size=2000, max_features=20, 
                          table_name=None, drill_query_callback=None):
    """
    Visualize related one-hot encodings that correlate with/predict a target column.
    
    Returns:
        QMainWindow: The visualization window, or None if no features were found.
    """
    analysis_result = find_related_ohe_features(df, target_column, sample_size, max_features)
    if not analysis_result["results"]:
        QMessageBox.information(
            None,
            "No Predictive Encodings Found",
            f"No related one-hot encodings found for '{target_column}'. "
            "Try a different column or increase variability in the data."
        )
        return None
    
    vis = RelatedOneHotEncodingsWindow(
        target_column, analysis_result, table_name=table_name, drill_query_callback=drill_query_callback
    )
    vis.show()
    return vis

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
