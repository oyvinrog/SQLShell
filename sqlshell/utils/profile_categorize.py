"""
Column Categorization Utilities

This module provides academically-grounded methods for categorizing columns:
- Numerical columns: Binning/discretization using established statistical methods
- Categorical columns: Frequency-based grouping with "Other" category

References:
-----------
- Dougherty, J., Kohavi, R., & Sahami, M. (1995). "Supervised and Unsupervised
  Discretization of Continuous Features"
- Liu, H. & Motoda, H. (1998). "Feature Selection for Knowledge Discovery and
  Data Mining"
- Jenks, G.F. (1967). "The Data Model Concept in Statistical Mapping"
- Freedman, D. & Diaconis, P. (1981). "On the histogram as a density estimator:
  L2 theory"
"""

import pandas as pd
import warnings
from typing import Tuple

# PyQt6 imports for visualization
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QComboBox, QTabWidget,
    QFrame, QSlider, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas


def _detect_column_type(series: pd.Series) -> str:
    """
    Detect if a column should be treated as numerical or categorical.

    Parameters
    ----------
    series : pd.Series
        The column to analyze

    Returns
    -------
    str
        'numerical' or 'categorical'
    """
    # Check if dtype is numeric
    if pd.api.types.is_numeric_dtype(series):
        # Check if it's really continuous or just encoded categories
        n_unique = series.nunique()
        n_total = len(series.dropna())

        # If very few unique values relative to total, might be categorical
        if n_total > 0 and n_unique / n_total < 0.05 and n_unique < 20:
            return 'categorical'
        return 'numerical'
    else:
        return 'categorical'


def categorize_numerical(
    dataframe: pd.DataFrame,
    column: str,
    method: str = "quantile",
    n_bins: int = 5,
    min_bin_size: int = 5
) -> pd.DataFrame:
    """
    Bin a numerical column into categorical ranges.

    Uses the NumericTargetDiscretizer from profile_cn2.py for academically
    grounded binning methods.

    Parameters
    ----------
    dataframe : pd.DataFrame
        Input dataframe
    column : str
        Name of numerical column to bin
    method : str, default='quantile'
        Binning method: 'quantile', 'equal_width', 'jenks',
        'freedman_diaconis', 'sturges', 'auto'
    n_bins : int, default=5
        Number of bins to create
    min_bin_size : int, default=5
        Minimum samples per bin (smaller bins get merged)

    Returns
    --------
    pd.DataFrame
        Copy of dataframe with new binned column added

    References
    ----------
    - Dougherty et al. (1995): Supervised and Unsupervised Discretization
    - Jenks (1967): Natural Breaks classification
    - Freedman & Diaconis (1981): Optimal histogram bin width
    """
    from sqlshell.utils.profile_cn2 import NumericTargetDiscretizer

    if column not in dataframe.columns:
        raise KeyError(f"Column '{column}' not found in dataframe")

    # Check for empty dataframe
    if len(dataframe) == 0:
        raise ValueError("Cannot categorize an empty dataframe")

    # Create a copy to avoid modifying original
    result = dataframe.copy()

    # Extract the column data
    data = dataframe[column].dropna()

    if len(data) == 0:
        warnings.warn(f"Column '{column}' contains only null values. Skipping categorization.")
        result[f"{column}_binned"] = "Missing"
        return result

    # Check if we have enough unique values
    n_unique = data.nunique()
    if n_unique <= 1:
        warnings.warn(f"Column '{column}' has only {n_unique} unique value(s). Creating single category.")
        result[f"{column}_binned"] = f"All values: {data.iloc[0]}"
        return result

    # Adjust n_bins if we have fewer unique values
    effective_n_bins = min(n_bins, n_unique - 1)

    try:
        # Create and fit the discretizer
        discretizer = NumericTargetDiscretizer(
            method=method,
            n_bins=effective_n_bins,
            min_bin_size=min_bin_size
        )

        # Fit and transform the data
        binned_values = discretizer.fit_transform(data)

        # Create the new column with bin labels
        result[f"{column}_binned"] = pd.Series(index=dataframe.index, dtype=str)
        result.loc[data.index, f"{column}_binned"] = binned_values

        # Fill NaN values with "Missing" label
        result[f"{column}_binned"] = result[f"{column}_binned"].fillna("Missing")

        return result

    except Exception as e:
        raise ValueError(f"Error binning column '{column}': {str(e)}")


def categorize_categorical(
    dataframe: pd.DataFrame,
    column: str,
    top_n: int = 5,
    other_label: str = "Other"
) -> pd.DataFrame:
    """
    Group low-frequency categories as "Other".

    Based on Pareto principle and frequency-based feature selection.

    Parameters
    ----------
    dataframe : pd.DataFrame
        Input dataframe
    column : str
        Name of categorical column to group
    top_n : int, default=5
        Number of top categories to keep
    other_label : str, default="Other"
        Label for grouped categories

    Returns
    --------
    pd.DataFrame
        Copy of dataframe with new grouped column added

    References
    ----------
    - Liu & Motoda (1998): Feature Selection for Knowledge Discovery
    - Pareto Principle: Focus on most frequent categories
    """
    if column not in dataframe.columns:
        raise KeyError(f"Column '{column}' not found in dataframe")

    # Check for empty dataframe
    if len(dataframe) == 0:
        raise ValueError("Cannot categorize an empty dataframe")

    # Create a copy to avoid modifying original
    result = dataframe.copy()

    # Get value counts
    value_counts = dataframe[column].value_counts()

    # Get top N categories
    top_categories = value_counts.head(top_n).index.tolist()

    # Create the grouped column
    def group_category(value):
        if pd.isna(value):
            return "Missing"
        elif value in top_categories:
            return str(value)
        else:
            return other_label

    result[f"{column}_grouped"] = dataframe[column].apply(group_category)

    return result


def auto_categorize(
    dataframe: pd.DataFrame,
    column: str,
    **kwargs
) -> Tuple[pd.DataFrame, str]:
    """
    Automatically detect column type and apply appropriate categorization.

    Parameters
    ----------
    dataframe : pd.DataFrame
        Input dataframe
    column : str
        Column name to categorize
    **kwargs : dict
        Additional parameters passed to categorization functions
        (e.g., n_bins, top_n, method)

    Returns
    --------
    Tuple[pd.DataFrame, str]
        (transformed dataframe, transformation_type: 'binned' or 'grouped')
    """
    if column not in dataframe.columns:
        raise KeyError(f"Column '{column}' not found in dataframe")

    # Check for empty dataframe
    if len(dataframe) == 0:
        raise ValueError("Cannot categorize an empty dataframe")

    # Detect column type
    col_type = _detect_column_type(dataframe[column])

    if col_type == 'numerical':
        # Extract numerical-specific kwargs
        method = kwargs.get('method', 'quantile')
        n_bins = kwargs.get('n_bins', 5)
        min_bin_size = kwargs.get('min_bin_size', 5)

        result = categorize_numerical(
            dataframe, column,
            method=method,
            n_bins=n_bins,
            min_bin_size=min_bin_size
        )
        return result, 'binned'
    else:
        # Extract categorical-specific kwargs
        top_n = kwargs.get('top_n', 5)
        other_label = kwargs.get('other_label', 'Other')

        result = categorize_categorical(
            dataframe, column,
            top_n=top_n,
            other_label=other_label
        )
        return result, 'grouped'


class CategorizeVisualization(QMainWindow):
    """
    Interactive visualization for categorization preview and configuration.

    Similar to OneHotEncodingVisualization in profile_ohe.py, this provides:
    - Preview of categorization results
    - Interactive parameter adjustment
    - Statistical visualizations
    - Apply button to commit changes

    Signals
    -------
    categorizationApplied : pyqtSignal(pd.DataFrame)
        Emitted when user clicks Apply with the transformed dataframe
    """

    categorizationApplied = pyqtSignal(pd.DataFrame)

    def __init__(
        self,
        original_df: pd.DataFrame,
        column_name: str,
        categorization_type: str,  # 'binned' or 'grouped'
        initial_method: str = 'quantile',
        initial_n_bins: int = 5,
        initial_top_n: int = 5
    ):
        """
        Initialize categorization visualization window.

        Parameters
        ----------
        original_df : pd.DataFrame
            Original dataframe
        column_name : str
            Column to categorize
        categorization_type : str
            'binned' for numerical, 'grouped' for categorical
        initial_method : str
            Initial binning method for numerical columns
        initial_n_bins : int
            Initial number of bins for numerical columns
        initial_top_n : int
            Initial number of top categories for categorical columns
        """
        super().__init__()

        self.original_df = original_df
        self.column_name = column_name
        self.categorization_type = categorization_type
        self.current_method = initial_method
        self.current_n_bins = initial_n_bins
        self.current_top_n = initial_top_n
        self.categorized_df = None

        # Window setup
        self.setWindowTitle(f"Categorize Column - {column_name}")
        self.setGeometry(100, 100, 1200, 900)

        # Create initial categorization
        self._update_categorization()

        # Build UI
        self._init_ui()

        # Show the window
        self.show()

    def _init_ui(self):
        """Initialize the user interface."""
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Main layout
        main_layout = QVBoxLayout(main_widget)

        # Title
        title_label = QLabel(f"Categorization Preview: {self.column_name}")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Description
        if self.categorization_type == 'binned':
            description = "Binning transforms continuous numerical data into discrete categories using statistical methods."
        else:
            description = "Grouping consolidates low-frequency categories into 'Other' to reduce dimensionality."

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)

        # Control panel
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.Shape.StyledPanel)
        control_layout = QHBoxLayout(control_frame)

        if self.categorization_type == 'binned':
            # Method selector for numerical
            method_label = QLabel("Binning Method:")
            self.method_selector = QComboBox()
            self.method_selector.addItems([
                "Quantile (Equal Frequency)",
                "Equal Width",
                "Jenks (Natural Breaks)",
                "Freedman-Diaconis",
                "Sturges",
                "Auto"
            ])
            # Map display names to method names
            self.method_map = {
                "Quantile (Equal Frequency)": "quantile",
                "Equal Width": "equal_width",
                "Jenks (Natural Breaks)": "jenks",
                "Freedman-Diaconis": "freedman_diaconis",
                "Sturges": "sturges",
                "Auto": "auto"
            }
            self.reverse_method_map = {v: k for k, v in self.method_map.items()}
            self.method_selector.setCurrentText(self.reverse_method_map.get(self.current_method, "Quantile (Equal Frequency)"))
            self.method_selector.currentTextChanged.connect(self._on_method_changed)

            control_layout.addWidget(method_label)
            control_layout.addWidget(self.method_selector)

            # Number of bins slider
            bins_label = QLabel(f"Number of Bins: {self.current_n_bins}")
            self.bins_label = bins_label
            self.bins_slider = QSlider(Qt.Orientation.Horizontal)
            self.bins_slider.setMinimum(2)
            self.bins_slider.setMaximum(10)
            self.bins_slider.setValue(self.current_n_bins)
            self.bins_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            self.bins_slider.setTickInterval(1)
            self.bins_slider.valueChanged.connect(self._on_bins_changed)

            control_layout.addWidget(bins_label)
            control_layout.addWidget(self.bins_slider)

        else:
            # Top N slider for categorical
            top_n_label = QLabel(f"Top Categories: {self.current_top_n}")
            self.top_n_label = top_n_label
            self.top_n_slider = QSlider(Qt.Orientation.Horizontal)
            self.top_n_slider.setMinimum(3)
            self.top_n_slider.setMaximum(10)
            self.top_n_slider.setValue(self.current_top_n)
            self.top_n_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            self.top_n_slider.setTickInterval(1)
            self.top_n_slider.valueChanged.connect(self._on_top_n_changed)

            control_layout.addWidget(top_n_label)
            control_layout.addWidget(self.top_n_slider)

        main_layout.addWidget(control_frame)

        # Tab widget for different views
        self.tab_widget = QTabWidget()

        # Original data tab
        original_tab = self._create_data_table(self.original_df)
        self.tab_widget.addTab(original_tab, "Original Data")

        # Categorized data tab
        self.categorized_tab = self._create_data_table(self.categorized_df)
        self.tab_widget.addTab(self.categorized_tab, "Categorized Data")

        # Statistics tab
        self.stats_tab = self._create_statistics_tab()
        self.tab_widget.addTab(self.stats_tab, "Statistics")

        # Visualization tab
        self.viz_tab = self._create_visualization_tab()
        self.tab_widget.addTab(self.viz_tab, "Visualization")

        main_layout.addWidget(self.tab_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.close)
        button_layout.addWidget(cancel_button)

        apply_button = QPushButton("Apply Categorization")
        apply_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px; }")
        apply_button.clicked.connect(self._on_apply)
        button_layout.addWidget(apply_button)

        main_layout.addLayout(button_layout)

    def _create_data_table(self, df: pd.DataFrame) -> QWidget:
        """Create a table widget to display dataframe."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        table = QTableWidget()
        table.setRowCount(min(100, len(df)))  # Show first 100 rows
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns.tolist())

        # Populate table
        for i in range(min(100, len(df))):
            for j, col in enumerate(df.columns):
                value = str(df.iloc[i, j])
                item = QTableWidgetItem(value)
                table.setItem(i, j, item)

        # Resize columns to content
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(table)

        if len(df) > 100:
            info_label = QLabel(f"Showing first 100 of {len(df)} rows")
            info_label.setStyleSheet("color: gray; font-style: italic;")
            layout.addWidget(info_label)

        return widget

    def _create_statistics_tab(self) -> QWidget:
        """Create statistics tab with summary information."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Create statistics table
        stats_table = QTableWidget()

        if self.categorization_type == 'binned':
            new_col = f"{self.column_name}_binned"
        else:
            new_col = f"{self.column_name}_grouped"

        # Get value counts
        value_counts = self.categorized_df[new_col].value_counts().sort_index()

        stats_table.setRowCount(len(value_counts))
        stats_table.setColumnCount(3)
        stats_table.setHorizontalHeaderLabels(["Category", "Count", "Percentage"])

        total = len(self.categorized_df)
        for i, (category, count) in enumerate(value_counts.items()):
            stats_table.setItem(i, 0, QTableWidgetItem(str(category)))
            stats_table.setItem(i, 1, QTableWidgetItem(str(count)))
            percentage = f"{count / total * 100:.2f}%"
            stats_table.setItem(i, 2, QTableWidgetItem(percentage))

        stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(QLabel("Category Distribution:"))
        layout.addWidget(stats_table)

        # Add summary info
        summary_text = f"""
        <b>Summary:</b><br>
        Total rows: {total}<br>
        Number of categories: {len(value_counts)}<br>
        Original unique values: {self.original_df[self.column_name].nunique()}<br>
        """

        summary_label = QLabel(summary_text)
        summary_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(summary_label)

        return widget

    def _create_visualization_tab(self) -> QWidget:
        """Create visualization tab with charts."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Create matplotlib figure
        self.figure, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(12, 5))
        self.canvas = FigureCanvas(self.figure)

        self._update_visualizations()

        layout.addWidget(self.canvas)

        return widget

    def _update_visualizations(self):
        """Update the visualization plots."""
        self.ax1.clear()
        self.ax2.clear()

        if self.categorization_type == 'binned':
            new_col = f"{self.column_name}_binned"

            # Original distribution (histogram)
            self.ax1.hist(self.original_df[self.column_name].dropna(), bins=30, edgecolor='black', alpha=0.7)
            self.ax1.set_title(f"Original Distribution\n{self.column_name}")
            self.ax1.set_xlabel("Value")
            self.ax1.set_ylabel("Frequency")
            self.ax1.grid(True, alpha=0.3)

            # Categorized distribution (bar chart)
            value_counts = self.categorized_df[new_col].value_counts().sort_index()
            self.ax2.bar(range(len(value_counts)), value_counts.values, edgecolor='black')
            self.ax2.set_title(f"Categorized Distribution\n{new_col}")
            self.ax2.set_xlabel("Bin")
            self.ax2.set_ylabel("Frequency")
            self.ax2.set_xticks(range(len(value_counts)))
            self.ax2.set_xticklabels(value_counts.index, rotation=45, ha='right')
            self.ax2.grid(True, alpha=0.3)

        else:
            new_col = f"{self.column_name}_grouped"

            # Original distribution (top 15)
            original_counts = self.original_df[self.column_name].value_counts().head(15)
            self.ax1.barh(range(len(original_counts)), original_counts.values)
            self.ax1.set_title(f"Original Top 15 Categories\n{self.column_name}")
            self.ax1.set_xlabel("Count")
            self.ax1.set_yticks(range(len(original_counts)))
            self.ax1.set_yticklabels(original_counts.index)
            self.ax1.invert_yaxis()
            self.ax1.grid(True, alpha=0.3, axis='x')

            # Grouped distribution
            grouped_counts = self.categorized_df[new_col].value_counts()
            colors = ['#FF6B6B' if cat == 'Other' else '#4ECDC4' for cat in grouped_counts.index]
            self.ax2.bar(range(len(grouped_counts)), grouped_counts.values, color=colors, edgecolor='black')
            self.ax2.set_title(f"Grouped Distribution\n{new_col}")
            self.ax2.set_xlabel("Category")
            self.ax2.set_ylabel("Count")
            self.ax2.set_xticks(range(len(grouped_counts)))
            self.ax2.set_xticklabels(grouped_counts.index, rotation=45, ha='right')
            self.ax2.grid(True, alpha=0.3, axis='y')

        self.figure.tight_layout()
        self.canvas.draw()

    def _update_categorization(self):
        """Update the categorization based on current parameters."""
        try:
            if self.categorization_type == 'binned':
                self.categorized_df = categorize_numerical(
                    self.original_df,
                    self.column_name,
                    method=self.current_method,
                    n_bins=self.current_n_bins
                )
            else:
                self.categorized_df = categorize_categorical(
                    self.original_df,
                    self.column_name,
                    top_n=self.current_top_n
                )
        except Exception as e:
            QMessageBox.warning(self, "Categorization Error", f"Error updating categorization: {str(e)}")

    def _refresh_ui(self):
        """Refresh all UI components with updated data."""
        # Update categorized data tab
        new_table = self._create_data_table(self.categorized_df)
        old_widget = self.tab_widget.widget(1)
        self.tab_widget.removeTab(1)
        self.tab_widget.insertTab(1, new_table, "Categorized Data")
        old_widget.deleteLater()

        # Update statistics tab
        new_stats = self._create_statistics_tab()
        old_widget = self.tab_widget.widget(2)
        self.tab_widget.removeTab(2)
        self.tab_widget.insertTab(2, new_stats, "Statistics")
        old_widget.deleteLater()

        # Update visualizations
        self._update_visualizations()

    def _on_method_changed(self, text):
        """Handle binning method change."""
        self.current_method = self.method_map.get(text, 'quantile')
        self._update_categorization()
        self._refresh_ui()

    def _on_bins_changed(self, value):
        """Handle number of bins change."""
        self.current_n_bins = value
        self.bins_label.setText(f"Number of Bins: {value}")
        self._update_categorization()
        self._refresh_ui()

    def _on_top_n_changed(self, value):
        """Handle top N change."""
        self.current_top_n = value
        self.top_n_label.setText(f"Top Categories: {value}")
        self._update_categorization()
        self._refresh_ui()

    def _on_apply(self):
        """Handle Apply button click."""
        # Emit signal with categorized dataframe
        self.categorizationApplied.emit(self.categorized_df)

        # Show success message
        QMessageBox.information(
            self,
            "Categorization Applied",
            f"Categorization has been applied successfully!\n\n"
            f"New column added: {self.column_name}_{'binned' if self.categorization_type == 'binned' else 'grouped'}"
        )

        # Close the window
        self.close()


def visualize_categorize(
    df: pd.DataFrame,
    column: str,
    method: str = "auto",
    **kwargs
) -> CategorizeVisualization:
    """
    Create and show interactive categorization visualization.

    This is the main entry point called from __main__.py

    Parameters
    ----------
    df : pd.DataFrame
        Original dataframe
    column : str
        Column to categorize
    method : str, default='auto'
        Method to use ('auto' detects column type)
    **kwargs : dict
        Additional parameters (n_bins, top_n, etc.)

    Returns
    -------
    CategorizeVisualization
        The visualization window (must be stored to prevent GC)
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in dataframe")

    # Auto-detect column type if method is auto
    if method == 'auto':
        col_type = _detect_column_type(df[column])
        if col_type == 'numerical':
            categorization_type = 'binned'
            initial_method = kwargs.get('initial_method', 'quantile')
        else:
            categorization_type = 'grouped'
            initial_method = None
    else:
        # Method specified, assume binned
        categorization_type = 'binned'
        initial_method = method

    # Extract parameters
    initial_n_bins = kwargs.get('n_bins', 5)
    initial_top_n = kwargs.get('top_n', 5)

    # Create and return visualization window
    viz = CategorizeVisualization(
        original_df=df,
        column_name=column,
        categorization_type=categorization_type,
        initial_method=initial_method if initial_method else 'quantile',
        initial_n_bins=initial_n_bins,
        initial_top_n=initial_top_n
    )

    return viz
