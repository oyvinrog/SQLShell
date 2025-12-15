"""
Dataset comparison module.

This module provides functionality for comparing multiple datasets using
academic techniques including merge indicators, cell-level diff analysis,
and statistical comparison of matched/unmatched rows.
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Try to import optional dependencies
try:
    import matplotlib
    try:
        matplotlib.use('qtagg')
    except ImportError:
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from PyQt6.QtCore import QObject, pyqtSignal, Qt
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
        QTableView, QHeaderView, QLabel, QFrame, QScrollArea, QTabWidget,
        QComboBox, QPushButton, QSplitter, QMessageBox, QTreeWidget,
        QTreeWidgetItem, QGroupBox
    )
    from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush, QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    
    class QObject:
        def __init__(self):
            pass
    
    class pyqtSignal:
        def __init__(self, *args):
            pass
        def emit(self, *args):
            pass


class DatasetComparator(QObject):
    """
    Compare multiple datasets using academic data comparison techniques.
    
    Key techniques used:
    1. Full Outer Join - to capture all rows from all datasets
    2. Merge Indicator - shows which dataset(s) each row came from
    3. Cell-level Diff - highlights exact value differences
    4. Statistical Summary - distribution of matches/differences
    """
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self):
        super().__init__()
        self.comparison_results = {}
        
    def compare(self, dataframes: list, names: list = None, key_columns: list = None):
        """
        Compare multiple dataframes and identify differences.
        
        Args:
            dataframes: List of pandas DataFrames to compare
            names: Optional list of names for each DataFrame
            key_columns: Optional list of columns to use as join keys.
                        If None, uses all common columns.
        
        Returns:
            dict: Comparison results including merged data, indicators, and diff analysis
        """
        if len(dataframes) < 2:
            return {"error": "At least two dataframes are required for comparison"}
        
        # Assign default names if not provided
        if names is None:
            names = [f"Dataset_{i+1}" for i in range(len(dataframes))]
        
        self.progress_updated.emit(5, "Finding common columns...")
        
        # Find common columns across all dataframes
        common_columns = self._find_common_columns(dataframes)
        
        if not common_columns:
            return {"error": "No common columns found between datasets"}
        
        # Use key_columns if provided, otherwise use common columns
        if key_columns is None:
            key_columns = common_columns
        else:
            # Validate key_columns exist in common_columns
            key_columns = [c for c in key_columns if c in common_columns]
            if not key_columns:
                key_columns = common_columns
        
        self.progress_updated.emit(15, "Performing full outer join...")
        
        # Perform comparison using full outer merge
        merged_df, indicator_df = self._full_outer_merge(dataframes, names, key_columns)
        
        self.progress_updated.emit(40, "Analyzing differences...")
        
        # Analyze cell-level differences for matched rows
        diff_analysis = self._analyze_differences(dataframes, names, key_columns, merged_df)
        
        self.progress_updated.emit(70, "Computing statistics...")
        
        # Compute summary statistics
        summary_stats = self._compute_summary_stats(indicator_df, diff_analysis, names)
        
        self.progress_updated.emit(90, "Finalizing results...")
        
        # Store results
        self.comparison_results = {
            'merged_df': merged_df,
            'indicator_df': indicator_df,
            'diff_analysis': diff_analysis,
            'summary_stats': summary_stats,
            'common_columns': common_columns,
            'key_columns': key_columns,
            'dataset_names': names,
            'original_shapes': [df.shape for df in dataframes],
            'dataframes': dataframes
        }
        
        self.progress_updated.emit(100, "Comparison complete!")
        
        return self.comparison_results
    
    def _find_common_columns(self, dataframes):
        """Find columns that exist in all dataframes."""
        if not dataframes:
            return []
        
        common = set(dataframes[0].columns)
        for df in dataframes[1:]:
            common = common.intersection(set(df.columns))
        
        return list(common)
    
    def _full_outer_merge(self, dataframes, names, key_columns):
        """
        Perform a full outer merge of all dataframes.
        
        Returns:
            merged_df: The merged dataframe with coalesced key columns
            indicator_df: DataFrame showing which datasets each row belongs to
        """
        # Start with first dataframe
        result = dataframes[0].copy()
        
        # Add indicator column for first dataframe
        result[f'_in_{names[0]}'] = True
        
        # Add suffix to non-key columns
        non_key_cols = [c for c in result.columns if c not in key_columns and not c.startswith('_in_')]
        result = result.rename(columns={c: f"{c}_{names[0]}" for c in non_key_cols})
        
        # Merge each subsequent dataframe
        for i, (df, name) in enumerate(zip(dataframes[1:], names[1:]), 1):
            df_copy = df.copy()
            df_copy[f'_in_{name}'] = True
            
            # Rename non-key columns
            non_key_cols = [c for c in df_copy.columns if c not in key_columns and not c.startswith('_in_')]
            df_copy = df_copy.rename(columns={c: f"{c}_{name}" for c in non_key_cols})
            
            # Full outer merge
            result = pd.merge(
                result, df_copy,
                on=key_columns,
                how='outer',
                suffixes=('', f'_{name}')
            )
        
        # Fill NaN in indicator columns with False
        for name in names:
            indicator_col = f'_in_{name}'
            if indicator_col in result.columns:
                result[indicator_col] = result[indicator_col].fillna(False)
        
        # Create indicator column showing which datasets matched
        def create_indicator(row):
            matches = []
            for name in names:
                if row.get(f'_in_{name}', False):
                    matches.append(name)
            if len(matches) == len(names):
                return 'all'
            elif len(matches) == 0:
                return 'none'
            elif len(matches) == 1:
                return f'{matches[0]}_only'
            else:
                return ','.join(matches)
        
        result['_indicator'] = result.apply(create_indicator, axis=1)
        
        # Create indicator dataframe
        indicator_cols = ['_indicator'] + [f'_in_{name}' for name in names]
        indicator_df = result[indicator_cols].copy()
        
        return result, indicator_df
    
    def _analyze_differences(self, dataframes, names, key_columns, merged_df):
        """
        Analyze cell-level differences between matched rows.
        
        Returns detailed diff information for rows that exist in multiple datasets.
        """
        diff_results = {
            'column_diffs': {},
            'row_diffs': [],
            'diff_matrix': None
        }
        
        if len(dataframes) != 2:
            # For now, detailed diff analysis only for 2 datasets
            # For more datasets, just return basic info
            return diff_results
        
        # Get rows that exist in both datasets
        both_mask = merged_df['_indicator'] == 'all'
        matched_rows = merged_df[both_mask].copy()
        
        if matched_rows.empty:
            return diff_results
        
        # Find columns that exist in both datasets (non-key columns)
        df1_cols = [c for c in dataframes[0].columns if c not in key_columns]
        df2_cols = [c for c in dataframes[1].columns if c not in key_columns]
        comparable_cols = set(df1_cols).intersection(set(df2_cols))
        
        # Compare each comparable column
        for col in comparable_cols:
            col1 = f'{col}_{names[0]}'
            col2 = f'{col}_{names[1]}'
            
            if col1 in matched_rows.columns and col2 in matched_rows.columns:
                # Compare values
                val1 = matched_rows[col1]
                val2 = matched_rows[col2]
                
                # Handle NaN comparisons
                both_nan = val1.isna() & val2.isna()
                one_nan = val1.isna() ^ val2.isna()
                
                # For numeric columns, compute difference
                if pd.api.types.is_numeric_dtype(val1) and pd.api.types.is_numeric_dtype(val2):
                    diff = (val1 - val2).abs()
                    is_different = (diff > 1e-10) | one_nan
                else:
                    is_different = (val1.astype(str) != val2.astype(str)) & ~both_nan
                    is_different = is_different | one_nan
                
                diff_count = is_different.sum()
                diff_pct = (diff_count / len(matched_rows)) * 100 if len(matched_rows) > 0 else 0
                
                diff_results['column_diffs'][col] = {
                    'diff_count': int(diff_count),
                    'diff_percentage': float(diff_pct),
                    'total_compared': len(matched_rows)
                }
        
        # Create diff matrix (row-level view)
        diff_matrix_data = []
        for idx, row in matched_rows.iterrows():
            row_diffs = []
            for col in comparable_cols:
                col1 = f'{col}_{names[0]}'
                col2 = f'{col}_{names[1]}'
                
                if col1 in matched_rows.columns and col2 in matched_rows.columns:
                    val1 = row[col1]
                    val2 = row[col2]
                    
                    # Check if different
                    if pd.isna(val1) and pd.isna(val2):
                        is_diff = False
                    elif pd.isna(val1) or pd.isna(val2):
                        is_diff = True
                    elif isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                        is_diff = abs(val1 - val2) > 1e-10
                    else:
                        is_diff = str(val1) != str(val2)
                    
                    if is_diff:
                        row_diffs.append({
                            'column': col,
                            'value_1': val1,
                            'value_2': val2
                        })
            
            if row_diffs:
                diff_matrix_data.append({
                    'index': idx,
                    'key_values': {k: row[k] for k in key_columns},
                    'differences': row_diffs
                })
        
        diff_results['row_diffs'] = diff_matrix_data
        
        return diff_results
    
    def _compute_summary_stats(self, indicator_df, diff_analysis, names):
        """Compute summary statistics for the comparison."""
        stats = {
            'total_rows': len(indicator_df),
            'indicator_counts': indicator_df['_indicator'].value_counts().to_dict(),
            'dataset_coverage': {}
        }
        
        # Calculate coverage for each dataset
        for name in names:
            col = f'_in_{name}'
            if col in indicator_df.columns:
                in_count = indicator_df[col].sum()
                stats['dataset_coverage'][name] = {
                    'rows': int(in_count),
                    'percentage': float((in_count / len(indicator_df)) * 100) if len(indicator_df) > 0 else 0
                }
        
        # Add diff stats if available
        if diff_analysis and 'column_diffs' in diff_analysis:
            total_diffs = sum(d['diff_count'] for d in diff_analysis['column_diffs'].values())
            cols_with_diffs = sum(1 for d in diff_analysis['column_diffs'].values() if d['diff_count'] > 0)
            stats['diff_stats'] = {
                'total_cell_differences': total_diffs,
                'columns_with_differences': cols_with_diffs,
                'rows_with_differences': len(diff_analysis.get('row_diffs', []))
            }
        
        return stats


def visualize_comparison(comparison_results, parent=None, show_window=True):
    """
    Create a visual display of dataset comparison results.
    
    Args:
        comparison_results: Results from DatasetComparator.compare()
        parent: Optional parent widget
        show_window: Whether to show the window immediately
        
    Returns:
        QWidget with the visualization
    """
    if not PYQT6_AVAILABLE:
        print("PyQt6 not available - providing text summary:")
        _print_text_summary(comparison_results)
        return comparison_results
    
    if "error" in comparison_results:
        print(f"Error: {comparison_results['error']}")
        return None
    
    # Ensure QApplication exists
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    # Create main widget as a proper window
    main_widget = QWidget(parent)
    # Set window flags to make it a proper closeable window
    main_widget.setWindowFlags(
        Qt.WindowType.Window |
        Qt.WindowType.WindowCloseButtonHint |
        Qt.WindowType.WindowMinMaxButtonsHint |
        Qt.WindowType.WindowTitleHint
    )
    main_widget.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    
    main_layout = QVBoxLayout(main_widget)
    
    # Add header with close button
    header_layout = QHBoxLayout()
    header = QLabel("<h2>Dataset Comparison Results</h2>")
    header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    header_layout.addWidget(header)
    
    # Add explicit close button in case window controls don't work
    close_btn = QPushButton("✕ Close")
    close_btn.setFixedWidth(80)
    close_btn.setStyleSheet("""
        QPushButton {
            background-color: #f44336;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #d32f2f;
        }
    """)
    close_btn.clicked.connect(main_widget.close)
    header_layout.addWidget(close_btn)
    
    main_layout.addLayout(header_layout)
    
    # Create tab widget
    tab_widget = QTabWidget()
    
    # Tab 1: Summary Overview
    summary_tab = _create_summary_tab(comparison_results)
    tab_widget.addTab(summary_tab, "Summary")
    
    # Tab 2: Merged Data with Indicators
    merged_tab = _create_merged_data_tab(comparison_results)
    tab_widget.addTab(merged_tab, "Merged Data")
    
    # Tab 3: Row Match Analysis
    match_tab = _create_match_analysis_tab(comparison_results)
    tab_widget.addTab(match_tab, "Match Analysis")
    
    # Tab 4: Cell-Level Differences (if available)
    if comparison_results.get('diff_analysis', {}).get('row_diffs'):
        diff_tab = _create_diff_detail_tab(comparison_results)
        tab_widget.addTab(diff_tab, "Cell Differences")
    
    # Tab 5: Visual Charts
    if MATPLOTLIB_AVAILABLE:
        chart_tab = _create_chart_tab(comparison_results)
        tab_widget.addTab(chart_tab, "Charts")
    
    main_layout.addWidget(tab_widget)
    
    main_widget.setWindowTitle("Dataset Comparison")
    main_widget.resize(1200, 800)
    
    if show_window:
        main_widget.show()
        main_widget.raise_()  # Bring to front
        main_widget.activateWindow()  # Give focus
    
    return main_widget


def _print_text_summary(results):
    """Print text summary when GUI is not available."""
    print("\n" + "=" * 60)
    print("DATASET COMPARISON SUMMARY")
    print("=" * 60)
    
    stats = results.get('summary_stats', {})
    print(f"\nTotal rows in merged result: {stats.get('total_rows', 'N/A')}")
    
    print("\nIndicator Counts:")
    for indicator, count in stats.get('indicator_counts', {}).items():
        print(f"  {indicator}: {count}")
    
    print("\nDataset Coverage:")
    for name, coverage in stats.get('dataset_coverage', {}).items():
        print(f"  {name}: {coverage['rows']} rows ({coverage['percentage']:.1f}%)")
    
    if 'diff_stats' in stats:
        print("\nDifference Statistics:")
        diff = stats['diff_stats']
        print(f"  Total cell differences: {diff['total_cell_differences']}")
        print(f"  Columns with differences: {diff['columns_with_differences']}")
        print(f"  Rows with differences: {diff['rows_with_differences']}")
    
    print("=" * 60)


# Only define DrillDownSummaryWidget if PyQt6 is available
if PYQT6_AVAILABLE:
    class DrillDownSummaryWidget(QWidget):
        """Interactive summary widget with drill-down capability."""
        
        def __init__(self, results, parent=None):
            super().__init__(parent)
            self.results = results
            self.setup_ui()
        
        def setup_ui(self):
            layout = QVBoxLayout(self)
            
            # Create splitter for summary and detail view
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Left panel: Summary with clickable items
            left_panel = QWidget()
            left_layout = QVBoxLayout(left_panel)
            
            scroll = QScrollArea()
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            
            stats = self.results.get('summary_stats', {})
            names = self.results.get('dataset_names', [])
            
            # Dataset info
            info_group = QGroupBox("Dataset Information")
            info_layout = QVBoxLayout(info_group)
            
            shapes = self.results.get('original_shapes', [])
            for i, (name, shape) in enumerate(zip(names, shapes)):
                label = QLabel(f"<b>{name}:</b> {shape[0]} rows × {shape[1]} columns")
                info_layout.addWidget(label)
            
            common_cols = self.results.get('common_columns', [])
            key_cols = self.results.get('key_columns', [])
            info_layout.addWidget(QLabel(f"<b>Common columns:</b> {len(common_cols)}"))
            info_layout.addWidget(QLabel(f"<b>Key columns used:</b> {', '.join(key_cols[:5])}{'...' if len(key_cols) > 5 else ''}"))
            
            scroll_layout.addWidget(info_group)
            
            # Match summary with clickable buttons
            match_group = QGroupBox("Match Summary (Click to drill down)")
            match_layout = QVBoxLayout(match_group)
            
            total_rows = stats.get('total_rows', 0)
            match_layout.addWidget(QLabel(f"<b>Total rows after full join:</b> {total_rows}"))
            
            indicator_counts = stats.get('indicator_counts', {})
            
            # Create clickable buttons for each indicator
            for indicator, count in indicator_counts.items():
                pct = (count / total_rows * 100) if total_rows > 0 else 0
                
                btn = QPushButton(f"▶ {indicator}: {count} rows ({pct:.1f}%)")
                btn.setFlat(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                
                if indicator == 'all':
                    btn.setStyleSheet("""
                        QPushButton { 
                            text-align: left; 
                            padding: 8px; 
                            background-color: #e8f5e9; 
                            border: 1px solid #a5d6a7;
                            border-radius: 4px;
                            font-weight: bold;
                        }
                        QPushButton:hover { background-color: #c8e6c9; }
                    """)
                elif '_only' in indicator:
                    btn.setStyleSheet("""
                        QPushButton { 
                            text-align: left; 
                            padding: 8px; 
                            background-color: #fff3e0; 
                            border: 1px solid #ffcc80;
                            border-radius: 4px;
                            font-weight: bold;
                            color: #e65100;
                        }
                        QPushButton:hover { background-color: #ffe0b2; }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton { 
                            text-align: left; 
                            padding: 8px; 
                            background-color: #e3f2fd; 
                            border: 1px solid #90caf9;
                            border-radius: 4px;
                            font-weight: bold;
                        }
                        QPushButton:hover { background-color: #bbdefb; }
                    """)
                
                # Connect click to drill-down
                btn.clicked.connect(lambda checked, ind=indicator: self.show_indicator_details(ind))
                match_layout.addWidget(btn)
            
            scroll_layout.addWidget(match_group)
            
            # Difference summary (if 2 datasets)
            if 'diff_stats' in stats:
                diff_group = QGroupBox("Cell-Level Differences (Matched Rows)")
                diff_layout = QVBoxLayout(diff_group)
                
                diff = stats['diff_stats']
                
                # Clickable button for rows with differences
                if diff['rows_with_differences'] > 0:
                    diff_btn = QPushButton(f"▶ Rows with differences: {diff['rows_with_differences']}")
                    diff_btn.setFlat(True)
                    diff_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    diff_btn.setStyleSheet("""
                        QPushButton { 
                            text-align: left; 
                            padding: 8px; 
                            background-color: #ffebee; 
                            border: 1px solid #ef9a9a;
                            border-radius: 4px;
                            font-weight: bold;
                            color: #c62828;
                        }
                        QPushButton:hover { background-color: #ffcdd2; }
                    """)
                    diff_btn.clicked.connect(self.show_diff_details)
                    diff_layout.addWidget(diff_btn)
                
                diff_layout.addWidget(QLabel(f"<b>Columns with differences:</b> {diff['columns_with_differences']}"))
                diff_layout.addWidget(QLabel(f"<b>Total cell differences:</b> {diff['total_cell_differences']}"))
                
                # Column-level diff details
                col_diffs = self.results.get('diff_analysis', {}).get('column_diffs', {})
                if col_diffs:
                    diff_layout.addWidget(QLabel("<br><b>Differences by Column:</b>"))
                    for col, info in sorted(col_diffs.items(), key=lambda x: -x[1]['diff_count']):
                        if info['diff_count'] > 0:
                            label = QLabel(f"  • <b>{col}:</b> {info['diff_count']} differences ({info['diff_percentage']:.1f}%)")
                            label.setStyleSheet("color: #cc3300;")
                            diff_layout.addWidget(label)
                
                scroll_layout.addWidget(diff_group)
            
            # Add instruction
            instruction = QLabel("<i>Click on any category above to see the matching rows →</i>")
            instruction.setStyleSheet("color: #666; padding: 10px;")
            scroll_layout.addWidget(instruction)
            
            scroll_layout.addStretch()
            scroll_widget.setLayout(scroll_layout)
            scroll.setWidget(scroll_widget)
            scroll.setWidgetResizable(True)
            left_layout.addWidget(scroll)
            
            # Right panel: Detail view
            self.detail_panel = QWidget()
            self.detail_layout = QVBoxLayout(self.detail_panel)
            
            self.detail_header = QLabel("<h3>Select a category to view details</h3>")
            self.detail_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.detail_header.setStyleSheet("color: #666; padding: 20px;")
            self.detail_layout.addWidget(self.detail_header)
            
            self.detail_table = QTableView()
            self.detail_table.hide()
            self.detail_layout.addWidget(self.detail_table)
            
            splitter.addWidget(left_panel)
            splitter.addWidget(self.detail_panel)
            splitter.setSizes([400, 600])
            
            layout.addWidget(splitter)
        
        def show_indicator_details(self, indicator):
            """Show rows matching the selected indicator."""
            merged_df = self.results.get('merged_df', pd.DataFrame())
            
            if merged_df.empty:
                return
            
            # Filter rows by indicator
            filtered_df = merged_df[merged_df['_indicator'] == indicator].copy()
            
            # Update header
            count = len(filtered_df)
            self.detail_header.setText(f"<h3>{indicator}: {count} rows</h3>")
            self.detail_header.setStyleSheet("color: #333; padding: 10px; background-color: #f5f5f5; border-radius: 4px;")
            
            # Populate table
            self._populate_table(filtered_df, indicator)
        
        def show_diff_details(self):
            """Show rows that have cell-level differences."""
            merged_df = self.results.get('merged_df', pd.DataFrame())
            diff_analysis = self.results.get('diff_analysis', {})
            row_diffs = diff_analysis.get('row_diffs', [])
            
            if merged_df.empty or not row_diffs:
                return
            
            # Get indices of rows with differences
            diff_indices = [rd['index'] for rd in row_diffs]
            
            # Filter to only rows with differences
            filtered_df = merged_df.loc[merged_df.index.isin(diff_indices)].copy()
            
            # Update header
            count = len(filtered_df)
            self.detail_header.setText(f"<h3>Rows with cell differences: {count} rows</h3>")
            self.detail_header.setStyleSheet("color: #c62828; padding: 10px; background-color: #ffebee; border-radius: 4px;")
            
            # Populate table with diff highlighting
            self._populate_table(filtered_df, 'diff', row_diffs)
        
        def _populate_table(self, df, indicator, row_diffs=None):
            """Populate the detail table with data."""
            self.detail_table.show()
            
            model = QStandardItemModel()
            
            # Set headers
            headers = list(df.columns)
            model.setHorizontalHeaderLabels(headers)
            
            # Limit rows for performance
            display_rows = min(500, len(df))
            
            # Build a set of diff cells for highlighting
            diff_cells = set()
            if row_diffs:
                names = self.results.get('dataset_names', [])
                for rd in row_diffs:
                    idx = rd['index']
                    for diff in rd['differences']:
                        col = diff['column']
                        # Both column variants should be highlighted
                        if len(names) >= 2:
                            diff_cells.add((idx, f"{col}_{names[0]}"))
                            diff_cells.add((idx, f"{col}_{names[1]}"))
            
            # Color mapping
            colors = {
                'all': QColor(200, 255, 200),  # Light green
                'diff': QColor(255, 235, 238),  # Light red
            }
            only_color = QColor(255, 243, 224)  # Light orange
            diff_cell_color = QColor(255, 200, 200)  # Highlight red for diff cells
            
            for row_idx, (orig_idx, row) in enumerate(df.head(display_rows).iterrows()):
                for col_idx, (col_name, value) in enumerate(row.items()):
                    if pd.isna(value):
                        item = QStandardItem("NULL")
                        item.setForeground(QBrush(QColor(150, 150, 150)))
                    else:
                        item = QStandardItem(str(value))
                    
                    # Highlight diff cells
                    if (orig_idx, col_name) in diff_cells:
                        item.setBackground(QBrush(diff_cell_color))
                        item.setFont(QFont("", -1, QFont.Weight.Bold))
                    elif indicator == 'all':
                        item.setBackground(QBrush(colors['all']))
                    elif indicator == 'diff':
                        pass  # Don't color non-diff cells
                    elif '_only' in str(indicator):
                        item.setBackground(QBrush(only_color))
                    
                    model.setItem(row_idx, col_idx, item)
            
            self.detail_table.setModel(model)
            self.detail_table.setAlternatingRowColors(True)
            self.detail_table.setSortingEnabled(True)
            self.detail_table.resizeColumnsToContents()


def _create_summary_tab(results):
    """Create the summary overview tab with drill-down capability."""
    if PYQT6_AVAILABLE:
        return DrillDownSummaryWidget(results)
    return None


def _create_merged_data_tab(results):
    """Create tab showing the merged dataframe."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    merged_df = results.get('merged_df', pd.DataFrame())
    
    if merged_df.empty:
        layout.addWidget(QLabel("No merged data available"))
        return widget
    
    # Add info label
    info_label = QLabel(f"<b>Merged data:</b> {len(merged_df)} rows × {len(merged_df.columns)} columns")
    layout.addWidget(info_label)
    
    # Create table view
    table_view = QTableView()
    model = QStandardItemModel()
    
    # Set headers
    headers = list(merged_df.columns)
    model.setHorizontalHeaderLabels(headers)
    
    # Limit rows for performance
    display_rows = min(500, len(merged_df))
    
    # Define colors for indicators
    indicator_colors = {
        'all': QColor(200, 255, 200),  # Light green
    }
    only_color = QColor(255, 220, 180)  # Light orange
    
    names = results.get('dataset_names', [])
    for name in names:
        indicator_colors[f'{name}_only'] = only_color
    
    # Populate table
    for row_idx in range(display_rows):
        row = merged_df.iloc[row_idx]
        indicator = row.get('_indicator', '')
        
        for col_idx, (col_name, value) in enumerate(row.items()):
            if pd.isna(value):
                item = QStandardItem("NULL")
                item.setForeground(QBrush(QColor(150, 150, 150)))
            else:
                item = QStandardItem(str(value))
            
            # Color based on indicator
            if indicator in indicator_colors:
                item.setBackground(QBrush(indicator_colors[indicator]))
            elif '_only' in str(indicator):
                item.setBackground(QBrush(only_color))
            
            model.setItem(row_idx, col_idx, item)
    
    table_view.setModel(model)
    table_view.setAlternatingRowColors(True)
    table_view.setSortingEnabled(True)
    table_view.resizeColumnsToContents()
    
    # Add legend
    legend = QLabel(
        "<b>Legend:</b> "
        "<span style='background-color: #c8ffc8; padding: 2px 5px;'>In ALL datasets</span> | "
        "<span style='background-color: #ffdcb4; padding: 2px 5px;'>In one dataset only</span> | "
        "<span style='color: #999999;'>NULL = Missing value</span>"
    )
    layout.addWidget(legend)
    layout.addWidget(table_view)
    
    if len(merged_df) > display_rows:
        layout.addWidget(QLabel(f"<i>Showing {display_rows} of {len(merged_df)} rows</i>"))
    
    return widget


def _create_match_analysis_tab(results):
    """Create tab showing match analysis by indicator."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    indicator_df = results.get('indicator_df', pd.DataFrame())
    names = results.get('dataset_names', [])
    
    if indicator_df.empty:
        layout.addWidget(QLabel("No indicator data available"))
        return widget
    
    # Create a tree widget showing breakdown
    tree = QTreeWidget()
    tree.setHeaderLabels(["Category", "Count", "Percentage"])
    tree.setColumnCount(3)
    
    total = len(indicator_df)
    indicator_counts = indicator_df['_indicator'].value_counts()
    
    # Add root item
    root = QTreeWidgetItem(["All Rows", str(total), "100%"])
    root.setFont(0, QFont("", -1, QFont.Weight.Bold))
    tree.addTopLevelItem(root)
    
    # Add indicator categories
    for indicator, count in indicator_counts.items():
        pct = (count / total * 100) if total > 0 else 0
        item = QTreeWidgetItem([str(indicator), str(count), f"{pct:.1f}%"])
        
        if indicator == 'all':
            item.setBackground(0, QBrush(QColor(200, 255, 200)))
            item.setBackground(1, QBrush(QColor(200, 255, 200)))
            item.setBackground(2, QBrush(QColor(200, 255, 200)))
        elif '_only' in str(indicator):
            item.setBackground(0, QBrush(QColor(255, 220, 180)))
            item.setBackground(1, QBrush(QColor(255, 220, 180)))
            item.setBackground(2, QBrush(QColor(255, 220, 180)))
        
        root.addChild(item)
    
    root.setExpanded(True)
    tree.resizeColumnToContents(0)
    tree.resizeColumnToContents(1)
    
    layout.addWidget(tree)
    
    # Add interpretation guide
    guide = QLabel("""
    <b>Interpretation Guide:</b><br>
    • <span style='color: green;'><b>all</b></span>: Rows that exist in ALL datasets (matched on key columns)<br>
    • <span style='color: #cc6600;'><b>DatasetName_only</b></span>: Rows that exist ONLY in that dataset<br>
    • <b>Dataset1,Dataset2</b>: Rows that exist in some but not all datasets
    """)
    guide.setWordWrap(True)
    guide.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
    layout.addWidget(guide)
    
    return widget


def _create_diff_detail_tab(results):
    """Create tab showing detailed cell-level differences."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    diff_analysis = results.get('diff_analysis', {})
    row_diffs = diff_analysis.get('row_diffs', [])
    names = results.get('dataset_names', [])
    
    if not row_diffs:
        layout.addWidget(QLabel("No cell-level differences found in matched rows"))
        return widget
    
    # Info header
    info = QLabel(f"<b>Found {len(row_diffs)} rows with differences in matched data</b>")
    layout.addWidget(info)
    
    # Create table showing differences
    table_view = QTableView()
    model = QStandardItemModel()
    
    # Build headers
    headers = ["Key Values", "Column", f"Value ({names[0]})", f"Value ({names[1]})", "Difference"]
    model.setHorizontalHeaderLabels(headers)
    
    row_idx = 0
    for row_diff in row_diffs[:100]:  # Limit for performance
        key_vals = ", ".join([f"{k}={v}" for k, v in row_diff['key_values'].items()])
        
        for diff in row_diff['differences']:
            val1 = diff['value_1']
            val2 = diff['value_2']
            
            # Calculate difference for numeric values
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                if not pd.isna(val1) and not pd.isna(val2):
                    diff_val = f"{val1 - val2:+.4g}"
                else:
                    diff_val = "NULL comparison"
            else:
                diff_val = "Type/Text differs"
            
            items = [
                QStandardItem(key_vals),
                QStandardItem(str(diff['column'])),
                QStandardItem(str(val1) if not pd.isna(val1) else "NULL"),
                QStandardItem(str(val2) if not pd.isna(val2) else "NULL"),
                QStandardItem(diff_val)
            ]
            
            # Highlight the differing values
            for item in items[2:4]:
                item.setBackground(QBrush(QColor(255, 230, 230)))
            
            for col_idx, item in enumerate(items):
                model.setItem(row_idx, col_idx, item)
            
            row_idx += 1
    
    table_view.setModel(model)
    table_view.setAlternatingRowColors(True)
    table_view.setSortingEnabled(True)
    table_view.resizeColumnsToContents()
    
    layout.addWidget(table_view)
    
    if len(row_diffs) > 100:
        layout.addWidget(QLabel(f"<i>Showing first 100 of {len(row_diffs)} rows with differences</i>"))
    
    return widget


def _create_chart_tab(results):
    """Create tab with visualization charts."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    # Create figure with subplots
    fig = Figure(figsize=(12, 8))
    canvas = FigureCanvasQTAgg(fig)
    
    stats = results.get('summary_stats', {})
    indicator_counts = stats.get('indicator_counts', {})
    names = results.get('dataset_names', [])
    
    # Chart 1: Pie chart of indicator distribution
    ax1 = fig.add_subplot(121)
    
    labels = list(indicator_counts.keys())
    sizes = list(indicator_counts.values())
    
    # Color mapping
    colors = []
    for label in labels:
        if label == 'all':
            colors.append('#66bb6a')  # Green
        elif '_only' in str(label):
            colors.append('#ffb74d')  # Orange
        else:
            colors.append('#42a5f5')  # Blue
    
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
    ax1.set_title('Row Distribution by Match Status')
    
    # Chart 2: Bar chart of column differences (if available)
    ax2 = fig.add_subplot(122)
    
    col_diffs = results.get('diff_analysis', {}).get('column_diffs', {})
    
    if col_diffs:
        # Sort by diff count
        sorted_diffs = sorted(col_diffs.items(), key=lambda x: -x[1]['diff_count'])[:15]
        
        if sorted_diffs:
            cols = [x[0] for x in sorted_diffs]
            counts = [x[1]['diff_count'] for x in sorted_diffs]
            
            bars = ax2.barh(range(len(cols)), counts, color='#ef5350')
            ax2.set_yticks(range(len(cols)))
            ax2.set_yticklabels(cols)
            ax2.set_xlabel('Number of Differences')
            ax2.set_title('Cell Differences by Column')
            ax2.invert_yaxis()
        else:
            ax2.text(0.5, 0.5, 'No differences found\nin matched rows',
                    ha='center', va='center', transform=ax2.transAxes, fontsize=12)
            ax2.set_title('Cell Differences by Column')
    else:
        ax2.text(0.5, 0.5, 'Cell-level comparison\nonly available for\n2 datasets',
                ha='center', va='center', transform=ax2.transAxes, fontsize=12)
        ax2.set_title('Cell Differences by Column')
    
    fig.tight_layout()
    layout.addWidget(canvas)
    
    return widget


def compare_datasets(dataframes, names=None, key_columns=None, parent=None, show_window=True):
    """
    Compare multiple datasets and show visual results.
    
    This is the main entry point for dataset comparison.
    
    Args:
        dataframes: List of pandas DataFrames to compare
        names: Optional list of names for each DataFrame
        key_columns: Optional list of columns to use as join keys
        parent: Optional parent widget
        show_window: Whether to show the window immediately
        
    Returns:
        tuple: (comparison_results, widget)
    """
    comparator = DatasetComparator()
    results = comparator.compare(dataframes, names, key_columns)
    
    if "error" in results:
        if PYQT6_AVAILABLE:
            QMessageBox.warning(parent, "Comparison Error", results["error"])
        else:
            print(f"Error: {results['error']}")
        return results, None
    
    widget = visualize_comparison(results, parent=parent, show_window=show_window)
    
    return results, widget


# Demo function
def demo_comparison():
    """Demonstrate the dataset comparison functionality."""
    print("=" * 60)
    print("DATASET COMPARISON DEMO")
    print("=" * 60)
    
    # Create sample datasets with some differences
    np.random.seed(42)
    
    # Dataset 1: Original data
    df1 = pd.DataFrame({
        'id': [1, 2, 3, 4, 5, 6, 7],
        'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace'],
        'age': [25, 30, 35, 28, 42, 55, 33],
        'salary': [50000, 60000, 75000, 55000, 80000, 95000, 62000],
        'department': ['Sales', 'IT', 'IT', 'HR', 'Sales', 'IT', 'HR']
    })
    
    # Dataset 2: Updated data with some changes
    df2 = pd.DataFrame({
        'id': [1, 2, 3, 4, 5, 8, 9],  # 6,7 removed, 8,9 added
        'name': ['Alice', 'Bob', 'Charles', 'Diana', 'Eve', 'Henry', 'Ivy'],  # Charlie -> Charles
        'age': [26, 30, 35, 28, 43, 45, 29],  # Alice, Eve aged
        'salary': [52000, 60000, 75000, 57000, 82000, 70000, 58000],  # Raises
        'department': ['Sales', 'IT', 'IT', 'Sales', 'Sales', 'IT', 'HR']  # Diana moved
    })
    
    print(f"\nDataset 1: {df1.shape}")
    print(df1)
    
    print(f"\nDataset 2: {df2.shape}")
    print(df2)
    
    print("\nComparing datasets...")
    
    comparator = DatasetComparator()
    results = comparator.compare([df1, df2], names=['Original', 'Updated'], key_columns=['id'])
    
    if "error" in results:
        print(f"Error: {results['error']}")
        return
    
    # Print summary
    stats = results['summary_stats']
    print(f"\n{'=' * 40}")
    print("COMPARISON RESULTS")
    print(f"{'=' * 40}")
    print(f"Total rows after merge: {stats['total_rows']}")
    
    print("\nMatch distribution:")
    for indicator, count in stats['indicator_counts'].items():
        print(f"  {indicator}: {count}")
    
    if 'diff_stats' in stats:
        print("\nDifferences in matched rows:")
        print(f"  Rows with differences: {stats['diff_stats']['rows_with_differences']}")
        print(f"  Total cell differences: {stats['diff_stats']['total_cell_differences']}")
    
    # Show visualization
    print("\nOpening visualization window...")
    visualize_comparison(results, show_window=True)
    
    return results


if __name__ == "__main__":
    demo_comparison()

