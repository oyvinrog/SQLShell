import shap
import pandas as pd
import xgboost as xgb
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import sys
import time
import hashlib
import os
import pickle
import gc
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, 
                             QVBoxLayout, QHBoxLayout, QLabel, QWidget, QComboBox, 
                             QPushButton, QSplitter, QHeaderView, QFrame, QProgressBar,
                             QMessageBox, QDialog)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPalette, QColor, QBrush, QPainter, QPen

# Import matplotlib at the top level
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import seaborn as sns

# Create a cache directory in user's home directory
CACHE_DIR = os.path.join(Path.home(), '.sqlshell_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_key(df, column):
    """Generate a cache key based on dataframe content and column"""
    # Get DataFrame characteristics that make it unique
    columns = ','.join(df.columns)
    shapes = f"{df.shape[0]}x{df.shape[1]}"
    col_types = ','.join(str(dtype) for dtype in df.dtypes)
    
    # Sample some values as fingerprint without loading entire dataframe
    sample_rows = min(50, len(df))
    values_sample = df.head(sample_rows).values.tobytes()
    
    # Create hash
    hash_input = f"{columns}|{shapes}|{col_types}|{column}|{len(df)}"
    m = hashlib.md5()
    m.update(hash_input.encode())
    m.update(values_sample)  # Add sample data to hash
    return m.hexdigest()

def cache_results(df, column, results):
    """Save results to disk cache"""
    try:
        cache_key = get_cache_key(df, column)
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(results, f)
        return True
    except Exception as e:
        print(f"Cache write error: {e}")
        return False

def get_cached_results(df, column):
    """Try to get results from disk cache"""
    try:
        cache_key = get_cache_key(df, column)
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            # Check if cache file is recent (less than 1 day old)
            mod_time = os.path.getmtime(cache_file)
            if time.time() - mod_time < 86400:  # 24 hours in seconds
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        return None
    except Exception as e:
        print(f"Cache read error: {e}")
        return None

# Worker thread for background processing
class ExplainerThread(QThread):
    # Signals for progress updates and results
    progress = pyqtSignal(int, str)
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, df, column):
        super().__init__()
        # Make a copy of the dataframe to avoid reference issues
        self.df = df.copy()
        self.column = column
        self._is_canceled = False
        
    def cancel(self):
        """Mark the thread as canceled"""
        self._is_canceled = True
        
    def run(self):
        try:
            # Check if canceled
            if self._is_canceled:
                return
                
            # Check disk cache first
            self.progress.emit(0, "Checking for cached results...")
            cached_results = get_cached_results(self.df, self.column)
            if cached_results is not None:
                # Check if canceled
                if self._is_canceled:
                    return
                    
                self.progress.emit(95, "Found cached results, loading...")
                time.sleep(0.5)  # Brief pause to show the user we found a cache
                
                # Check if canceled
                if self._is_canceled:
                    return
                    
                self.progress.emit(100, "Loaded from cache")
                self.result.emit(cached_results)
                return
            
            # Clean up memory before intensive computation
            gc.collect()
            
            # Check if canceled
            if self._is_canceled:
                return
                
            # No cache found, proceed with computation
            self.progress.emit(5, "Computing new analysis...")
            
            # Create a copy to avoid modifying the original dataframe
            df = self.df.copy()
            
            # Sample up to 500 rows for better statistical significance while maintaining speed
            if len(df) > 500:
                sample_size = 500  # Increased sample size for better analysis
                self.progress.emit(10, f"Sampling dataset (using {sample_size} rows from {len(df)} total)...")
                df = df.sample(n=sample_size, random_state=42)
                # Force garbage collection after sampling
                gc.collect()
            
            # Check if canceled
            if self._is_canceled:
                return
                
            # Drop columns with too many unique values (likely IDs) or excessive NaNs
            self.progress.emit(15, "Analyzing columns for preprocessing...")
            cols_to_drop = []
            for col in df.columns:
                if col == self.column:  # Don't drop target column
                    continue
                try:
                    # Drop if more than 95% unique values (likely ID column)
                    if df[col].nunique() / len(df) > 0.95:
                        cols_to_drop.append(col)
                    # Drop if more than 50% missing values
                    elif df[col].isna().mean() > 0.5:
                        cols_to_drop.append(col)
                except:
                    # If we can't analyze the column, drop it
                    cols_to_drop.append(col)
            
            # Drop identified columns
            if cols_to_drop:
                self.progress.emit(20, f"Removing {len(cols_to_drop)} low-information columns...")
                df = df.drop(columns=cols_to_drop)
            
            # Ensure target column is still in the dataframe
            if self.column not in df.columns:
                raise ValueError(f"Target column '{self.column}' not found in dataframe after preprocessing")
            
            # Separate features and target
            self.progress.emit(25, "Preparing features and target...")
            X = df.drop(columns=[self.column])
            y = df[self.column]
            
            # Handle high-cardinality categorical features
            self.progress.emit(30, "Encoding categorical features...")
            # Use a simpler approach - just one-hot encode columns with few unique values
            # and drop high-cardinality columns completely for speed
            categorical_cols = X.select_dtypes(include='object').columns
            high_cardinality_threshold = 10  # Lower threshold to drop more columns
            
            for col in categorical_cols:
                unique_count = X[col].nunique()
                if unique_count <= high_cardinality_threshold:
                    # Simple label encoding for low-cardinality features
                    X[col] = X[col].fillna('_MISSING_').astype('category').cat.codes
                else:
                    # Drop high-cardinality features to speed up analysis
                    X = X.drop(columns=[col])
            
            # Handle target column in a simpler, faster way
            if y.dtype == 'object':
                # For categorical targets, use simple category codes
                y = y.fillna('_MISSING_').astype('category').cat.codes
            else:
                # For numeric targets, just fill NaNs with mean
                y = y.fillna(y.mean() if pd.api.types.is_numeric_dtype(y) else y.mode()[0])

            # Train/test split
            self.progress.emit(40, "Splitting data into train/test sets...")
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            # Check if canceled
            if self._is_canceled:
                return
                
            # Train a tree-based model
            self.progress.emit(50, "Training XGBoost model...")
            model = xgb.XGBRegressor(
                n_estimators=5,              # Absolute minimum number of trees
                max_depth=2,                 # Very shallow trees
                learning_rate=0.3,           # Higher learning rate to compensate for fewer trees
                tree_method='hist',          # Fast histogram method
                subsample=0.7,               # Use 70% of data per tree
                grow_policy='depthwise',     # Simple growth policy
                n_jobs=1,                    # Single thread to avoid overhead
                random_state=42,
                verbosity=0                  # Suppress output
            )
            
            # Set memory conservation parameter for large datasets with many features
            if X_train.shape[1] > 100:  # If there are many features
                self.progress.emit(55, "Large feature set detected, using memory-efficient training...")
                model.set_params(grow_policy='lossguide', max_leaves=64)
            
            # Fit model with a try/except to catch memory issues
            try:
                model.fit(X_train, y_train)
            except Exception as e:
                # If we encounter an error, try with an even smaller and simpler model
                self.progress.emit(55, "Adjusting model parameters due to computational constraints...")
                model = xgb.XGBRegressor(
                    n_estimators=5, 
                    max_depth=2,
                    subsample=0.5,
                    colsample_bytree=0.5,
                    n_jobs=1
                )
                model.fit(X_train, y_train)

            # Check if canceled
            if self._is_canceled:
                return
                
            # Skip SHAP and use model feature importance directly for simplicity and reliability
            self.progress.emit(80, "Calculating feature importance...")
            
            try:
                # Get feature importance directly from XGBoost
                importance = model.feature_importances_
                
                # Create and sort the importance dataframe
                shap_importance = pd.DataFrame({
                    'feature': X.columns,
                    'mean_abs_shap': importance
                }).sort_values(by='mean_abs_shap', ascending=False)
                
                # Cache the results for future use
                self.progress.emit(95, "Caching results for future use...")
                cache_results(self.df, self.column, shap_importance)
                
                # Clean up after computation
                del df, X, y, X_train, X_test, y_train, y_test, model
                gc.collect()
                
                # Check if canceled
                if self._is_canceled:
                    return
                    
                # Emit the result
                self.progress.emit(100, "Analysis complete")
                self.result.emit(shap_importance)
                return
                
            except Exception as e:
                print(f"Error in feature importance calculation: {e}")
                import traceback
                traceback.print_exc()
                
                # Last resort: create equal importance for all features
                importance_values = np.ones(len(X.columns)) / len(X.columns)
                shap_importance = pd.DataFrame({
                    'feature': X.columns,
                    'mean_abs_shap': importance_values
                }).sort_values(by='mean_abs_shap', ascending=False)
                
                # Cache the results
                try:
                    cache_results(self.df, self.column, shap_importance)
                except:
                    pass  # Ignore cache errors
                
                # Clean up
                try:
                    del df, X, y, X_train, X_test, y_train, y_test, model
                    gc.collect()
                except:
                    pass
                
                # Emit the result
                self.progress.emit(100, "Analysis complete (with default values)")
                self.result.emit(shap_importance)
                return

        except Exception as e:
            if not self._is_canceled:  # Only emit error if not canceled
                import traceback
                print(f"Error in ExplainerThread: {str(e)}")
                print(traceback.format_exc())  # Print full stack trace to help debug
                self.error.emit(str(e))

    def analyze_column(self):
        if self.df is None or self.column_selector.currentText() == "":
            return
            
        # Cancel any existing worker thread
        if self.worker_thread and self.worker_thread.isRunning():
            # Signal the thread to cancel
            self.worker_thread.cancel()
            
            try:
                # Disconnect all signals to avoid callbacks during termination
                self.worker_thread.progress.disconnect()
                self.worker_thread.result.disconnect()
                self.worker_thread.error.disconnect()
                self.worker_thread.finished.disconnect()
            except Exception:
                pass  # Already disconnected
                
            # Terminate thread properly
            self.worker_thread.terminate()
            self.worker_thread.wait(1000)  # Wait up to 1 second
            self.worker_thread = None  # Clear reference
            
        target_column = self.column_selector.currentText()
        
        # Check in-memory cache first (fastest)
        if target_column in self.result_cache:
            self.handle_results(self.result_cache[target_column])
            return
            
        # Check global application-wide cache second (still fast)
        global_key = get_cache_key(self.df, target_column)
        if global_key in ColumnProfilerApp.global_cache:
            self.result_cache[target_column] = ColumnProfilerApp.global_cache[global_key]
            self.handle_results(self.result_cache[target_column])
            return
            
        # Disk cache will be checked in the worker thread
        
        # Disable the analyze button while processing
        self.analyze_button.setEnabled(False)
        
        # Show progress indicators
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.setText("Starting analysis...")
        self.progress_label.show()
        self.cancel_button.show()
        
        # Create and start the worker thread
        self.worker_thread = ExplainerThread(self.df, target_column)
        self.worker_thread.progress.connect(self.update_progress)
        self.worker_thread.result.connect(self.cache_and_display_results)
        self.worker_thread.error.connect(self.handle_error)
        self.worker_thread.finished.connect(self.on_analysis_finished)
        self.worker_thread.start()
    
    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def cache_and_display_results(self, importance_df):
        # Cache the results
        target_column = self.column_selector.currentText()
        self.result_cache[target_column] = importance_df
        
        # Also cache in the global application cache
        global_key = get_cache_key(self.df, target_column)
        ColumnProfilerApp.global_cache[global_key] = importance_df
        
        # Display the results
        self.handle_results(importance_df)
    
    def on_analysis_finished(self):
        """Handle cleanup when analysis is finished (either completed or cancelled)"""
        self.analyze_button.setEnabled(True)
        self.cancel_button.hide()
    
    def handle_results(self, importance_df):
        # Hide progress indicators
        self.progress_bar.hide()
        self.progress_label.hide()
        self.cancel_button.hide()
        
        # Update importance table incrementally
        self.importance_table.setRowCount(len(importance_df))
        
        # Using a timer for incremental updates
        self.importance_df = importance_df  # Store for incremental rendering
        self.current_row = 0
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(lambda: self.render_next_batch(10))
        self.render_timer.start(10)  # Update every 10ms
        
    def render_next_batch(self, batch_size):
        if self.current_row >= len(self.importance_df):
            # All rows rendered, now render the chart and stop the timer
            self.render_chart()
            self.render_timer.stop()
            return
            
        # Render a batch of rows
        end_row = min(self.current_row + batch_size, len(self.importance_df))
        for row in range(self.current_row, end_row):
            feature = self.importance_df.iloc[row]['feature']
            mean_abs_shap = self.importance_df.iloc[row]['mean_abs_shap']
            self.importance_table.setItem(row, 0, QTableWidgetItem(feature))
            self.importance_table.setItem(row, 1, QTableWidgetItem(str(round(mean_abs_shap, 4))))
            
        self.current_row = end_row
        QApplication.processEvents()  # Allow UI to update
        
    def render_chart(self):
        # Create horizontal bar chart
        self.chart_view.axes.clear()
        
        # Limit to top 20 features for better visualization
        plot_df = self.importance_df.head(20)
        
        # Plot with custom colors
        bars = self.chart_view.axes.barh(
            plot_df['feature'], 
            plot_df['mean_abs_shap'],
            color='skyblue'
        )
        
        # Add values at the end of bars
        for bar in bars:
            width = bar.get_width()
            self.chart_view.axes.text(
                width * 1.05, 
                bar.get_y() + bar.get_height()/2, 
                f'{width:.2f}', 
                va='center'
            )
            
        self.chart_view.axes.set_title(f'Feature Importance for Predicting {self.column_selector.currentText()}')
        self.chart_view.axes.set_xlabel('Mean Absolute SHAP Value')
        self.chart_view.figure.tight_layout()
        self.chart_view.draw()
        
    def handle_error(self, error_message):
        """Handle errors during analysis"""
        # Hide progress indicators
        self.progress_bar.hide()
        self.progress_label.hide()
        self.cancel_button.hide()
        
        # Re-enable analyze button
        self.analyze_button.setEnabled(True)
        
        # Print error to console for debugging
        print(f"Error in column profiler: {error_message}")
        
        # Show error message
        QMessageBox.critical(self, "Error", f"An error occurred during analysis:\n\n{error_message}")
        
        # Show a message in the UI as well
        self.importance_table.setRowCount(1)
        self.importance_table.setColumnCount(1)
        self.importance_table.setItem(0, 0, QTableWidgetItem(f"Error: {error_message}"))
        self.importance_table.resizeColumnsToContents()
        
        # Update the chart to show error
        self.chart_view.axes.clear()
        self.chart_view.axes.text(0.5, 0.5, f"Error calculating importance:\n{error_message}", 
                               ha='center', va='center', fontsize=12, color='red',
                               wrap=True)
        self.chart_view.axes.set_axis_off()
        self.chart_view.draw()
        
    def closeEvent(self, event):
        """Clean up when the window is closed"""
        # Stop any running timer
        if self.render_timer and self.render_timer.isActive():
            self.render_timer.stop()
            
        # Clean up any background threads
        if self.worker_thread and self.worker_thread.isRunning():
            # Disconnect all signals to avoid callbacks during termination
            try:
                self.worker_thread.progress.disconnect()
                self.worker_thread.result.disconnect()
                self.worker_thread.error.disconnect()
                self.worker_thread.finished.disconnect()
            except Exception:
                pass  # Already disconnected
                
            # Terminate thread properly
            self.worker_thread.terminate()
            self.worker_thread.wait(1000)  # Wait up to 1 second
            
        # Clear references to prevent thread issues
        self.worker_thread = None
            
        # Clean up memory
        self.result_cache.clear()
        
        # Accept the close event
        event.accept()
        
        # Suggest garbage collection
        gc.collect()

    def cancel_analysis(self):
        """Cancel the current analysis"""
        if self.worker_thread and self.worker_thread.isRunning():
            # Signal the thread to cancel first
            self.worker_thread.cancel()
            
            # Disconnect all signals to avoid callbacks during termination
            try:
                self.worker_thread.progress.disconnect()
                self.worker_thread.result.disconnect()
                self.worker_thread.error.disconnect()
                self.worker_thread.finished.disconnect()
            except Exception:
                pass  # Already disconnected
                
            # Terminate thread properly
            self.worker_thread.terminate() 
            self.worker_thread.wait(1000)  # Wait up to 1 second
            
            # Clear reference
            self.worker_thread = None
            
            # Update UI
            self.progress_bar.hide()
            self.progress_label.setText("Analysis cancelled")
            self.progress_label.show()
            self.cancel_button.hide()
            self.analyze_button.setEnabled(True)
            
            # Hide the progress label after 2 seconds
            QTimer.singleShot(2000, self.progress_label.hide)
            
# Custom matplotlib canvas for embedding in Qt
class MatplotlibCanvas(FigureCanvasQTAgg):
    def __init__(self, width=5, height=4, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.figure.add_subplot(111)
        super().__init__(self.figure)

# Main application class
class ColumnProfilerApp(QMainWindow):
    # Global application-wide cache to prevent redundant computations
    global_cache = {}
    
    def __init__(self, df):
        super().__init__()
        
        # Store reference to data
        self.df = df
        
        # Initialize cache for results
        self.result_cache = {}
        
        # Initialize thread variable
        self.worker_thread = None
        
        # Variables for incremental rendering
        self.importance_df = None
        self.current_row = 0
        self.render_timer = None
        
        # Set window properties
        self.setWindowTitle("Column Profiler")
        self.setMinimumSize(900, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Create top control panel
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        # Column selector
        self.column_selector = QComboBox()
        self.column_selector.addItems([col for col in df.columns])
        control_layout.addWidget(QLabel("Select Column to Analyze:"))
        control_layout.addWidget(self.column_selector)
        
        # Analyze button
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.clicked.connect(self.analyze_column)
        control_layout.addWidget(self.analyze_button)
        
        # Progress indicators
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.hide()
        self.progress_label = QLabel()
        self.progress_label.hide()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_analysis)
        self.cancel_button.hide()
        
        control_layout.addWidget(self.progress_bar)
        control_layout.addWidget(self.progress_label)
        control_layout.addWidget(self.cancel_button)
        
        # Add control panel to main layout
        main_layout.addWidget(control_panel)
        
        # Add a splitter for results area
        results_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Create table for showing importance values
        self.importance_table = QTableWidget()
        self.importance_table.setColumnCount(2)
        self.importance_table.setHorizontalHeaderLabels(["Feature", "Importance"])
        self.importance_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.importance_table.cellDoubleClicked.connect(self.show_relationship_visualization)
        results_splitter.addWidget(self.importance_table)
        
        # Add instruction label for double-click functionality
        instruction_label = QLabel("Double-click on any feature to view detailed relationship visualization with the target column")
        instruction_label.setStyleSheet("color: #666; font-style: italic;")
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(instruction_label)
        
        # Create matplotlib canvas for the chart
        self.chart_view = MatplotlibCanvas(width=8, height=5, dpi=100)
        results_splitter.addWidget(self.chart_view)
        
        # Set initial splitter sizes
        results_splitter.setSizes([300, 300])
        
        # Add the splitter to the main layout
        main_layout.addWidget(results_splitter)
        
        # Set the central widget
        self.setCentralWidget(central_widget)

    def analyze_column(self):
        if self.df is None or self.column_selector.currentText() == "":
            return
            
        # Cancel any existing worker thread
        if self.worker_thread and self.worker_thread.isRunning():
            # Signal the thread to cancel
            self.worker_thread.cancel()
            
            try:
                # Disconnect all signals to avoid callbacks during termination
                self.worker_thread.progress.disconnect()
                self.worker_thread.result.disconnect()
                self.worker_thread.error.disconnect()
                self.worker_thread.finished.disconnect()
            except Exception:
                pass  # Already disconnected
                
            # Terminate thread properly
            self.worker_thread.terminate()
            self.worker_thread.wait(1000)  # Wait up to 1 second
            self.worker_thread = None  # Clear reference
            
        target_column = self.column_selector.currentText()
        
        # Check in-memory cache first (fastest)
        if target_column in self.result_cache:
            self.handle_results(self.result_cache[target_column])
            return
            
        # Check global application-wide cache second (still fast)
        global_key = get_cache_key(self.df, target_column)
        if global_key in ColumnProfilerApp.global_cache:
            self.result_cache[target_column] = ColumnProfilerApp.global_cache[global_key]
            self.handle_results(self.result_cache[target_column])
            return
            
        # Disk cache will be checked in the worker thread
        
        # Disable the analyze button while processing
        self.analyze_button.setEnabled(False)
        
        # Show progress indicators
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.setText("Starting analysis...")
        self.progress_label.show()
        self.cancel_button.show()
        
        # Create and start the worker thread
        self.worker_thread = ExplainerThread(self.df, target_column)
        self.worker_thread.progress.connect(self.update_progress)
        self.worker_thread.result.connect(self.cache_and_display_results)
        self.worker_thread.error.connect(self.handle_error)
        self.worker_thread.finished.connect(self.on_analysis_finished)
        self.worker_thread.start()
    
    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def cache_and_display_results(self, importance_df):
        # Cache the results
        target_column = self.column_selector.currentText()
        self.result_cache[target_column] = importance_df
        
        # Also cache in the global application cache
        global_key = get_cache_key(self.df, target_column)
        ColumnProfilerApp.global_cache[global_key] = importance_df
        
        # Display the results
        self.handle_results(importance_df)
    
    def on_analysis_finished(self):
        """Handle cleanup when analysis is finished (either completed or cancelled)"""
        self.analyze_button.setEnabled(True)
        self.cancel_button.hide()
    
    def handle_results(self, importance_df):
        # Hide progress indicators
        self.progress_bar.hide()
        self.progress_label.hide()
        self.cancel_button.hide()
        
        # Update importance table incrementally
        self.importance_table.setRowCount(len(importance_df))
        
        # Using a timer for incremental updates
        self.importance_df = importance_df  # Store for incremental rendering
        self.current_row = 0
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(lambda: self.render_next_batch(10))
        self.render_timer.start(10)  # Update every 10ms
        
    def render_next_batch(self, batch_size):
        if self.current_row >= len(self.importance_df):
            # All rows rendered, now render the chart and stop the timer
            self.render_chart()
            self.render_timer.stop()
            return
            
        # Render a batch of rows
        end_row = min(self.current_row + batch_size, len(self.importance_df))
        for row in range(self.current_row, end_row):
            feature = self.importance_df.iloc[row]['feature']
            mean_abs_shap = self.importance_df.iloc[row]['mean_abs_shap']
            self.importance_table.setItem(row, 0, QTableWidgetItem(feature))
            self.importance_table.setItem(row, 1, QTableWidgetItem(str(round(mean_abs_shap, 4))))
            
        self.current_row = end_row
        QApplication.processEvents()  # Allow UI to update
        
    def render_chart(self):
        # Create horizontal bar chart
        self.chart_view.axes.clear()
        
        # Limit to top 20 features for better visualization
        plot_df = self.importance_df.head(20)
        
        # Plot with custom colors
        bars = self.chart_view.axes.barh(
            plot_df['feature'], 
            plot_df['mean_abs_shap'],
            color='skyblue'
        )
        
        # Add values at the end of bars
        for bar in bars:
            width = bar.get_width()
            self.chart_view.axes.text(
                width * 1.05, 
                bar.get_y() + bar.get_height()/2, 
                f'{width:.2f}', 
                va='center'
            )
            
        self.chart_view.axes.set_title(f'Feature Importance for Predicting {self.column_selector.currentText()}')
        self.chart_view.axes.set_xlabel('Mean Absolute SHAP Value')
        self.chart_view.figure.tight_layout()
        self.chart_view.draw()
        
    def handle_error(self, error_message):
        """Handle errors during analysis"""
        # Hide progress indicators
        self.progress_bar.hide()
        self.progress_label.hide()
        self.cancel_button.hide()
        
        # Re-enable analyze button
        self.analyze_button.setEnabled(True)
        
        # Print error to console for debugging
        print(f"Error in column profiler: {error_message}")
        
        # Show error message
        QMessageBox.critical(self, "Error", f"An error occurred during analysis:\n\n{error_message}")
        
        # Show a message in the UI as well
        self.importance_table.setRowCount(1)
        self.importance_table.setColumnCount(1)
        self.importance_table.setItem(0, 0, QTableWidgetItem(f"Error: {error_message}"))
        self.importance_table.resizeColumnsToContents()
        
        # Update the chart to show error
        self.chart_view.axes.clear()
        self.chart_view.axes.text(0.5, 0.5, f"Error calculating importance:\n{error_message}", 
                               ha='center', va='center', fontsize=12, color='red',
                               wrap=True)
        self.chart_view.axes.set_axis_off()
        self.chart_view.draw()
        
    def closeEvent(self, event):
        """Clean up when the window is closed"""
        # Stop any running timer
        if self.render_timer and self.render_timer.isActive():
            self.render_timer.stop()
            
        # Clean up any background threads
        if self.worker_thread and self.worker_thread.isRunning():
            # Disconnect all signals to avoid callbacks during termination
            try:
                self.worker_thread.progress.disconnect()
                self.worker_thread.result.disconnect()
                self.worker_thread.error.disconnect()
                self.worker_thread.finished.disconnect()
            except Exception:
                pass  # Already disconnected
                
            # Terminate thread properly
            self.worker_thread.terminate()
            self.worker_thread.wait(1000)  # Wait up to 1 second
            
        # Clear references to prevent thread issues
        self.worker_thread = None
            
        # Clean up memory
        self.result_cache.clear()
        
        # Accept the close event
        event.accept()
        
        # Suggest garbage collection
        gc.collect()

    def cancel_analysis(self):
        """Cancel the current analysis"""
        if self.worker_thread and self.worker_thread.isRunning():
            # Signal the thread to cancel first
            self.worker_thread.cancel()
            
            # Disconnect all signals to avoid callbacks during termination
            try:
                self.worker_thread.progress.disconnect()
                self.worker_thread.result.disconnect()
                self.worker_thread.error.disconnect()
                self.worker_thread.finished.disconnect()
            except Exception:
                pass  # Already disconnected
                
            # Terminate thread properly
            self.worker_thread.terminate() 
            self.worker_thread.wait(1000)  # Wait up to 1 second
            
            # Clear reference
            self.worker_thread = None
            
            # Update UI
            self.progress_bar.hide()
            self.progress_label.setText("Analysis cancelled")
            self.progress_label.show()
            self.cancel_button.hide()
            self.analyze_button.setEnabled(True)
            
            # Hide the progress label after 2 seconds
            QTimer.singleShot(2000, self.progress_label.hide)
            
    def show_relationship_visualization(self, row, column):
        """Show visualization of relationship between selected feature and target column"""
        if self.importance_df is None or row >= len(self.importance_df):
            return
            
        # Get the feature name and target column
        feature = self.importance_df.iloc[row]['feature']
        target = self.column_selector.currentText()
        
        # Create a dialog to show the visualization
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Relationship: {feature} vs {target}")
        dialog.resize(800, 600)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Create canvas for the plot
        canvas = MatplotlibCanvas(width=8, height=6, dpi=100)
        layout.addWidget(canvas)
        
        # Determine the data types
        feature_is_numeric = pd.api.types.is_numeric_dtype(self.df[feature])
        target_is_numeric = pd.api.types.is_numeric_dtype(self.df[target])
        
        # Clear the figure
        canvas.axes.clear()
        
        # Create appropriate visualization based on data types
        if feature_is_numeric and target_is_numeric:
            # Scatter plot for numeric vs numeric
            sns.scatterplot(x=feature, y=target, data=self.df, ax=canvas.axes)
            # Add regression line
            sns.regplot(x=feature, y=target, data=self.df, ax=canvas.axes, 
                        scatter=False, line_kws={"color": "red"})
            canvas.axes.set_title(f"Scatter Plot: {feature} vs {target}")
            
        elif feature_is_numeric and not target_is_numeric:
            # Box plot for numeric vs categorical
            sns.boxplot(x=target, y=feature, data=self.df, ax=canvas.axes)
            canvas.axes.set_title(f"Box Plot: {feature} by {target}")
            
        elif not feature_is_numeric and target_is_numeric:
            # Bar plot for categorical vs numeric
            sns.barplot(x=feature, y=target, data=self.df, ax=canvas.axes)
            canvas.axes.set_title(f"Bar Plot: Average {target} by {feature}")
            # Rotate x-axis labels if there are many categories
            if self.df[feature].nunique() > 5:
                canvas.axes.set_xticklabels(canvas.axes.get_xticklabels(), rotation=45, ha='right')
            
        else:
            # Heatmap for categorical vs categorical
            # Create a crosstab of the two categorical variables
            crosstab = pd.crosstab(self.df[feature], self.df[target], normalize='index')
            sns.heatmap(crosstab, annot=True, cmap="YlGnBu", ax=canvas.axes)
            canvas.axes.set_title(f"Heatmap: {feature} vs {target}")
        
        # Adjust layout and draw
        canvas.figure.tight_layout()
        canvas.draw()
        
        # Add a close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        # Show the dialog
        dialog.exec()

def visualize_profile(df: pd.DataFrame, column: str = None) -> None:
    """
    Launch a PyQt6 UI for visualizing column importance.
    
    Args:
        df: DataFrame containing the data
        column: Optional target column to analyze immediately
    """
    try:
        # Check if dataset is too small for meaningful analysis
        row_count = len(df)
        if row_count <= 5:
            print(f"WARNING: Dataset only has {row_count} rows. Feature importance analysis requires more data for meaningful results.")
            if QApplication.instance():
                QMessageBox.warning(None, "Insufficient Data", 
                                 f"The dataset only contains {row_count} rows. Feature importance analysis requires more data for meaningful results.")
        
        # For large datasets, sample up to 500 rows for better statistical significance
        elif row_count > 500:  
            print(f"Sampling 500 rows from dataset ({row_count:,} total rows)")
            df = df.sample(n=500, random_state=42)
        
        # Check if we're already in a Qt application
        existing_app = QApplication.instance()
        standalone_mode = existing_app is None
        
        # Create app if needed
        if standalone_mode:
            app = QApplication(sys.argv)
        else:
            app = existing_app
        
        app.setStyle('Fusion')  # Modern look
        
        # Set modern dark theme (only in standalone mode to avoid affecting parent app)
        if standalone_mode:
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
            palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
            app.setPalette(palette)
        
        window = ColumnProfilerApp(df)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # Ensure cleanup on close
        window.show()
        
        # Add tooltip to explain double-click functionality
        window.importance_table.setToolTip("Double-click on a feature to visualize its relationship with the target column")
        
        # If a specific column is provided, analyze it immediately
        if column is not None and column in df.columns:
            window.column_selector.setCurrentText(column)
            # Wrap the analysis in a try/except to prevent crashes
            def safe_analyze():
                try:
                    window.analyze_column()
                except Exception as e:
                    print(f"Error during column analysis: {e}")
                    import traceback
                    traceback.print_exc()
                    QMessageBox.critical(window, "Analysis Error", 
                                      f"Error analyzing column:\n\n{str(e)}")
            
            QTimer.singleShot(100, safe_analyze)  # Use timer to avoid immediate thread issues
            
            # Set a watchdog timer to cancel analysis if it takes too long (30 seconds)
            def check_progress():
                if window.worker_thread and window.worker_thread.isRunning():
                    # If still running after 30 seconds, cancel the operation
                    QMessageBox.warning(window, "Analysis Timeout", 
                                      "The analysis is taking longer than expected. It will be canceled to prevent hanging.")
                    try:
                        window.cancel_analysis()
                    except Exception as e:
                        print(f"Error canceling analysis: {e}")
                    
            QTimer.singleShot(30000, check_progress)  # 30 seconds timeout
        
        # Only enter event loop in standalone mode
        if standalone_mode:
            sys.exit(app.exec())
        else:
            # Return the window for parent app to track
            return window
    except Exception as e:
        # Handle any exceptions to prevent crashes
        print(f"Error in visualize_profile: {e}")
        import traceback
        traceback.print_exc()
        
        # Show error to user
        if QApplication.instance():
            QMessageBox.critical(None, "Profile Error", f"Error creating column profile:\n\n{str(e)}")
        return None

def test_profile():
    """
    Test the profile and visualization functions with sample data.
    """
    # Create a sample DataFrame
    np.random.seed(42)
    n = 1000
    
    # Generate sample data with known relationships
    age = np.random.normal(35, 10, n).astype(int)
    experience = age - np.random.randint(18, 25, n)  # experience correlates with age
    experience = np.maximum(0, experience)  # no negative experience
    
    salary = 30000 + 2000 * experience + np.random.normal(0, 10000, n)
    
    departments = np.random.choice(['Engineering', 'Marketing', 'Sales', 'HR', 'Finance'], n)
    education = np.random.choice(['High School', 'Bachelor', 'Master', 'PhD'], n, 
                               p=[0.2, 0.5, 0.2, 0.1])
    
    performance = np.random.normal(0, 1, n)
    performance += 0.5 * (education == 'Master') + 0.8 * (education == 'PhD')  # education affects performance
    performance += 0.01 * experience  # experience slightly affects performance
    performance = (performance - performance.min()) / (performance.max() - performance.min()) * 5  # scale to 0-5
    
    # Create the DataFrame
    df = pd.DataFrame({
        'Age': age,
        'Experience': experience,
        'Department': departments,
        'Education': education,
        'Performance': performance,
        'Salary': salary
    })
    
    print("Launching PyQt6 Column Profiler application...")
    visualize_profile(df, 'Salary')  # Start with Salary analysis

if __name__ == "__main__":
    test_profile()
