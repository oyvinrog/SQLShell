import pandas as pd
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QTableView, QHeaderView, QLabel, QFrame, QScrollArea
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QPalette, QBrush

class EntropyProfiler(QObject):
    """Class to calculate entropy of columns in a dataframe"""
    progress_updated = pyqtSignal(int, str)  # Signal for progress reporting
    
    def __init__(self):
        super().__init__()
    
    def calculate_entropy(self, series):
        """Calculate Shannon entropy for a series of values"""
        # Handle NaN values by dropping them
        series = series.dropna()
        
        if len(series) == 0:
            return 0.0
            
        # For numerical data with many unique values, bin the data
        if series.dtype.kind in 'ifc' and series.nunique() > 10:
            # Create bins (10 bins by default)
            series = pd.cut(series, bins=10)
        
        # Calculate value counts and probabilities
        value_counts = series.value_counts(normalize=True)
        
        # Calculate entropy: -sum(p * log2(p))
        entropy = -np.sum(value_counts * np.log2(value_counts))
        return entropy
    
    def normalize_entropy(self, entropy_value, max_entropy):
        """Normalize entropy value to 0-1 range"""
        if max_entropy == 0:
            return 0.0
        return entropy_value / max_entropy
    
    def profile(self, df):
        """
        Profile a dataframe to identify the most important columns based on entropy.
        
        Args:
            df: pandas DataFrame to analyze
            
        Returns:
            DataFrame with columns ranked by importance (entropy)
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame")
        
        if df.empty:
            return pd.DataFrame(columns=['column', 'entropy', 'normalized_entropy', 'importance'])
        
        results = []
        total_columns = len(df.columns)
        
        # Calculate entropy for each column
        for i, column in enumerate(df.columns):
            # Emit progress signal (if connected)
            self.progress_updated.emit(int((i / total_columns) * 100), f"Analyzing column: {column}")
            
            try:
                entropy_value = self.calculate_entropy(df[column])
                results.append({
                    'column': column,
                    'entropy': entropy_value
                })
            except Exception as e:
                # Skip columns that can't be analyzed
                continue
        
        # Create results dataframe
        result_df = pd.DataFrame(results)
        
        if result_df.empty:
            return pd.DataFrame(columns=['column', 'entropy', 'normalized_entropy', 'importance'])
        
        # Calculate max entropy for normalization
        max_entropy = result_df['entropy'].max()
        
        # Add normalized entropy
        result_df['normalized_entropy'] = result_df['entropy'].apply(
            lambda x: self.normalize_entropy(x, max_entropy)
        )
        
        # Rank by importance (normalized entropy)
        result_df = result_df.sort_values(by='normalized_entropy', ascending=False)
        
        # Add importance label
        def get_importance(value):
            if value >= 0.8:
                return "High"
            elif value >= 0.5:
                return "Medium"
            elif value >= 0.3:
                return "Low"
            else:
                return "Very Low"
        
        result_df['importance'] = result_df['normalized_entropy'].apply(get_importance)
        
        self.progress_updated.emit(100, "Analysis complete")
        return result_df


class EntropyVisualization(QMainWindow):
    """Window to visualize entropy results"""
    
    def __init__(self, results_df, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Column Entropy Profile")
        self.resize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add a title
        title = QLabel("Column Importance Analysis (Entropy-Based)")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Add a description
        description = QLabel(
            "Columns with higher entropy values contain more information and are likely more important for analysis."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Create visual bars representation
        self.create_visual_bars(layout, results_df)
        
        # Create table view
        self.create_table_view(layout, results_df)
    
    def create_visual_bars(self, layout, df):
        """Create horizontal bars representing entropy values"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setLineWidth(1)
        
        # Create a scroll area for the bars
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Content widget for the scroll area
        content_widget = QWidget()
        bars_layout = QVBoxLayout(content_widget)
        
        # Scale for better visualization
        max_width = 500
        
        # Create a bar for each column
        importance_colors = {
            "High": QColor(52, 152, 219),     # Blue
            "Medium": QColor(46, 204, 113),   # Green
            "Low": QColor(241, 196, 15),      # Yellow
            "Very Low": QColor(230, 126, 34)  # Orange
        }
        
        # Header
        header = QLabel("Visualization of Column Importance (by Normalized Entropy)")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-weight: bold; margin-top: 10px;")
        bars_layout.addWidget(header)
        
        for _, row in df.iterrows():
            bar_container = QWidget()
            bar_layout = QVBoxLayout(bar_container)
            bar_layout.setContentsMargins(0, 2, 0, 2)
            
            # Column name and value
            label_text = f"{row['column']}: {row['normalized_entropy']:.3f} ({row['importance']})"
            label = QLabel(label_text)
            bar_layout.addWidget(label)
            
            # Progress bar
            bar_width = int(row['normalized_entropy'] * max_width)
            bar = QFrame()
            bar.setFixedHeight(20)
            bar.setFixedWidth(bar_width)
            bar.setStyleSheet(f"background-color: {importance_colors[row['importance']].name()}; border-radius: 2px;")
            
            # Container to left-align the bar
            bar_container_inner = QWidget()
            bar_container_layout = QHBoxLayout(bar_container_inner)
            bar_container_layout.setContentsMargins(0, 0, 0, 0)
            bar_container_layout.addWidget(bar)
            bar_container_layout.addStretch()
            
            bar_layout.addWidget(bar_container_inner)
            bars_layout.addWidget(bar_container)
        
        bars_layout.addStretch()
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        
        # Add the scroll area to the frame layout
        frame_layout = QVBoxLayout(frame)
        frame_layout.addWidget(scroll_area)
        
        # Add to main layout
        layout.addWidget(frame)
        
        # Set a reasonable maximum height for the scroll area
        if len(df) > 10:
            scroll_area.setMaximumHeight(400)
    
    def create_table_view(self, layout, df):
        """Create a table view showing the entropy results"""
        # Create the model
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(['Column', 'Entropy', 'Normalized Entropy', 'Importance'])
        
        # Set table data
        for index, row in df.iterrows():
            column_item = QStandardItem(str(row['column']))
            entropy_item = QStandardItem(f"{row['entropy']:.4f}")
            norm_entropy_item = QStandardItem(f"{row['normalized_entropy']:.4f}")
            importance_item = QStandardItem(row['importance'])
            
            # Set alignment
            entropy_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            norm_entropy_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            importance_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            
            # Color based on importance
            if row['importance'] == 'High':
                importance_item.setBackground(QBrush(QColor(52, 152, 219)))  # Blue
            elif row['importance'] == 'Medium':
                importance_item.setBackground(QBrush(QColor(46, 204, 113)))  # Green
            elif row['importance'] == 'Low':
                importance_item.setBackground(QBrush(QColor(241, 196, 15)))  # Yellow
            else:  # Very Low
                importance_item.setBackground(QBrush(QColor(230, 126, 34)))  # Orange
            
            model.appendRow([column_item, entropy_item, norm_entropy_item, importance_item])
        
        # Create and configure the table view
        table_view = QTableView()
        table_view.setModel(model)
        table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_view.setAlternatingRowColors(True)
        table_view.setMinimumHeight(200)
        
        layout.addWidget(table_view)


# Function interface for simpler usage
def profile(df):
    """
    Profile a dataframe to identify the most important columns based on entropy.
    
    Args:
        df: pandas DataFrame to analyze
        
    Returns:
        DataFrame with columns ranked by importance (entropy)
    """
    profiler = EntropyProfiler()
    return profiler.profile(df)


def visualize_profile(df):
    """
    Create a visual representation of the entropy profile for a dataframe.
    
    Args:
        df: pandas DataFrame to analyze
        
    Returns:
        A PyQt6 window showing the visualization
    """
    profiler = EntropyProfiler()
    results = profiler.profile(df)
    vis = EntropyVisualization(results)
    vis.show()
    return vis


def test_profile_entropy():
    """Test the entropy profiler with a sample dataframe"""
    import sys
    
    # Create a QApplication instance if one doesn't exist
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Generate a random dataframe with some columns with different distributions
    np.random.seed(42)  # For reproducibility
    
    # Create a dataframe with columns of varying entropy levels
    df = pd.DataFrame({
        'uniform': np.random.randint(0, 100, size=1000),  # High entropy (uniform distribution)
        'normal': np.random.normal(50, 10, size=1000),    # Medium entropy
        'binary': np.random.choice([0, 1], size=1000),    # Low entropy (only two values)
        'constant': np.ones(1000),                        # Zero entropy (same value)
        'skewed': np.random.exponential(5, size=1000),     # Skewed distribution,
        'categorical': np.random.choice(['A', 'B', 'C'], size=1000),  # Categorical data
        'mixed': np.random.randint(0, 100, size=1000) * np.random.choice([0, 1], size=1000),  # Mixed data
        'datetime': pd.date_range('2020-01-01', periods=1000),  # Datetime data
        'text': pd.Series(['a', 'b', 'c'] * 334)[:1000],  # Text data  
        'boolean': np.random.choice([True, False], size=1000), # Boolean data
        # add 20 more dummy columns with different distributions
        'dummy1': np.random.randint(0, 100, size=1000),
        'dummy2': np.random.normal(50, 10, size=1000),
        'dummy3': np.random.choice([0, 1], size=1000),
        'dummy4': np.ones(1000),
        'dummy5': np.random.exponential(5, size=1000),
        # add 20 more dummy columns with different distributions
        'dummy6': np.random.randint(0, 100, size=1000),
        'dummy7': np.random.normal(50, 10, size=1000),
        'dummy8': np.random.choice([0, 1], size=1000),
        'dummy9': np.ones(1000),
        'dummy10': np.random.exponential(5, size=1000),
        
    })
    
    # Add a categorical column with few categories
    df['category'] = np.random.choice(['A', 'B', 'C'], size=1000)
    
    # Calculate and display profile information
    print("Entropy Profile Results:")
    profiler = EntropyProfiler()
    result = profiler.profile(df)
    print(result)
    
    # Visualize the results
    vis = visualize_profile(df)
    
    # Start the application event loop
    app.exec()


if __name__ == "__main__":
    test_profile_entropy()