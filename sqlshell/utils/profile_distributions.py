import pandas as pd
import numpy as np
import scipy.stats as stats
import matplotlib
matplotlib.use('qtagg')  # Set the backend before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QTableView, QHeaderView, QLabel, QFrame, QScrollArea, QTabWidget,
    QComboBox, QPushButton, QSplitter
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush


class DistributionProfiler(QObject):
    """Class to analyze distributions of columns in a dataframe"""
    progress_updated = pyqtSignal(int, str)  # Signal for progress reporting
    
    def __init__(self):
        super().__init__()
        
        # Define common distributions to test
        self.distributions = [
            {'name': 'normal', 'distribution': stats.norm, 'color': 'blue'},
            {'name': 'uniform', 'distribution': stats.uniform, 'color': 'green'},
            {'name': 'exponential', 'distribution': stats.expon, 'color': 'red'},
            {'name': 'lognormal', 'distribution': stats.lognorm, 'color': 'purple'},
            {'name': 'gamma', 'distribution': stats.gamma, 'color': 'orange'},
            {'name': 'beta', 'distribution': stats.beta, 'color': 'brown'},
        ]
    
    def get_best_distribution(self, data):
        """Find the best distribution that fits the data"""
        # Remove NaNs
        data = data.dropna()
        
        if len(data) == 0:
            return None, None, None
            
        # For categorical or non-numeric data, return None
        if not pd.api.types.is_numeric_dtype(data):
            return None, None, None
            
        # For constant data, return a simple result
        if data.nunique() == 1:
            return 'constant', None, 1.0
        
        # If too few unique values, may not be appropriate for distribution fitting
        if data.nunique() < 5:
            return 'discrete', None, None
        
        best_distribution = None
        best_params = None
        best_sse = np.inf
        
        # Get histogram data
        hist, bin_edges = np.histogram(data, bins='auto', density=True)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Try each distribution
        for dist_info in self.distributions:
            distribution = dist_info['distribution']
            
            try:
                # Fit distribution to data
                params = distribution.fit(data)
                
                # Get PDF values
                arg_params = params[:-2]
                loc = params[-2]
                scale = params[-1]
                
                pdf = distribution.pdf(bin_centers, loc=loc, scale=scale, *arg_params)
                
                # Calculate sum of squared errors
                sse = np.sum((pdf - hist) ** 2)
                
                # Find best fit distribution
                if sse < best_sse:
                    best_distribution = dist_info['name']
                    best_params = params
                    best_sse = sse
                    
            except Exception:
                continue
        
        # Calculate Kolmogorov-Smirnov test for goodness of fit
        if best_distribution and best_params:
            dist = getattr(stats, best_distribution)
            
            # Try to compute K-S test
            try:
                arg_params = best_params[:-2]
                loc = best_params[-2]
                scale = best_params[-1]
                ks_stat, p_value = stats.kstest(data, dist.cdf, args=arg_params, loc=loc, scale=scale)
                return best_distribution, best_params, p_value
            except:
                return best_distribution, best_params, None
        
        return None, None, None
    
    def describe_distribution(self, series):
        """Provide distribution statistics for a series"""
        stats_dict = {}
        
        # Remove NaNs
        series = series.dropna()
        
        if len(series) == 0:
            return {
                'count': 0,
                'distribution': 'empty',
                'goodness_of_fit': None
            }
        
        # Basic statistics
        stats_dict['count'] = len(series)
        stats_dict['unique_count'] = series.nunique()
        stats_dict['missing_count'] = series.isna().sum()
        stats_dict['missing_percentage'] = (series.isna().sum() / len(series)) * 100
        
        # For categorical data
        if not pd.api.types.is_numeric_dtype(series):
            stats_dict['type'] = 'categorical'
            top_values = series.value_counts().head(5).to_dict()
            stats_dict['top_values'] = {str(k): v for k, v in top_values.items()}
            stats_dict['distribution'] = 'categorical'
            return stats_dict
        
        # For numerical data
        stats_dict['type'] = 'numerical'
        stats_dict['min'] = float(series.min())
        stats_dict['max'] = float(series.max())
        stats_dict['mean'] = float(series.mean())
        stats_dict['median'] = float(series.median())
        stats_dict['std'] = float(series.std())
        stats_dict['skewness'] = float(stats.skew(series))
        stats_dict['kurtosis'] = float(stats.kurtosis(series))
        
        # Find best distribution
        best_dist, params, p_value = self.get_best_distribution(series)
        stats_dict['distribution'] = best_dist
        stats_dict['goodness_of_fit'] = p_value
        
        return stats_dict
    
    def profile(self, df):
        """
        Profile a dataframe to identify the distribution characteristics of each column.
        
        Args:
            df: pandas DataFrame to analyze
            
        Returns:
            DataFrame with columns and their distribution profiles
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame")
        
        if df.empty:
            return pd.DataFrame(columns=['column', 'type', 'distribution', 'goodness_of_fit'])
        
        results = []
        total_columns = len(df.columns)
        
        # Analyze each column
        for i, column in enumerate(df.columns):
            # Emit progress signal (if connected)
            self.progress_updated.emit(int((i / total_columns) * 100), f"Analyzing column: {column}")
            
            try:
                stats_dict = self.describe_distribution(df[column])
                stats_dict['column'] = column
                results.append(stats_dict)
            except Exception as e:
                # Skip columns that can't be analyzed
                continue
        
        # Create results dataframe
        result_df = pd.DataFrame(results)
        
        if result_df.empty:
            return pd.DataFrame(columns=['column', 'type', 'distribution', 'goodness_of_fit'])
        
        # Sort by distribution type and column name
        result_df = result_df.sort_values(by=['type', 'column'])
        
        self.progress_updated.emit(100, "Analysis complete")
        return result_df


class MatplotlibCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas for embedding plots in PyQt"""
    def __init__(self, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)


class DistributionVisualization(QMainWindow):
    """Window to visualize distribution results"""
    
    def __init__(self, df, results_df, parent=None):
        super().__init__(parent)
        self.df = df
        self.results_df = results_df
        self.current_column = None
        
        self.setWindowTitle("Column Distribution Profiles")
        self.resize(1000, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Add a title
        title = QLabel("Statistical Distribution Analysis")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title)
        
        # Add a description
        description = QLabel(
            "Analyzing column distributions helps identify data patterns and select appropriate statistical methods."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        main_layout.addWidget(description)
        
        # Create a splitter for table and visualization
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter, 1)
        
        # Create table view
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        self.create_table_view(table_layout)
        splitter.addWidget(table_widget)
        
        # Create visualization section
        vis_widget = QWidget()
        vis_layout = QVBoxLayout(vis_widget)
        self.create_visualization_section(vis_layout)
        splitter.addWidget(vis_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([300, 500])
    
    def create_table_view(self, layout):
        """Create a table view showing the distribution results"""
        # Create the model
        model = QStandardItemModel()
        headers = ['Column', 'Type', 'Distribution', 'Count', 'Unique', 'Missing %']
        if 'skewness' in self.results_df.columns:
            headers.extend(['Mean', 'Median', 'Std', 'Skewness', 'Kurtosis'])
        model.setHorizontalHeaderLabels(headers)
        
        # Set table data
        for _, row in self.results_df.iterrows():
            items = []
            
            # Basic columns present in all rows
            column_item = QStandardItem(str(row['column']))
            type_item = QStandardItem(str(row['type']))
            dist_item = QStandardItem(str(row['distribution']))
            count_item = QStandardItem(str(row['count']))
            unique_item = QStandardItem(str(row.get('unique_count', 'N/A')))
            missing_item = QStandardItem(f"{row.get('missing_percentage', 0):.1f}%")
            
            items.extend([column_item, type_item, dist_item, count_item, unique_item, missing_item])
            
            # Add numerical statistics if available
            if row['type'] == 'numerical':
                mean_item = QStandardItem(f"{row.get('mean', 'N/A'):.2f}")
                median_item = QStandardItem(f"{row.get('median', 'N/A'):.2f}")
                std_item = QStandardItem(f"{row.get('std', 'N/A'):.2f}")
                skew_item = QStandardItem(f"{row.get('skewness', 'N/A'):.2f}")
                kurt_item = QStandardItem(f"{row.get('kurtosis', 'N/A'):.2f}")
                
                items.extend([mean_item, median_item, std_item, skew_item, kurt_item])
            else:
                # Add empty items for categorical data
                for _ in range(5):
                    items.append(QStandardItem(""))
            
            model.appendRow(items)
        
        # Create and configure the table view
        self.table_view = QTableView()
        self.table_view.setModel(model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setMinimumHeight(200)
        
        # Connect selection signal
        self.table_view.selectionModel().selectionChanged.connect(self.on_column_selected)
        
        layout.addWidget(self.table_view)
        
        # Add column selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Select Column:"))
        
        self.column_selector = QComboBox()
        self.column_selector.addItems(self.results_df['column'].tolist())
        self.column_selector.currentTextChanged.connect(self.on_combobox_changed)
        selector_layout.addWidget(self.column_selector)
        
        layout.addLayout(selector_layout)
    
    def create_visualization_section(self, layout):
        """Create the visualization section with tabs for different plots"""
        self.tab_widget = QTabWidget()
        
        # Create tabs for different visualizations
        self.histogram_tab = QWidget()
        self.histogram_layout = QVBoxLayout(self.histogram_tab)
        self.histogram_canvas = MatplotlibCanvas(width=8, height=4)
        self.histogram_layout.addWidget(self.histogram_canvas)
        self.tab_widget.addTab(self.histogram_tab, "Histogram & Density")
        
        self.boxplot_tab = QWidget()
        self.boxplot_layout = QVBoxLayout(self.boxplot_tab)
        self.boxplot_canvas = MatplotlibCanvas(width=8, height=4)
        self.boxplot_layout.addWidget(self.boxplot_canvas)
        self.tab_widget.addTab(self.boxplot_tab, "Box Plot")
        
        self.qq_tab = QWidget()
        self.qq_layout = QVBoxLayout(self.qq_tab)
        self.qq_canvas = MatplotlibCanvas(width=8, height=4)
        self.qq_layout.addWidget(self.qq_canvas)
        self.tab_widget.addTab(self.qq_tab, "Q-Q Plot")
        
        self.ecdf_tab = QWidget()
        self.ecdf_layout = QVBoxLayout(self.ecdf_tab)
        self.ecdf_canvas = MatplotlibCanvas(width=8, height=4)
        self.ecdf_layout.addWidget(self.ecdf_canvas)
        self.tab_widget.addTab(self.ecdf_tab, "Empirical CDF")
        
        # For categorical data
        self.categorical_tab = QWidget()
        self.categorical_layout = QVBoxLayout(self.categorical_tab)
        self.categorical_canvas = MatplotlibCanvas(width=8, height=4)
        self.categorical_layout.addWidget(self.categorical_canvas)
        self.tab_widget.addTab(self.categorical_tab, "Bar Chart")
        
        layout.addWidget(self.tab_widget)
        
        # Stats panel
        self.stats_label = QLabel("Select a column to view distribution statistics")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet("font-family: monospace; background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)
    
    def on_combobox_changed(self, column_name):
        """Handle column selection from combobox"""
        self.visualize_column(column_name)
    
    def on_column_selected(self, selected, deselected):
        """Handle column selection from table"""
        indexes = selected.indexes()
        if indexes:
            # Get the column name from the first column
            row_idx = indexes[0].row()
            column_name = self.table_view.model().item(row_idx, 0).text()
            
            # Update combobox to match
            index = self.column_selector.findText(column_name)
            if index >= 0:
                self.column_selector.setCurrentIndex(index)
            
            self.visualize_column(column_name)
    
    def visualize_column(self, column_name):
        """Visualize the selected column with various plots"""
        if column_name not in self.df.columns:
            return
            
        self.current_column = column_name
        
        # Get column data and stats
        series = self.df[column_name]
        column_stats = self.results_df[self.results_df['column'] == column_name].iloc[0].to_dict()
        
        # Update stats label
        self.update_stats_display(column_stats)
        
        # Check if categorical or numerical
        if column_stats['type'] == 'categorical':
            self.create_categorical_plots(series, column_stats)
            self.tab_widget.setCurrentWidget(self.categorical_tab)
        else:
            self.create_numerical_plots(series, column_stats)
            self.tab_widget.setCurrentWidget(self.histogram_tab)
    
    def update_stats_display(self, stats):
        """Update the statistics display panel"""
        if stats['type'] == 'numerical':
            # Format numerical stats
            stats_text = (
                f"<b>Column:</b> {stats['column']} | <b>Type:</b> {stats['type']} | "
                f"<b>Distribution:</b> {stats['distribution']}\n"
                f"<b>Count:</b> {stats['count']} | <b>Unique:</b> {stats['unique_count']} | "
                f"<b>Missing:</b> {stats['missing_count']} ({stats['missing_percentage']:.1f}%)\n"
                f"<b>Min:</b> {stats['min']:.4g} | <b>Max:</b> {stats['max']:.4g} | "
                f"<b>Mean:</b> {stats['mean']:.4g} | <b>Median:</b> {stats['median']:.4g} | <b>Std:</b> {stats['std']:.4g}\n"
                f"<b>Skewness:</b> {stats['skewness']:.4g} | <b>Kurtosis:</b> {stats['kurtosis']:.4g}"
            )
            
            if stats['goodness_of_fit'] is not None:
                stats_text += f" | <b>Goodness of fit (p-value):</b> {stats['goodness_of_fit']:.4g}"
        else:
            # Format categorical stats
            stats_text = (
                f"<b>Column:</b> {stats['column']} | <b>Type:</b> {stats['type']}\n"
                f"<b>Count:</b> {stats['count']} | <b>Unique:</b> {stats['unique_count']} | "
                f"<b>Missing:</b> {stats['missing_count']} ({stats['missing_percentage']:.1f}%)"
            )
            
            if 'top_values' in stats:
                top_values = stats['top_values']
                stats_text += "\n<b>Top values:</b> "
                stats_text += ", ".join([f"{k} ({v})" for k, v in top_values.items()])
        
        self.stats_label.setText(stats_text)
    
    def create_numerical_plots(self, series, column_stats):
        """Create plots for numerical data"""
        # Clean data
        data = series.dropna()
        
        # Histogram with fitted distribution
        self.histogram_canvas.axes.clear()
        self.histogram_canvas.axes.hist(data, bins='auto', density=True, alpha=0.6, label="Data")
        
        # If we have a fitted distribution, plot it
        if column_stats['distribution'] not in [None, 'discrete', 'constant', 'categorical']:
            # Get the distribution and params
            dist_name = column_stats['distribution']
            
            # Simple estimation for distribution parameters if we don't have them
            # In a real implementation, you would save the parameters from the profiler
            if dist_name == 'normal':
                x = np.linspace(data.min(), data.max(), 1000)
                y = stats.norm.pdf(x, data.mean(), data.std())
                self.histogram_canvas.axes.plot(x, y, 'r-', lw=2, label=f"Fitted {dist_name}")
            elif dist_name == 'uniform':
                x = np.linspace(data.min(), data.max(), 1000)
                y = stats.uniform.pdf(x, data.min(), data.max() - data.min())
                self.histogram_canvas.axes.plot(x, y, 'r-', lw=2, label=f"Fitted {dist_name}")
            elif dist_name == 'exponential':
                x = np.linspace(data.min(), data.max(), 1000)
                y = stats.expon.pdf(x, scale=1/data.mean())
                self.histogram_canvas.axes.plot(x, y, 'r-', lw=2, label=f"Fitted {dist_name}")
            
        self.histogram_canvas.axes.set_title(f"Histogram of {series.name}")
        self.histogram_canvas.axes.set_xlabel("Value")
        self.histogram_canvas.axes.set_ylabel("Density")
        self.histogram_canvas.axes.legend()
        self.histogram_canvas.fig.tight_layout()
        self.histogram_canvas.draw()
        
        # Box plot
        self.boxplot_canvas.axes.clear()
        self.boxplot_canvas.axes.boxplot(data, vert=False)
        self.boxplot_canvas.axes.set_title(f"Box Plot of {series.name}")
        self.boxplot_canvas.axes.set_xlabel("Value")
        self.boxplot_canvas.axes.set_yticks([])
        self.boxplot_canvas.fig.tight_layout()
        self.boxplot_canvas.draw()
        
        # Q-Q plot
        self.qq_canvas.axes.clear()
        stats.probplot(data, dist="norm", plot=self.qq_canvas.axes)
        self.qq_canvas.axes.set_title(f"Q-Q Plot of {series.name} (vs Normal)")
        self.qq_canvas.fig.tight_layout()
        self.qq_canvas.draw()
        
        # Empirical CDF
        self.ecdf_canvas.axes.clear()
        x = np.sort(data)
        y = np.arange(1, len(x) + 1) / len(x)
        self.ecdf_canvas.axes.step(x, y, where='post', label="Empirical CDF")
        self.ecdf_canvas.axes.set_title(f"Empirical CDF of {series.name}")
        self.ecdf_canvas.axes.set_xlabel("Value")
        self.ecdf_canvas.axes.set_ylabel("Cumulative Probability")
        self.ecdf_canvas.fig.tight_layout()
        self.ecdf_canvas.draw()
    
    def create_categorical_plots(self, series, stats):
        """Create plots for categorical data"""
        # Clean data
        data = series.dropna()
        
        # Bar chart for categorical data
        self.categorical_canvas.axes.clear()
        value_counts = data.value_counts().sort_values(ascending=False)
        
        # Limit to top 15 categories if there are too many
        if len(value_counts) > 15:
            value_counts = value_counts.head(15)
            title = f"Top 15 Categories in {series.name}"
        else:
            title = f"Categories in {series.name}"
            
        value_counts.plot(kind='bar', ax=self.categorical_canvas.axes)
        self.categorical_canvas.axes.set_title(title)
        self.categorical_canvas.axes.set_xlabel("Category")
        self.categorical_canvas.axes.set_ylabel("Count")
        
        # Rotate x-axis labels if needed
        if len(value_counts) > 5:
            plt.setp(self.categorical_canvas.axes.get_xticklabels(), rotation=45, ha='right')
            
        self.categorical_canvas.fig.tight_layout()
        self.categorical_canvas.draw()


# Function interface for simpler usage
def profile(df):
    """
    Profile a dataframe to identify the distribution characteristics of each column.
    
    Args:
        df: pandas DataFrame to analyze
        
    Returns:
        DataFrame with columns and their distribution profiles
    """
    profiler = DistributionProfiler()
    return profiler.profile(df)


def visualize_profile(df):
    """
    Create a visual representation of the distribution profiles for a dataframe.
    
    Args:
        df: pandas DataFrame to analyze
        
    Returns:
        A PyQt6 window showing the visualization
    """
    profiler = DistributionProfiler()
    results = profiler.profile(df)
    vis = DistributionVisualization(df, results)
    vis.show()
    return vis


def test_profile_distributions():
    """Test the distribution profiler with a sample dataframe"""
    import sys
    
    # Create a QApplication instance if one doesn't exist
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Generate a random dataframe with some columns with different distributions
    np.random.seed(42)  # For reproducibility
    
    # Create a dataframe with columns of varying distributions
    df = pd.DataFrame({
        'uniform': np.random.uniform(0, 100, size=1000),  # Uniform distribution
        'normal': np.random.normal(50, 10, size=1000),    # Normal distribution
        'exponential': np.random.exponential(5, size=1000),  # Exponential distribution
        'lognormal': np.random.lognormal(0, 1, size=1000),  # Log-normal distribution
        'bimodal': np.concatenate([np.random.normal(20, 5, 500), np.random.normal(60, 5, 500)]),  # Bimodal
        'constant': np.ones(1000),  # Constant value
        'binary': np.random.choice([0, 1], size=1000),  # Binary
        'categorical': np.random.choice(['A', 'B', 'C', 'D'], size=1000),  # Categorical data
        'skewed': 100 - np.random.power(5, size=1000) * 100,  # Right-skewed
        'multimodal': np.concatenate([
            np.random.normal(10, 2, 300),
            np.random.normal(30, 2, 300),
            np.random.normal(50, 2, 400)
        ]),  # Multimodal
        'boolean': np.random.choice([True, False], size=1000),  # Boolean
        'integer': np.random.randint(1, 10, size=1000),  # Small integers
        'text': pd.Series(['short', 'medium length', 'very long text entry', 'another value'] * 250)  # Text data
    })
    
    # Add datetime and timedelta columns
    df['datetime'] = pd.date_range('2020-01-01', periods=1000, freq='h')
    df['timedelta'] = pd.Series([pd.Timedelta(days=i) for i in range(1000)])
    
    # Add a column with missing values
    df['with_missing'] = df['normal'].copy()
    df.loc[np.random.choice(df.index, size=200), 'with_missing'] = np.nan
    
    # Calculate and display profile information
    print("Distribution Profile Results:")
    profiler = DistributionProfiler()
    result = profiler.profile(df)
    print(result[['column', 'type', 'distribution', 'unique_count']])
    
    # Visualize the results
    vis = visualize_profile(df)
    
    # Start the application event loop
    app.exec()


if __name__ == "__main__":
    test_profile_distributions() 