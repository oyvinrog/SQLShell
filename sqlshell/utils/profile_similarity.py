import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Try to import optional dependencies
try:
    import matplotlib
    matplotlib.use('qtagg')  # Set the backend before importing pyplot
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available, visualizations will be limited")

try:
    from PyQt6.QtCore import QObject, pyqtSignal, Qt
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
        QTableView, QHeaderView, QLabel, QFrame, QScrollArea, QTabWidget,
        QComboBox, QPushButton, QSplitter, QMessageBox
    )
    from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    print("Warning: PyQt6 not available, using basic QObject substitute")
    
    # Create a basic substitute for QObject when PyQt6 is not available
    class QObject:
        def __init__(self):
            pass
    
    class pyqtSignal:
        def __init__(self, *args):
            pass
        def emit(self, *args):
            pass

try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False
    print("Warning: seaborn not available")

try:
    from scipy.spatial.distance import euclidean, pdist, squareform
    from scipy.stats import zscore
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available, using numpy alternatives")

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: sklearn not available, PCA analysis will be limited")


class SimilarityProfiler(QObject):
    """Class to analyze similarity between rows and columns using z-scores and euclidean distance"""
    progress_updated = pyqtSignal(int, str)  # Signal for progress reporting
    
    def __init__(self):
        super().__init__()
        self.similarity_results = {}
        self.z_scores = None
        self.distance_matrix = None
        self.numerical_columns = []
        
    def profile(self, df):
        """
        Perform similarity analysis on the dataframe
        
        Args:
            df (pd.DataFrame): Input dataframe
            
        Returns:
            dict: Dictionary containing similarity analysis results
        """
        self.progress_updated.emit(10, "Starting similarity analysis...")
        
        if df is None or df.empty:
            return {"error": "Empty or invalid dataframe"}
            
        # Store original dataframe
        self.original_df = df.copy()
        
        # Identify numerical columns
        self.numerical_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(self.numerical_columns) == 0:
            return {"error": "No numerical columns found for similarity analysis"}
            
        self.progress_updated.emit(20, "Computing z-scores...")
        
        # Calculate z-scores for numerical columns
        numerical_df = df[self.numerical_columns].copy()
        
        # Handle missing values
        numerical_df = numerical_df.fillna(numerical_df.mean())
        
        # Calculate z-scores
        if SCIPY_AVAILABLE:
            self.z_scores = numerical_df.apply(zscore, nan_policy='omit')
        else:
            # Fallback to manual z-score calculation
            self.z_scores = (numerical_df - numerical_df.mean()) / numerical_df.std()
        
        self.progress_updated.emit(40, "Computing distance matrices...")
        
        # Calculate euclidean distance between rows
        row_distances = self._calculate_row_distances(numerical_df)
        
        # Calculate euclidean distance between columns (features)
        col_distances = self._calculate_column_distances(numerical_df)
        
        self.progress_updated.emit(60, "Analyzing similarity patterns...")
        
        # Find most similar and dissimilar pairs
        similar_rows, dissimilar_rows = self._find_extreme_pairs(row_distances, 'rows')
        similar_cols, dissimilar_cols = self._find_extreme_pairs(col_distances, 'columns')
        
        self.progress_updated.emit(80, "Computing cluster analysis...")
        
        # Perform basic clustering analysis
        cluster_info = self._analyze_clusters(numerical_df)
        
        self.progress_updated.emit(90, "Finalizing results...")
        
        # Store results
        self.similarity_results = {
            'z_scores': self.z_scores,
            'row_distances': row_distances,
            'column_distances': col_distances,
            'similar_rows': similar_rows,
            'dissimilar_rows': dissimilar_rows,
            'similar_columns': similar_cols,
            'dissimilar_columns': dissimilar_cols,
            'cluster_info': cluster_info,
            'numerical_columns': self.numerical_columns,
            'original_shape': df.shape,
            'processed_shape': numerical_df.shape
        }
        
        self.progress_updated.emit(100, "Similarity analysis complete!")
        
        return self.similarity_results
    
    def _calculate_row_distances(self, df):
        """Calculate euclidean distances between all pairs of rows"""
        try:
            if SKLEARN_AVAILABLE and SCIPY_AVAILABLE:
                # Standardize the data
                scaler = StandardScaler()
                scaled_data = scaler.fit_transform(df)
                
                # Calculate pairwise distances
                distances = pdist(scaled_data, metric='euclidean')
                distance_matrix = squareform(distances)
            else:
                # Fallback to manual calculation
                # Standardize manually
                mean_vals = df.mean()
                std_vals = df.std()
                scaled_data = (df - mean_vals) / std_vals
                
                # Calculate pairwise euclidean distances manually
                n_rows = len(scaled_data)
                distance_matrix = np.zeros((n_rows, n_rows))
                
                for i in range(n_rows):
                    for j in range(i+1, n_rows):
                        dist = np.sqrt(np.sum((scaled_data.iloc[i] - scaled_data.iloc[j]) ** 2))
                        distance_matrix[i, j] = dist
                        distance_matrix[j, i] = dist
            
            return pd.DataFrame(
                distance_matrix, 
                index=df.index, 
                columns=df.index
            )
        except Exception as e:
            print(f"Error calculating row distances: {e}")
            return pd.DataFrame()
    
    def _calculate_column_distances(self, df):
        """Calculate euclidean distances between all pairs of columns"""
        try:
            # Transpose to treat columns as observations
            df_transposed = df.T
            
            if SKLEARN_AVAILABLE and SCIPY_AVAILABLE:
                # Standardize the data
                scaler = StandardScaler()
                scaled_data = scaler.fit_transform(df_transposed)
                
                # Calculate pairwise distances
                distances = pdist(scaled_data, metric='euclidean')
                distance_matrix = squareform(distances)
            else:
                # Fallback to manual calculation
                # Standardize manually
                mean_vals = df_transposed.mean()
                std_vals = df_transposed.std()
                scaled_data = (df_transposed - mean_vals) / std_vals
                
                # Calculate pairwise euclidean distances manually
                n_cols = len(scaled_data)
                distance_matrix = np.zeros((n_cols, n_cols))
                
                for i in range(n_cols):
                    for j in range(i+1, n_cols):
                        dist = np.sqrt(np.sum((scaled_data.iloc[i] - scaled_data.iloc[j]) ** 2))
                        distance_matrix[i, j] = dist
                        distance_matrix[j, i] = dist
            
            return pd.DataFrame(
                distance_matrix, 
                index=df.columns, 
                columns=df.columns
            )
        except Exception as e:
            print(f"Error calculating column distances: {e}")
            return pd.DataFrame()
    
    def _find_extreme_pairs(self, distance_matrix, pair_type='rows'):
        """Find most similar and dissimilar pairs from distance matrix"""
        if distance_matrix.empty:
            return [], []
            
        # Get upper triangle (avoid duplicates and self-comparisons)
        mask = np.triu(np.ones_like(distance_matrix, dtype=bool), k=1)
        distances = distance_matrix.where(mask)
        
        # Flatten and get valid distances
        flat_distances = distances.stack()
        
        if len(flat_distances) == 0:
            return [], []
        
        # Find most similar (smallest distance) and dissimilar (largest distance)
        similar_pairs = flat_distances.nsmallest(5).index.tolist()
        dissimilar_pairs = flat_distances.nlargest(5).index.tolist()
        
        return similar_pairs, dissimilar_pairs
    
    def _analyze_clusters(self, df):
        """Perform basic clustering analysis using PCA"""
        try:
            if df.shape[1] < 2:
                return {"error": "Need at least 2 numerical columns for clustering"}
                
            if not SKLEARN_AVAILABLE:
                return {"error": "sklearn not available for PCA analysis"}
                
            # Standardize data
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(df)
            
            # Apply PCA
            n_components = min(3, df.shape[1])  # Use max 3 components
            pca = PCA(n_components=n_components)
            pca_result = pca.fit_transform(scaled_data)
            
            # Calculate explained variance
            explained_variance = pca.explained_variance_ratio_
            
            return {
                'pca_components': pca_result,
                'explained_variance': explained_variance,
                'cumulative_variance': np.cumsum(explained_variance),
                'n_components': n_components,
                'feature_importance': pca.components_
            }
        except Exception as e:
            return {"error": f"Clustering analysis failed: {e}"}


def visualize_profile(df, profiler_results=None, force_text_mode=False, show_window=True):
    """
    Visualize the similarity profiling results
    
    Args:
        df (pd.DataFrame): Original dataframe
        profiler_results (dict): Results from SimilarityProfiler.profile()
        force_text_mode (bool): Force text mode even if GUI is available
        show_window (bool): Whether to show the window (for standalone usage)
        
    Returns:
        QWidget or dict: Widget containing the visualization or dict with results if GUI not available
    """
    # If no results provided, run the profiler
    if profiler_results is None:
        profiler = SimilarityProfiler()
        profiler_results = profiler.profile(df)
    
    if "error" in profiler_results:
        print(f"Error: {profiler_results['error']}")
        return profiler_results
    
    # Check if we should use GUI or text mode
    if force_text_mode or not PYQT6_AVAILABLE:
        # Return results as dictionary with text summary when GUI is not available
        if not PYQT6_AVAILABLE:
            print("PyQt6 not available - providing text summary:")
        else:
            print("Text mode requested - providing text summary:")
        _print_text_summary(profiler_results)
        return profiler_results
    
    # Ensure QApplication exists (for standalone usage)
    app = QApplication.instance()
    if app is None:
        # Create QApplication for standalone usage
        # In SQLShell, this will already exist
        app = QApplication([])
    
    # Create main widget (only if PyQt6 is available)
    main_widget = QWidget()
    main_layout = QVBoxLayout()
    
    # Create tab widget for different visualizations
    tab_widget = QTabWidget()
    
    # Tab 1: Z-scores heatmap
    if 'z_scores' in profiler_results and not profiler_results['z_scores'].empty:
        zscore_tab = _create_zscore_visualization(profiler_results['z_scores'])
        if zscore_tab:
            tab_widget.addTab(zscore_tab, "Z-Scores Heatmap")
    
    # Tab 2: Row similarity matrix
    if 'row_distances' in profiler_results and not profiler_results['row_distances'].empty:
        row_sim_tab = _create_distance_visualization(
            profiler_results['row_distances'], 
            "Row Similarity Matrix"
        )
        if row_sim_tab:
            tab_widget.addTab(row_sim_tab, "Row Similarities")
    
    # Tab 3: Column similarity matrix
    if 'column_distances' in profiler_results and not profiler_results['column_distances'].empty:
        col_sim_tab = _create_distance_visualization(
            profiler_results['column_distances'], 
            "Column Similarity Matrix"
        )
        if col_sim_tab:
            tab_widget.addTab(col_sim_tab, "Column Similarities")
    
    # Tab 4: PCA visualization
    if 'cluster_info' in profiler_results and 'pca_components' in profiler_results['cluster_info']:
        pca_tab = _create_pca_visualization(profiler_results['cluster_info'])
        if pca_tab:
            tab_widget.addTab(pca_tab, "PCA Analysis")
    
    # Tab 5: Data Preview with unusual rows highlighted
    if 'z_scores' in profiler_results and not profiler_results['z_scores'].empty:
        preview_tab = _create_data_preview_tab(df, profiler_results)
        if preview_tab:
            tab_widget.addTab(preview_tab, "Data Preview")
    
    # Tab 6: Summary statistics
    summary_tab = _create_summary_tab(profiler_results)
    if summary_tab:
        tab_widget.addTab(summary_tab, "Summary")
    
    main_layout.addWidget(tab_widget)
    main_widget.setLayout(main_layout)
    
    # Set window properties
    main_widget.setWindowTitle("Similarity Analysis Results")
    main_widget.resize(1000, 700)
    
    # Show the window if requested (for standalone usage)
    if show_window:
        main_widget.show()
        
        # For standalone usage, run the event loop
        app = QApplication.instance()
        if app is not None:
            # Check if we're running as main script
            import sys
            import __main__
            
            # Only start event loop if we're the main script and no event loop is running
            if hasattr(__main__, '__file__') and not hasattr(sys, 'ps1'):
                try:
                    # We're in a script, start the event loop
                    app.exec()
                except RuntimeError:
                    # Event loop might already be running, that's okay
                    pass
    
    return main_widget


def _print_text_summary(results):
    """Print a text summary when GUI is not available"""
    print("\n" + "="*50)
    print("SIMILARITY ANALYSIS SUMMARY")
    print("="*50)
    
    print(f"Dataset shape: {results.get('original_shape', 'N/A')}")
    print(f"Numerical columns: {len(results.get('numerical_columns', []))}")
    
    if 'similar_rows' in results and results['similar_rows']:
        print("\nMost similar row pairs:")
        for i, pair in enumerate(results['similar_rows'][:3]):
            print(f"  {i+1}. Row {pair[0]} ↔ Row {pair[1]}")
    
    if 'similar_columns' in results and results['similar_columns']:
        print("\nMost similar column pairs:")
        for i, pair in enumerate(results['similar_columns'][:3]):
            print(f"  {i+1}. {pair[0]} ↔ {pair[1]}")
    
    if 'cluster_info' in results and 'explained_variance' in results['cluster_info']:
        cluster_info = results['cluster_info']
        print(f"\nPCA Analysis:")
        print(f"  Components: {cluster_info['n_components']}")
        print(f"  Total variance explained: {cluster_info['cumulative_variance'][-1]:.1%}")
    
    print("="*50)


def _create_zscore_visualization(z_scores):
    """Create z-scores heatmap visualization"""
    if not PYQT6_AVAILABLE or not MATPLOTLIB_AVAILABLE:
        return None
        
    widget = QWidget()
    layout = QVBoxLayout()
    
    # Create matplotlib figure
    fig = Figure(figsize=(12, 8))
    canvas = FigureCanvasQTAgg(fig)
    
    ax = fig.add_subplot(111)
    
    # Create heatmap
    im = ax.imshow(z_scores.values, cmap='RdBu_r', aspect='auto', vmin=-3, vmax=3)
    
    # Set labels
    ax.set_title('Z-Scores Heatmap\n(Blue: Below average, Red: Above average)', fontsize=14)
    ax.set_xlabel('Columns')
    ax.set_ylabel('Rows')
    
    # Set ticks
    if len(z_scores.columns) <= 20:
        ax.set_xticks(range(len(z_scores.columns)))
        ax.set_xticklabels(z_scores.columns, rotation=45, ha='right')
    else:
        ax.set_xticks([])
        ax.set_xlabel(f'Columns (showing {len(z_scores.columns)} columns)')
    
    if len(z_scores.index) <= 20:
        ax.set_yticks(range(len(z_scores.index)))
        ax.set_yticklabels(z_scores.index)
    else:
        ax.set_yticks([])
        ax.set_ylabel(f'Rows (showing {len(z_scores.index)} rows)')
    
    # Add colorbar
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Z-Score', rotation=270, labelpad=15)
    
    fig.tight_layout()
    
    layout.addWidget(canvas)
    widget.setLayout(layout)
    
    return widget


def _create_distance_visualization(distance_matrix, title):
    """Create distance matrix visualization"""
    if not PYQT6_AVAILABLE or not MATPLOTLIB_AVAILABLE:
        return None
        
    widget = QWidget()
    layout = QVBoxLayout()
    
    # Create matplotlib figure
    fig = Figure(figsize=(10, 8))
    canvas = FigureCanvasQTAgg(fig)
    
    ax = fig.add_subplot(111)
    
    # Create heatmap (invert colormap so smaller distances are darker)
    im = ax.imshow(distance_matrix.values, cmap='viridis_r', aspect='auto')
    
    # Set labels
    ax.set_title(f'{title}\n(Darker colors indicate higher similarity)', fontsize=14)
    
    # Set ticks
    if len(distance_matrix.index) <= 15:
        ax.set_xticks(range(len(distance_matrix.columns)))
        ax.set_xticklabels(distance_matrix.columns, rotation=45, ha='right')
        ax.set_yticks(range(len(distance_matrix.index)))
        ax.set_yticklabels(distance_matrix.index)
    else:
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel(f'Showing {len(distance_matrix.columns)} items')
        ax.set_ylabel(f'Showing {len(distance_matrix.index)} items')
    
    # Add colorbar
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Euclidean Distance', rotation=270, labelpad=15)
    
    fig.tight_layout()
    
    layout.addWidget(canvas)
    widget.setLayout(layout)
    
    return widget


def _create_pca_visualization(cluster_info):
    """Create PCA visualization"""
    if not PYQT6_AVAILABLE or not MATPLOTLIB_AVAILABLE:
        return None
        
    widget = QWidget()
    layout = QVBoxLayout()
    
    if 'error' in cluster_info:
        error_label = QLabel(f"PCA Error: {cluster_info['error']}")
        error_label.setStyleSheet("color: red;")
        layout.addWidget(error_label)
        widget.setLayout(layout)
        return widget
    
    # Create matplotlib figure
    fig = Figure(figsize=(12, 8))
    canvas = FigureCanvasQTAgg(fig)
    
    pca_components = cluster_info['pca_components']
    explained_variance = cluster_info['explained_variance']
    n_components = cluster_info['n_components']
    
    if n_components >= 2:
        # Create 2D scatter plot
        ax1 = fig.add_subplot(121)
        scatter = ax1.scatter(pca_components[:, 0], pca_components[:, 1], 
                             c=range(len(pca_components)), cmap='viridis', alpha=0.7)
        ax1.set_xlabel(f'PC1 ({explained_variance[0]:.1%} variance)')
        ax1.set_ylabel(f'PC2 ({explained_variance[1]:.1%} variance)')
        ax1.set_title('PCA: First Two Components')
        ax1.grid(True, alpha=0.3)
        
        # Add colorbar
        cbar = fig.colorbar(scatter, ax=ax1, shrink=0.8)
        cbar.set_label('Row Index')
    
    # Create variance explained plot
    if n_components >= 2:
        ax2 = fig.add_subplot(122)
    else:
        ax2 = fig.add_subplot(111)
        
    ax2.bar(range(1, len(explained_variance) + 1), explained_variance, alpha=0.7)
    ax2.plot(range(1, len(explained_variance) + 1), np.cumsum(explained_variance), 
             'ro-', linewidth=2, markersize=6)
    ax2.set_xlabel('Principal Component')
    ax2.set_ylabel('Variance Explained')
    ax2.set_title('PCA Variance Explained')
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(range(1, len(explained_variance) + 1))
    
    fig.tight_layout()
    
    layout.addWidget(canvas)
    widget.setLayout(layout)
    
    return widget


def _create_summary_tab(results):
    """Create summary statistics tab"""
    if not PYQT6_AVAILABLE:
        return None
        
    widget = QWidget()
    layout = QVBoxLayout()
    
    # Create scroll area for the summary
    scroll = QScrollArea()
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout()
    
    # Basic information
    info_label = QLabel("<h3>Similarity Analysis Summary</h3>")
    info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    scroll_layout.addWidget(info_label)
    
    # Dataset info
    dataset_info = f"""
    <b>Dataset Information:</b><br>
    • Original shape: {results.get('original_shape', 'N/A')}<br>
    • Processed shape: {results.get('processed_shape', 'N/A')}<br>
    • Numerical columns analyzed: {len(results.get('numerical_columns', []))}<br>
    """
    
    dataset_label = QLabel(dataset_info)
    dataset_label.setWordWrap(True)
    scroll_layout.addWidget(dataset_label)
    
    # Similar pairs information
    if 'similar_rows' in results and results['similar_rows']:
        similar_info = "<b>Most Similar Row Pairs:</b><br>"
        for i, pair in enumerate(results['similar_rows'][:3]):
            similar_info += f"• Row {pair[0]} ↔ Row {pair[1]}<br>"
        
        similar_label = QLabel(similar_info)
        similar_label.setWordWrap(True)
        scroll_layout.addWidget(similar_label)
    
    if 'similar_columns' in results and results['similar_columns']:
        col_similar_info = "<b>Most Similar Column Pairs:</b><br>"
        for i, pair in enumerate(results['similar_columns'][:3]):
            col_similar_info += f"• {pair[0]} ↔ {pair[1]}<br>"
        
        col_similar_label = QLabel(col_similar_info)
        col_similar_label.setWordWrap(True)
        scroll_layout.addWidget(col_similar_label)
    
    # PCA information
    if 'cluster_info' in results and 'explained_variance' in results['cluster_info']:
        cluster_info = results['cluster_info']
        pca_info = f"""
        <b>PCA Analysis:</b><br>
        • Components: {cluster_info['n_components']}<br>
        • Total variance explained: {cluster_info['cumulative_variance'][-1]:.1%}<br>
        • First component: {cluster_info['explained_variance'][0]:.1%}<br>
        """
        
        pca_label = QLabel(pca_info)
        pca_label.setWordWrap(True)
        scroll_layout.addWidget(pca_label)
    
    scroll_widget.setLayout(scroll_layout)
    scroll.setWidget(scroll_widget)
    scroll.setWidgetResizable(True)
    
    layout.addWidget(scroll)
    widget.setLayout(layout)
    
    return widget


def _create_data_preview_tab(original_df, results):
    """Create data preview tab with unusual rows highlighted"""
    if not PYQT6_AVAILABLE:
        return None
        
    widget = QWidget()
    layout = QVBoxLayout()
    
    # Create header label
    header_label = QLabel("<h3>Data Preview - Unusual Rows Highlighted</h3>")
    header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(header_label)
    
    # Calculate "unusualness" score for each row
    z_scores = results['z_scores']
    
    # Calculate unusualness as the sum of absolute z-scores for each row
    unusualness_scores = z_scores.abs().sum(axis=1)
    
    # Sort dataframe by unusualness (most unusual first)
    sorted_indices = unusualness_scores.sort_values(ascending=False).index
    sorted_df = original_df.loc[sorted_indices].copy()
    sorted_z_scores = z_scores.loc[sorted_indices]
    sorted_unusualness = unusualness_scores.loc[sorted_indices]
    
    # Add unusualness score as first column
    display_df = sorted_df.copy()
    display_df.insert(0, 'Unusualness_Score', sorted_unusualness.round(2))
    
    # Limit to top 50 rows for performance
    display_rows = min(50, len(display_df))
    display_df = display_df.head(display_rows)
    sorted_z_scores = sorted_z_scores.head(display_rows)
    
    # Create table view
    table_view = QTableView()
    model = QStandardItemModel()
    
    # Set headers
    headers = ['Row Index'] + list(display_df.columns)
    model.setHorizontalHeaderLabels(headers)
    
    # Populate table with data and coloring
    for row_idx, (orig_idx, row) in enumerate(display_df.iterrows()):
        # Add original row index as first column
        index_item = QStandardItem(str(orig_idx))
        index_item.setBackground(QBrush(QColor(240, 240, 240)))  # Light gray background
        model.setItem(row_idx, 0, index_item)
        
        # Add data columns
        for col_idx, (col_name, value) in enumerate(row.items()):
            item = QStandardItem(str(value))
            
            # Color based on unusualness and z-scores
            if col_name == 'Unusualness_Score':
                # Color unusualness score column
                unusualness = float(value)
                if unusualness > 6:  # Very unusual
                    item.setBackground(QBrush(QColor(255, 100, 100)))  # Red
                elif unusualness > 4:  # Unusual
                    item.setBackground(QBrush(QColor(255, 200, 100)))  # Orange
                elif unusualness > 2:  # Somewhat unusual
                    item.setBackground(QBrush(QColor(255, 255, 100)))  # Yellow
                else:  # Normal
                    item.setBackground(QBrush(QColor(200, 255, 200)))  # Light green
            else:
                # Color data columns based on z-scores
                if col_name in sorted_z_scores.columns:
                    z_score = sorted_z_scores.iloc[row_idx][col_name]
                    
                    if abs(z_score) > 3:  # Extreme outlier
                        item.setBackground(QBrush(QColor(255, 100, 100)))  # Red
                    elif abs(z_score) > 2:  # Outlier
                        item.setBackground(QBrush(QColor(255, 200, 100)))  # Orange
                    elif abs(z_score) > 1:  # Somewhat unusual
                        item.setBackground(QBrush(QColor(255, 255, 200)))  # Light yellow
                    # Normal values get no special coloring
            
            model.setItem(row_idx, col_idx + 1, item)
    
    table_view.setModel(model)
    
    # Configure table appearance
    table_view.setAlternatingRowColors(True)
    table_view.setSortingEnabled(True)
    table_view.horizontalHeader().setStretchLastSection(True)
    table_view.resizeColumnsToContents()
    
    # Create info panel
    info_text = f"""
    <b>Data Preview Information:</b><br>
    • Showing top {display_rows} most unusual rows (out of {len(original_df)})<br>
    • Rows sorted by unusualness score (sum of absolute z-scores)<br>
    • <span style='background-color: #ff6464; padding: 2px;'>Red</span>: Extreme values (|z-score| > 3 or unusualness > 6)<br>
    • <span style='background-color: #ffc864; padding: 2px;'>Orange</span>: Outliers (|z-score| > 2 or unusualness > 4)<br>
    • <span style='background-color: #ffff64; padding: 2px;'>Yellow</span>: Somewhat unusual (|z-score| > 1 or unusualness > 2)<br>
    • <span style='background-color: #c8ffc8; padding: 2px;'>Light Green</span>: Normal unusualness score<br>
    • White: Normal values<br><br>
    <b>Most Unusual Rows:</b><br>
    """
    
    # Add top 5 most unusual rows info
    for i in range(min(5, len(sorted_unusualness))):
        row_idx = sorted_unusualness.index[i]
        score = sorted_unusualness.iloc[i]
        info_text += f"• Row {row_idx}: unusualness score {score:.2f}<br>"
    
    info_label = QLabel(info_text)
    info_label.setWordWrap(True)
    info_label.setMaximumHeight(200)
    info_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc; }")
    
    # Add widgets to layout
    layout.addWidget(info_label)
    layout.addWidget(table_view)
    
    widget.setLayout(layout)
    return widget


def demo_similarity_analysis():
    """
    Demo function to showcase the similarity analysis capabilities
    Creates a sample dataset and demonstrates both analysis and visualization
    """
    print("Running Similarity Analysis Demo...")
    
    # Create sample data for testing
    np.random.seed(42)
    sample_df = pd.DataFrame({
        'revenue': np.random.normal(1000, 200, 80),
        'marketing_cost': np.random.normal(500, 100, 80),
        'customer_satisfaction': np.random.normal(4.0, 0.5, 80),
        'product_sales': np.random.normal(150, 30, 80)
    })
    
    # Create some correlations
    sample_df['product_sales'] = sample_df['revenue'] * 0.15 + np.random.normal(0, 20, 80)
    sample_df['marketing_cost'] = sample_df['revenue'] * 0.4 + np.random.normal(0, 50, 80)
    
    # Add some similar rows for testing similarity detection
    sample_df.iloc[40] = sample_df.iloc[10] + np.random.normal(0, 10, 4)
    sample_df.iloc[41] = sample_df.iloc[10] + np.random.normal(0, 15, 4)
    
    print(f"Created sample dataset: {sample_df.shape}")
    print(f"Columns: {list(sample_df.columns)}")
    
    # Test the profiler
    profiler = SimilarityProfiler()
    results = profiler.profile(sample_df)
    
    print("\nAnalysis Results:")
    print(f"✓ Analyzed {len(results.get('numerical_columns', []))} numerical columns")
    print(f"✓ Dataset shape: {results.get('original_shape', 'N/A')}")
    print(f"✓ Found {len(results.get('similar_rows', []))} similar row pairs")
    print(f"✓ Found {len(results.get('similar_columns', []))} similar column pairs")
    
    # Show most similar pairs
    if results.get('similar_rows'):
        print(f"\nMost similar rows:")
        for i, pair in enumerate(results['similar_rows'][:3]):
            distance = results['row_distances'].loc[pair[0], pair[1]]
            print(f"  {i+1}. Row {pair[0]} ↔ Row {pair[1]} (distance: {distance:.3f})")
    
    if results.get('similar_columns'):
        print(f"\nMost similar columns:")
        for i, pair in enumerate(results['similar_columns'][:3]):
            distance = results['column_distances'].loc[pair[0], pair[1]]
            print(f"  {i+1}. {pair[0]} ↔ {pair[1]} (distance: {distance:.3f})")

    # Demonstrate visualization
    print(f"\nCreating visualization...")
    print("Available visualization tabs:")
    print("  1. Z-Scores Heatmap - Shows standardized values")
    print("  2. Row Similarities - Distance matrix between rows")
    print("  3. Column Similarities - Distance matrix between columns") 
    print("  4. PCA Analysis - Principal component analysis")
    print("  5. Data Preview - Dataframe with unusual rows highlighted")
    print("  6. Summary - Text summary of results")
    
    # For SQLShell integration (widget only)
    widget = visualize_profile(sample_df, results, show_window=False)
    print(f"✓ Created widget for SQLShell: {type(widget)}")
    
    # Show the actual visualization window for demo
    print(f"\n🎯 Opening visualization window...")
    print("   Close the window to continue or press Ctrl+C to exit")
    
    # This will show the actual GUI window with all tabs
    visualize_profile(sample_df, results, show_window=True)
    
    return sample_df, results, widget


# Main function for testing
if __name__ == "__main__":
    print("="*60)
    print("SIMILARITY PROFILER DEMO")
    print("="*60)
    
    try:
        df, results, widget = demo_similarity_analysis()
        
        print(f"\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nTo use in your code:")
        print("1. from sqlshell.utils.profile_similarity import SimilarityProfiler, visualize_profile")
        print("2. profiler = SimilarityProfiler()")
        print("3. results = profiler.profile(your_dataframe)")
        print("4. widget = visualize_profile(your_dataframe, show_window=False)  # For SQLShell")
        print("5. visualize_profile(your_dataframe, show_window=True)   # For standalone")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()