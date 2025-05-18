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
from scipy.stats import chi2_contingency, pearsonr

# Import matplotlib at the top level
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import seaborn as sns
import matplotlib.pyplot as plt

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
        
    def calculate_correlation(self, x, y):
        """Calculate correlation between two variables, handling different data types.
        Returns absolute correlation value between 0 and 1."""
        try:
            # Handle missing values
            mask = ~(pd.isna(x) | pd.isna(y))
            x_clean = x[mask]
            y_clean = y[mask]
            
            # If too few data points, return default
            if len(x_clean) < 5:
                return 0.0
                
            # Check data types
            x_is_numeric = pd.api.types.is_numeric_dtype(x_clean)
            y_is_numeric = pd.api.types.is_numeric_dtype(y_clean)
            
            # Case 1: Both numeric - use Pearson correlation
            if x_is_numeric and y_is_numeric:
                corr, _ = pearsonr(x_clean, y_clean)
                return abs(corr)
            
            # Case 2: Categorical vs Categorical - use Cramer's V
            elif not x_is_numeric and not y_is_numeric:
                # Convert to categorical codes
                x_cat = pd.Categorical(x_clean).codes
                y_cat = pd.Categorical(y_clean).codes
                
                # Create contingency table
                contingency = pd.crosstab(x_cat, y_cat)
                
                # Calculate Cramer's V
                chi2, _, _, _ = chi2_contingency(contingency)
                n = contingency.sum().sum()
                phi2 = chi2 / n
                
                # Get dimensions
                r, k = contingency.shape
                
                # Calculate Cramer's V with correction for dimensions
                cramers_v = np.sqrt(phi2 / min(k-1, r-1)) if min(k-1, r-1) > 0 else 0.0
                return min(cramers_v, 1.0)  # Cap at 1.0
            
            # Case 3: Mixed types - convert to ranks or categories
            else:
                if x_is_numeric and not y_is_numeric:
                    # Convert categorical y to codes
                    y_encoded = pd.Categorical(y_clean).codes
                    
                    # Calculate correlation between x and encoded y
                    # Using point-biserial correlation (special case of Pearson)
                    corr, _ = pearsonr(x_clean, y_encoded)
                    return abs(corr)
                else:  # y is numeric, x is categorical
                    # Convert categorical x to codes
                    x_encoded = pd.Categorical(x_clean).codes
                    
                    # Calculate correlation
                    corr, _ = pearsonr(x_encoded, y_clean)
                    return abs(corr)
        
        except Exception as e:
            print(f"Error calculating correlation: {e}")
            return 0.0  # Return zero if correlation calculation fails

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

            # Early check for empty dataframe or no columns
            if self.df.empty or len(self.df.columns) == 0:
                raise ValueError("The dataframe is empty or has no columns for analysis")
                
            # No cache found, proceed with computation
            self.progress.emit(5, "Computing new analysis...")
            
            # Validate that the target column exists in the dataframe
            if self.column not in self.df.columns:
                raise ValueError(f"Target column '{self.column}' not found in the dataframe")
                
            # Create a copy to avoid modifying the original dataframe
            df = self.df.copy()
            
            # Verify we have data to work with
            if len(df) == 0:
                raise ValueError("No data available for analysis (empty dataframe)")
                
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
                    # Only drop columns with extremely high uniqueness (99% instead of 95%)
                    # This ensures we keep more features for analysis
                    if df[col].nunique() / len(df) > 0.99 and len(df) > 100:
                        cols_to_drop.append(col)
                    # Only drop columns with very high missing values (80% instead of 50%)
                    elif df[col].isna().mean() > 0.8:
                        cols_to_drop.append(col)
                except:
                    # If we can't analyze the column, drop it
                    cols_to_drop.append(col)
            
            # Drop identified columns, but ensure we keep at least some features
            remaining_cols = [col for col in df.columns if col != self.column and col not in cols_to_drop]
            
            # If dropping would leave us with no features, keep at least 3 columns (or all if less than 3)
            if len(remaining_cols) == 0 and len(cols_to_drop) > 0:
                # Sort dropped columns by uniqueness (keep those with lower uniqueness)
                col_uniqueness = {}
                for col in cols_to_drop:
                    try:
                        col_uniqueness[col] = df[col].nunique() / len(df)
                    except:
                        col_uniqueness[col] = 1.0  # Assume high uniqueness for problematic columns
                
                # Sort by uniqueness and keep the least unique columns
                cols_to_keep = sorted(col_uniqueness.items(), key=lambda x: x[1])[:min(3, len(cols_to_drop))]
                cols_to_drop = [col for col in cols_to_drop if col not in [c[0] for c in cols_to_keep]]
                print(f"Keeping {len(cols_to_keep)} columns to ensure analysis can proceed")
            
            if cols_to_drop:
                self.progress.emit(20, f"Removing {len(cols_to_drop)} low-information columns...")
                df = df.drop(columns=cols_to_drop)
            
            # Ensure target column is still in the dataframe
            if self.column not in df.columns:
                raise ValueError(f"Target column '{self.column}' not found in dataframe after preprocessing")
            
            # Calculate correlation coefficients first
            self.progress.emit(25, "Calculating correlation measures...")
            correlations = {}
            
            # Get all feature columns (excluding target)
            feature_cols = [col for col in df.columns if col != self.column]
            
            # Calculate correlation for each feature
            for col in feature_cols:
                try:
                    # Calculate correlation between each feature and target
                    cor_val = self.calculate_correlation(df[col], df[self.column])
                    correlations[col] = cor_val
                except Exception as e:
                    print(f"Error calculating correlation for {col}: {e}")
                    correlations[col] = 0.0
            
            # Separate features and target
            self.progress.emit(30, "Preparing features and target...")
            X = df.drop(columns=[self.column])
            y = df[self.column]
            
            # Handle high-cardinality categorical features
            self.progress.emit(35, "Encoding categorical features...")
            # Use a simpler approach - just one-hot encode columns with few unique values
            # and encode (don't drop) high-cardinality columns for speed
            categorical_cols = X.select_dtypes(include='object').columns
            high_cardinality_threshold = 20  # Higher threshold to keep more columns
            
            # Keep track of how many columns we've processed
            columns_processed = 0
            columns_kept = 0
            
            for col in categorical_cols:
                columns_processed += 1
                unique_count = X[col].nunique()
                # Always keep the column, but use different encoding strategies based on cardinality
                if unique_count <= high_cardinality_threshold:
                    # Simple label encoding for low-cardinality features
                    X[col] = X[col].fillna('_MISSING_').astype('category').cat.codes
                    columns_kept += 1
                else:
                    # For high-cardinality features, still encode them but with a simpler approach
                    # Use label encoding instead of dropping
                    X[col] = X[col].fillna('_MISSING_').astype('category').cat.codes
                    columns_kept += 1
            
            # Log how many columns were kept
            if columns_processed > 0:
                self.progress.emit(40, f"Encoded {columns_kept} categorical columns out of {columns_processed}")
            
            # Handle target column in a simpler, faster way
            if y.dtype == 'object':
                # For categorical targets, use simple category codes
                y = y.fillna('_MISSING_').astype('category').cat.codes
            else:
                # For numeric targets, just fill NaNs with mean
                y = y.fillna(y.mean() if pd.api.types.is_numeric_dtype(y) else y.mode()[0])

            # Train/test split
            self.progress.emit(45, "Splitting data into train/test sets...")
            
            # Make sure we still have features to work with
            if X.shape[1] == 0:
                raise ValueError("No features remain after preprocessing. Try selecting a different target column.")
                
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            # Check if canceled
            if self._is_canceled:
                return
                
            # Train a tree-based model
            self.progress.emit(50, "Training XGBoost model...")
            
            # Check the number of features left for analysis
            feature_count = X_train.shape[1]
            
            # Adjust model complexity based on feature count
            if feature_count < 3:
                max_depth = 1  # Very simple trees for few features
                n_estimators = 10  # Use more trees to compensate
            else:
                max_depth = 2  # Still shallow trees
                n_estimators = 5  # Fewer trees for more features
                
            model = xgb.XGBRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
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
                # Log the error for debugging
                print(f"Initial XGBoost fit failed: {str(e)}")
                
                # If we encounter an error, try with an even smaller and simpler model
                self.progress.emit(55, "Adjusting model parameters due to computational constraints...")
                try:
                    # Try a simpler regressor with more conservative parameters
                    model = xgb.XGBRegressor(
                        n_estimators=3, 
                        max_depth=1,
                        subsample=0.5,
                        colsample_bytree=0.5,
                        n_jobs=1,
                        verbosity=0
                    )
                    model.fit(X_train, y_train)
                except Exception as inner_e:
                    # If even the simpler model fails, resort to a fallback strategy
                    print(f"Even simpler XGBoost failed: {str(inner_e)}")
                    self.progress.emit(60, "Using fallback importance calculation method...")
                    
                    # Create a basic feature importance based on correlation with target
                    # This is a simple fallback when model training fails
                    importance = []
                    for col in X.columns:
                        try:
                            # Use pre-calculated correlations for fallback importance
                            corr_value = correlations.get(col, 0.5)
                            # Scale correlation to make a reasonable importance value
                            # Higher correlation = higher importance
                            importance.append(0.5 + corr_value/2 if not pd.isna(corr_value) else 0.5)
                        except:
                            # If correlation fails, use default
                            importance.append(0.5)
                    
                    # Normalize to sum to 1
                    importance = np.array(importance)
                    if sum(importance) > 0:
                        importance = importance / sum(importance)
                    else:
                        # Equal importance if everything fails
                        importance = np.ones(len(X.columns)) / len(X.columns)
                    
                    # Skip the model-based code path since we calculated importances manually
                    self.progress.emit(80, "Creating importance results...")
                    feature_importance = pd.DataFrame({
                        'feature': X.columns,
                        'importance_value': importance,
                        'correlation': [correlations.get(col, 0.0) for col in X.columns]
                    }).sort_values(by='importance_value', ascending=False)
                    
                    # Cache the results for future use
                    self.progress.emit(95, "Caching results for future use...")
                    cache_results(self.df, self.column, feature_importance)
                    
                    # Clean up after computation
                    del df, X, y, X_train, X_test, y_train, y_test
                    gc.collect()
                    
                    # Check if canceled
                    if self._is_canceled:
                        return
                        
                    # Emit the result
                    self.progress.emit(100, "Analysis complete (fallback method)")
                    self.result.emit(feature_importance)
                    return

            # Check if canceled
            if self._is_canceled:
                return
                
            # Get feature importance directly from XGBoost
            self.progress.emit(80, "Calculating feature importance and correlations...")
            
            try:
                # Check if we have features to analyze
                if X.shape[1] == 0:
                    raise ValueError("No features available for importance analysis")
                
                # Get feature importance directly from XGBoost
                importance = model.feature_importances_
                
                # Verify importance values are valid
                if np.isnan(importance).any() or np.isinf(importance).any():
                    # Handle NaN or Inf values
                    print("Warning: Invalid importance values detected, using fallback method")
                    # Replace with equal importance
                    importance = np.ones(len(X.columns)) / len(X.columns)
                
                # Create and sort the importance dataframe with correlations
                feature_importance = pd.DataFrame({
                    'feature': X.columns,
                    'importance_value': importance,
                    'correlation': [correlations.get(col, 0.0) for col in X.columns]
                }).sort_values(by='importance_value', ascending=False)
                
                # Cache the results for future use
                self.progress.emit(95, "Caching results for future use...")
                cache_results(self.df, self.column, feature_importance)
                
                # Clean up after computation
                del df, X, y, X_train, X_test, y_train, y_test, model
                gc.collect()
                
                # Check if canceled
                if self._is_canceled:
                    return
                    
                # Emit the result
                self.progress.emit(100, "Analysis complete")
                self.result.emit(feature_importance)
                return
                
            except Exception as e:
                print(f"Error in feature importance calculation: {e}")
                import traceback
                traceback.print_exc()
                
                # Create fallback importance values when model-based approach fails
                self.progress.emit(85, "Using alternative importance calculation method...")
                
                try:
                    # Try correlation-based approach first
                    importance = []
                    has_valid_correlations = False
                    
                    for col in X.columns:
                        try:
                            # Use pre-calculated correlations
                            corr = correlations.get(col, 0.1)
                            if not pd.isna(corr):
                                importance.append(corr)
                                has_valid_correlations = True
                            else:
                                importance.append(0.1)  # Default for failed correlation
                        except:
                            # Default value for any error
                            importance.append(0.1)
                    
                    # Normalize importance values
                    importance = np.array(importance)
                    if has_valid_correlations and sum(importance) > 0:
                        # If we have valid correlations, use them normalized
                        importance = importance / max(sum(importance), 0.001)
                    else:
                        # Otherwise use frequency-based heuristic
                        print("Using frequency-based feature importance as fallback")
                        # Count unique values as a proxy for importance
                        importance = []
                        total_rows = len(X)
                        
                        for col in X.columns:
                            try:
                                # More unique values could indicate more information content
                                # But we invert the ratio so columns with fewer unique values
                                # (more predictive) get higher importance
                                uniqueness = X[col].nunique() / total_rows
                                # Invert and scale between 0.1 and 1.0
                                val = 1.0 - (0.9 * uniqueness)
                                importance.append(max(0.1, min(1.0, val)))
                            except:
                                importance.append(0.1)  # Default value
                                
                        # Normalize
                        importance = np.array(importance)
                        importance = importance / max(sum(importance), 0.001)
                
                except Exception as fallback_error:
                    # Last resort: create equal importance for all features
                    print(f"Fallback error: {fallback_error}, using equal importance")
                    importance_values = np.ones(len(X.columns)) / max(len(X.columns), 1)
                    importance = importance_values
                
                # Create dataframe with results, including correlations
                feature_importance = pd.DataFrame({
                    'feature': X.columns,
                    'importance_value': importance,
                    'correlation': [correlations.get(col, 0.0) for col in X.columns]
                }).sort_values(by='importance_value', ascending=False)
                
                # Cache the results
                try:
                    cache_results(self.df, self.column, feature_importance)
                except:
                    pass  # Ignore cache errors
                
                # Clean up
                try:
                    del df, X, y, X_train, X_test, y_train, y_test
                    gc.collect()
                except:
                    pass
                
                # Emit the result
                self.progress.emit(100, "Analysis complete (with fallback methods)")
                self.result.emit(feature_importance)
                return

        except IndexError as e:
            # Handle index errors with more detail
            import traceback
            import inspect
            trace = traceback.format_exc()
            
            # Get more detailed information
            frame = inspect.trace()[-1]
            frame_info = inspect.getframeinfo(frame[0])
            filename = frame_info.filename
            lineno = frame_info.lineno
            function = frame_info.function
            code_context = frame_info.code_context[0].strip() if frame_info.code_context else "Unknown code context"
            
            # Format a more detailed error message
            detail_msg = f"IndexError: {str(e)}\nLocation: {filename}:{lineno} in function '{function}'\nCode: {code_context}\n\n{trace}"
            print(detail_msg)  # Print to console for debugging
            
            if not self._is_canceled:
                self.error.emit(f"Index error at line {lineno} in {function}:\n{str(e)}\nCode: {code_context}")
        
        except Exception as e:
            if not self._is_canceled:  # Only emit error if not canceled
                import traceback
                trace = traceback.format_exc()
                print(f"Error in ExplainerThread: {str(e)}")
                print(trace)  # Print full stack trace to help debug
                self.error.emit(f"{str(e)}\n\nTrace: {trace}")

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
        
        # Update importance table to include correlation column
        self.importance_table.setColumnCount(3)
        self.importance_table.setHorizontalHeaderLabels(["Feature", "Importance", "Abs. Correlation"])
        self.importance_table.setRowCount(len(importance_df))
        
        # Using a timer for incremental updates
        self.importance_df = importance_df  # Store for incremental rendering
        self.current_row = 0
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(lambda: self.render_next_batch(10))
        self.render_timer.start(10)  # Update every 10ms

    def render_next_batch(self, batch_size):
        try:
            if self.current_row >= len(self.importance_df):
                # All rows rendered, now render the chart and stop the timer
                self.render_chart()
                self.render_timer.stop()
                return
            
            # Render a batch of rows
            end_row = min(self.current_row + batch_size, len(self.importance_df))
            for row in range(self.current_row, end_row):
                try:
                    # Check if row exists in dataframe to prevent index errors
                    if row < len(self.importance_df):
                        feature = self.importance_df.iloc[row]['feature']
                        importance_value = self.importance_df.iloc[row]['importance_value']
                        
                        # Add correlation if available
                        correlation = self.importance_df.iloc[row].get('correlation', None)
                        if correlation is not None:
                            self.importance_table.setItem(row, 0, QTableWidgetItem(str(feature)))
                            self.importance_table.setItem(row, 1, QTableWidgetItem(str(round(importance_value, 4))))
                            self.importance_table.setItem(row, 2, QTableWidgetItem(str(round(correlation, 4))))
                        else:
                            self.importance_table.setItem(row, 0, QTableWidgetItem(str(feature)))
                            self.importance_table.setItem(row, 1, QTableWidgetItem(str(round(importance_value, 4))))
                    else:
                        # Handle out of range index
                        print(f"Warning: Row {row} is out of range (max: {len(self.importance_df)-1})")
                        self.importance_table.setItem(row, 0, QTableWidgetItem("Error"))
                        self.importance_table.setItem(row, 1, QTableWidgetItem("Out of range"))
                        self.importance_table.setItem(row, 2, QTableWidgetItem("N/A"))
                except (IndexError, KeyError) as e:
                    # Enhanced error reporting for index and key errors
                    import traceback
                    trace = traceback.format_exc()
                    error_msg = f"Error rendering row {row}: {e.__class__.__name__}: {e}\n{trace}"
                    print(error_msg)
                    
                    # Handle missing data in the dataframe gracefully
                    self.importance_table.setItem(row, 0, QTableWidgetItem(f"Error: {e.__class__.__name__}"))
                    self.importance_table.setItem(row, 1, QTableWidgetItem(f"{str(e)[:20]}"))
                    self.importance_table.setItem(row, 2, QTableWidgetItem("Error"))
                except Exception as e:
                    # Catch any other exceptions
                    print(f"Unexpected error rendering row {row}: {e.__class__.__name__}: {e}")
                    self.importance_table.setItem(row, 0, QTableWidgetItem(f"Error: {e.__class__.__name__}"))
                    self.importance_table.setItem(row, 1, QTableWidgetItem("See console for details"))
                    self.importance_table.setItem(row, 2, QTableWidgetItem("Error"))
                
            self.current_row = end_row
            QApplication.processEvents()  # Allow UI to update
        except Exception as e:
            # Catch any exceptions in the rendering loop itself
            import traceback
            trace = traceback.format_exc()
            error_msg = f"Error in render_next_batch: {e.__class__.__name__}: {e}\n{trace}"
            print(error_msg)
            
            # Try to stop the timer to prevent further errors
            try:
                if self.render_timer and self.render_timer.isActive():
                    self.render_timer.stop()
            except:
                pass
            
            # Show error
            QMessageBox.critical(self, "Rendering Error", 
                               f"Error rendering results: {e.__class__.__name__}: {e}")
        
    def render_chart(self):
        # Create horizontal bar chart
        try:
            if self.importance_df is None or len(self.importance_df) == 0:
                # No data to render
                self.chart_view.axes.clear()
                self.chart_view.axes.text(0.5, 0.5, "No data available for chart", 
                                      ha='center', va='center', fontsize=12, color='gray')
                self.chart_view.axes.set_axis_off()
                self.chart_view.draw()
                return
                
            self.chart_view.axes.clear()
            
            # Get a sorted copy based on current sort key
            plot_df = self.importance_df.sort_values(by=self.current_sort, ascending=False).head(20).copy()
            
            # Verify we have data before proceeding
            if len(plot_df) == 0:
                self.chart_view.axes.text(0.5, 0.5, "No features found with importance values", 
                                      ha='center', va='center', fontsize=12, color='gray')
                self.chart_view.axes.set_axis_off()
                self.chart_view.draw()
                return
            
            # Check required columns exist
            required_columns = ['feature', 'importance_value']
            missing_columns = [col for col in required_columns if col not in plot_df.columns]
            if missing_columns:
                error_msg = f"Missing required columns: {', '.join(missing_columns)}"
                self.chart_view.axes.text(0.5, 0.5, error_msg, 
                                      ha='center', va='center', fontsize=12, color='red')
                self.chart_view.axes.set_axis_off()
                self.chart_view.draw()
                print(f"Chart rendering error: {error_msg}")
                return
            
            # Truncate long feature names for better display
            max_feature_length = 30
            plot_df['display_feature'] = plot_df['feature'].apply(
                lambda x: (str(x)[:max_feature_length] + '...') if len(str(x)) > max_feature_length else str(x)
            )
            
            # Reverse order for better display (highest at top)
            plot_df = plot_df.iloc[::-1].reset_index(drop=True)
            
            # Create a figure with two subplots side by side
            self.chart_view.figure.clear()
            gs = self.chart_view.figure.add_gridspec(1, 2, width_ratios=[3, 2])
            
            # First subplot for importance
            ax1 = self.chart_view.figure.add_subplot(gs[0, 0])
            
            # Create a colormap for better visualization
            cmap = plt.cm.Blues
            colors = cmap(np.linspace(0.4, 0.8, len(plot_df)))
            
            # Plot with custom colors
            bars = ax1.barh(
                plot_df['display_feature'], 
                plot_df['importance_value'],
                color=colors,
                height=0.7,  # Thinner bars for more spacing
                alpha=0.8
            )
            
            # Add values at the end of bars
            for bar in bars:
                width = bar.get_width()
                ax1.text(
                    width * 1.05, 
                    bar.get_y() + bar.get_height()/2, 
                    f'{width:.2f}', 
                    va='center',
                    fontsize=9,
                    fontweight='bold'
                )
            
            # Add grid for better readability
            ax1.grid(True, axis='x', linestyle='--', alpha=0.3)
            
            # Remove unnecessary spines
            for spine in ['top', 'right']:
                ax1.spines[spine].set_visible(False)
            
            # Make labels more readable
            ax1.tick_params(axis='y', labelsize=9)
            
            # Set title and labels
            ax1.set_title(f'Feature Importance for {self.column_selector.currentText()}')
            ax1.set_xlabel('Importance Value')
            
            # Add a note about the sorting order
            sort_label = "Sorted by: " + ("Importance" if self.current_sort == 'importance_value' else "Correlation")
            
            # Second subplot for correlation if available
            if 'correlation' in plot_df.columns:
                ax2 = self.chart_view.figure.add_subplot(gs[0, 1], sharey=ax1)
                
                # Create a colormap for correlation - use a different color
                cmap_corr = plt.cm.Reds
                colors_corr = cmap_corr(np.linspace(0.4, 0.8, len(plot_df)))
                
                # Plot correlation bars
                corr_bars = ax2.barh(
                    plot_df['display_feature'],
                    plot_df['correlation'],
                    color=colors_corr,
                    height=0.7,
                    alpha=0.8
                )
                
                # Add values at the end of correlation bars
                for bar in corr_bars:
                    width = bar.get_width()
                    ax2.text(
                        width * 1.05,
                        bar.get_y() + bar.get_height()/2,
                        f'{width:.2f}',
                        va='center',
                        fontsize=9,
                        fontweight='bold'
                    )
                
                # Add grid and styling
                ax2.grid(True, axis='x', linestyle='--', alpha=0.3)
                ax2.set_title('Absolute Correlation')
                ax2.set_xlabel('Correlation Value')
                
                # Hide y-axis labels since they're shared with the first plot
                ax2.set_yticklabels([])
                
                # Remove unnecessary spines
                for spine in ['top', 'right']:
                    ax2.spines[spine].set_visible(False)
            
            # Add a note about the current sort order
            self.chart_view.figure.text(0.5, 0.01, sort_label, ha='center', fontsize=9, style='italic')
            
            # Adjust figure size based on number of features
            feature_count = len(plot_df)
            self.chart_view.figure.set_figheight(max(5, min(4 + feature_count * 0.3, 12)))
            
            # Adjust layout and draw
            self.chart_view.figure.tight_layout(rect=[0, 0.03, 1, 0.97])  # Make room for sort label
            self.chart_view.draw()
            
        except IndexError as e:
            # Special handling for index errors with detailed information
            import traceback
            import inspect
            
            # Get stack trace information
            trace = traceback.format_exc()
            
            # Try to get line and context information
            try:
                frame = inspect.trace()[-1]
                frame_info = inspect.getframeinfo(frame[0])
                filename = frame_info.filename
                lineno = frame_info.lineno
                function = frame_info.function
                code_context = frame_info.code_context[0].strip() if frame_info.code_context else "Unknown code context"
                
                # Detailed error message
                detail_msg = f"IndexError at line {lineno} in {function}: {str(e)}\nCode: {code_context}"
                print(f"Chart rendering error: {detail_msg}\n{trace}")
                
                # Display error in chart
                self.chart_view.axes.clear()
                self.chart_view.axes.text(0.5, 0.5, 
                                     f"Index Error in chart rendering:\n{str(e)}\nAt line {lineno}: {code_context}", 
                                     ha='center', va='center', fontsize=12, color='red',
                                     wrap=True)
                self.chart_view.axes.set_axis_off()
                self.chart_view.draw()
            except Exception as inner_e:
                # Fallback if the detailed error reporting fails
                print(f"Error getting detailed error info: {inner_e}")
                print(f"Original error: {e}\n{trace}")
                
                self.chart_view.axes.clear()
                self.chart_view.axes.text(0.5, 0.5, f"Index Error: {str(e)}", 
                                     ha='center', va='center', fontsize=12, color='red')
                self.chart_view.axes.set_axis_off()
                self.chart_view.draw()
        except Exception as e:
            # Recover gracefully from any chart rendering errors with detailed information
            import traceback
            trace = traceback.format_exc()
            error_msg = f"Error rendering chart: {e.__class__.__name__}: {str(e)}"
            print(f"{error_msg}\n{trace}")
            
            self.chart_view.axes.clear()
            self.chart_view.axes.text(0.5, 0.5, error_msg, 
                                  ha='center', va='center', fontsize=12, color='red',
                                  wrap=True)
            self.chart_view.axes.set_axis_off()
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
        
        # Show error message with more details
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText("An error occurred during analysis")
        msg_box.setDetailedText(error_message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        
        # Show a message in the UI as well
        self.importance_table.setRowCount(1)
        self.importance_table.setColumnCount(3)
        self.importance_table.setHorizontalHeaderLabels(["Feature", "Importance", "Abs. Correlation"])
        self.importance_table.setItem(0, 0, QTableWidgetItem(f"Error: {error_message.split('\n')[0]}"))
        self.importance_table.setItem(0, 1, QTableWidgetItem(""))
        self.importance_table.setItem(0, 2, QTableWidgetItem(""))
        self.importance_table.resizeColumnsToContents()
        
        # Update the chart to show error
        self.chart_view.axes.clear()
        self.chart_view.axes.text(0.5, 0.5, f"Error calculating importance:\n{error_message.split('\n')[0]}", 
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
        if self.importance_df is None or row < 0 or row >= len(self.importance_df):
            return
            
        # Get the feature name and target column
        try:
            feature = self.importance_df.iloc[row]['feature']
            target = self.column_selector.currentText()
            
            # Verify both columns exist in the dataframe
            if feature not in self.df.columns:
                QMessageBox.warning(self, "Column Not Found", 
                                   f"Feature column '{feature}' not found in the dataframe")
                return
                
            if target not in self.df.columns:
                QMessageBox.warning(self, "Column Not Found",
                                   f"Target column '{target}' not found in the dataframe")
                return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error getting column data: {str(e)}")
            return
        
        # Create a dialog to show the visualization
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Relationship: {feature} vs {target}")
        dialog.resize(900, 700)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Create canvas for the plot
        canvas = MatplotlibCanvas(width=8, height=6, dpi=100)
        layout.addWidget(canvas)
        
        # Determine the data types
        feature_is_numeric = pd.api.types.is_numeric_dtype(self.df[feature])
        target_is_numeric = pd.api.types.is_numeric_dtype(self.df[target])
        
        # Get unique counts to determine if we have high cardinality
        feature_unique_count = self.df[feature].nunique()
        target_unique_count = self.df[target].nunique()
        
        # Define high cardinality threshold
        high_cardinality_threshold = 10
        
        # Clear the figure
        canvas.axes.clear()
        
        # Create a working copy of the dataframe
        working_df = self.df.copy()
        
        # Prepare data for high cardinality columns
        if not feature_is_numeric and feature_unique_count > high_cardinality_threshold:
            # Get the top N categories by frequency
            top_categories = self.df[feature].value_counts().nlargest(high_cardinality_threshold).index.tolist()
            # Create "Other" category for remaining values
            working_df[feature] = working_df[feature].apply(lambda x: x if x in top_categories else 'Other')
            
        if not target_is_numeric and target_unique_count > high_cardinality_threshold:
            top_categories = self.df[target].value_counts().nlargest(high_cardinality_threshold).index.tolist()
            working_df[target] = working_df[target].apply(lambda x: x if x in top_categories else 'Other')
        
        # Create appropriate visualization based on data types and cardinality
        if feature_is_numeric and target_is_numeric:
            # Scatter plot for numeric vs numeric
            # Use hexbin for large datasets to avoid overplotting
            if len(working_df) > 100:
                canvas.axes.hexbin(
                    working_df[feature], 
                    working_df[target], 
                    gridsize=25, 
                    cmap='Blues',
                    mincnt=1
                )
                canvas.axes.set_title(f"Hexbin Density Plot: {feature} vs {target}")
                canvas.axes.set_xlabel(feature)
                canvas.axes.set_ylabel(target)
                # Add a colorbar
                cbar = canvas.figure.colorbar(canvas.axes.collections[0], ax=canvas.axes)
                cbar.set_label('Count')
            else:
                # For smaller datasets, use a scatter plot with transparency
                sns.scatterplot(
                    x=feature, 
                    y=target, 
                    data=working_df, 
                    ax=canvas.axes,
                    alpha=0.6
                )
                # Add regression line
                sns.regplot(
                    x=feature, 
                    y=target, 
                    data=working_df, 
                    ax=canvas.axes, 
                    scatter=False, 
                    line_kws={"color": "red"}
                )
                canvas.axes.set_title(f"Scatter Plot: {feature} vs {target}")
            
        elif feature_is_numeric and not target_is_numeric:
            # Box plot for numeric vs categorical
            if target_unique_count <= high_cardinality_threshold * 2:
                # Standard boxplot for reasonable number of categories
                order = working_df[target].value_counts().nlargest(high_cardinality_threshold * 2).index
                sns.boxplot(
                    x=target, 
                    y=feature, 
                    data=working_df, 
                    ax=canvas.axes, 
                    order=order
                )
                canvas.axes.set_title(f"Box Plot: {feature} by {target}")
                # Rotate x-axis labels for better readability
                canvas.axes.set_xticklabels(
                    canvas.axes.get_xticklabels(), 
                    rotation=45, 
                    ha='right'
                )
            else:
                # For very high cardinality, use a violin plot with limited categories
                order = working_df[target].value_counts().nlargest(high_cardinality_threshold).index
                working_df_filtered = working_df[working_df[target].isin(order)]
                sns.violinplot(
                    x=target, 
                    y=feature, 
                    data=working_df_filtered, 
                    ax=canvas.axes,
                    inner='quartile',
                    cut=0
                )
                canvas.axes.set_title(f"Violin Plot: {feature} by Top {len(order)} {target} Categories")
                canvas.axes.set_xticklabels(
                    canvas.axes.get_xticklabels(), 
                    rotation=45, 
                    ha='right'
                )
            
        elif not feature_is_numeric and target_is_numeric:
            # Bar plot for categorical vs numeric
            if feature_unique_count <= high_cardinality_threshold * 2:
                # Use standard barplot for reasonable number of categories
                order = working_df[feature].value_counts().nlargest(high_cardinality_threshold * 2).index
                sns.barplot(
                    x=feature, 
                    y=target, 
                    data=working_df, 
                    ax=canvas.axes,
                    order=order,
                    estimator=np.mean,
                    errorbar=('ci', 95),
                    capsize=0.2
                )
                canvas.axes.set_title(f"Bar Plot: Average {target} by {feature}")
                
                # Add value labels on top of bars
                for p in canvas.axes.patches:
                    canvas.axes.annotate(
                        f'{p.get_height():.1f}', 
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', 
                        va='bottom', 
                        fontsize=8, 
                        rotation=0
                    )
                
                # Rotate x-axis labels if needed
                if feature_unique_count > 5:
                    canvas.axes.set_xticklabels(
                        canvas.axes.get_xticklabels(), 
                        rotation=45, 
                        ha='right'
                    )
            else:
                # For high cardinality, use a horizontal bar plot with top N categories
                top_n = 15  # Show top 15 categories
                # Calculate mean of target for each feature category
                grouped = working_df.groupby(feature)[target].agg(['mean', 'count', 'std']).reset_index()
                # Sort by mean and take top categories
                top_groups = grouped.nlargest(top_n, 'mean')
                
                # Sort by mean value for better visualization
                sns.barplot(
                    y=feature, 
                    x='mean', 
                    data=top_groups, 
                    ax=canvas.axes,
                    orient='h'
                )
                canvas.axes.set_title(f"Top {top_n} Categories by Average {target}")
                canvas.axes.set_xlabel(f"Average {target}")
                
                # Add count annotations
                for i, row in enumerate(top_groups.itertuples()):
                    canvas.axes.text(
                        row.mean + 0.1, 
                        i, 
                        f'n={row.count}', 
                        va='center',
                        fontsize=8
                    )
            
        else:
            # Both feature and target are categorical
            if feature_unique_count <= high_cardinality_threshold and target_unique_count <= high_cardinality_threshold:
                # Heatmap for categorical vs categorical with manageable cardinality
                crosstab = pd.crosstab(
                    working_df[feature], 
                    working_df[target],
                    normalize='index'
                )
                
                # Create heatmap with improved readability
                sns.heatmap(
                    crosstab, 
                    annot=True, 
                    cmap="YlGnBu", 
                    ax=canvas.axes,
                    fmt='.2f',
                    linewidths=0.5,
                    annot_kws={"size": 9 if crosstab.size < 30 else 7}
                )
                canvas.axes.set_title(f"Heatmap: {feature} vs {target} (proportions)")
            else:
                # For high cardinality in both, show a count plot of top categories
                feature_top = working_df[feature].value_counts().nlargest(8).index
                target_top = working_df[target].value_counts().nlargest(5).index
                
                # Filter data to only include top categories
                filtered_df = working_df[
                    working_df[feature].isin(feature_top) & 
                    working_df[target].isin(target_top)
                ]
                
                # Create a grouped count plot
                sns.countplot(
                    x=feature,
                    hue=target,
                    data=filtered_df,
                    ax=canvas.axes
                )
                canvas.axes.set_title(f"Count Plot: Top {len(feature_top)} {feature} by Top {len(target_top)} {target}")
                
                # Rotate x-axis labels
                canvas.axes.set_xticklabels(
                    canvas.axes.get_xticklabels(), 
                    rotation=45, 
                    ha='right'
                )
                
                # Move legend to a better position
                canvas.axes.legend(title=target, bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Add informational text about data reduction if applicable
        if (not feature_is_numeric and feature_unique_count > high_cardinality_threshold) or \
           (not target_is_numeric and target_unique_count > high_cardinality_threshold):
            canvas.figure.text(
                0.5, 0.01, 
                f"Note: Visualization simplified to show top categories only. Original data has {feature_unique_count} unique {feature} values and {target_unique_count} unique {target} values.",
                ha='center', 
                fontsize=8, 
                style='italic'
            )
        
        # Adjust layout and draw
        canvas.figure.tight_layout()
        canvas.draw()
        
        # Add a close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        # Show the dialog
        dialog.exec()
        
    def change_sort(self, sort_key):
        """Change the sort order of the results"""
        if self.importance_df is None:
            return
            
        # Update button states
        if sort_key == 'importance_value':
            self.importance_sort_btn.setChecked(True)
            self.correlation_sort_btn.setChecked(False)
        else:
            self.importance_sort_btn.setChecked(False)
            self.correlation_sort_btn.setChecked(True)
            
        # Store the current sort key
        self.current_sort = sort_key
        
        # Re-sort the dataframe
        self.importance_df = self.importance_df.sort_values(by=sort_key, ascending=False)
        
        # Reset rendering of the table
        self.importance_table.clearContents()
        self.importance_table.setRowCount(len(self.importance_df))
        self.current_row = 0
        
        # Start incremental rendering with the new sort order
        if self.render_timer and self.render_timer.isActive():
            self.render_timer.stop()
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(lambda: self.render_next_batch(10))
        self.render_timer.start(10)  # Update every 10ms

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
        
        # Current sort key
        self.current_sort = 'importance_value'
        
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
        
        # Add sorting control
        sort_panel = QWidget()
        sort_layout = QHBoxLayout(sort_panel)
        sort_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add sort label
        sort_layout.addWidget(QLabel("Sort by:"))
        
        # Add sort buttons
        self.importance_sort_btn = QPushButton("Importance")
        self.importance_sort_btn.setCheckable(True)
        self.importance_sort_btn.setChecked(True)  # Default sort
        self.importance_sort_btn.clicked.connect(lambda: self.change_sort('importance_value'))
        
        self.correlation_sort_btn = QPushButton("Correlation")
        self.correlation_sort_btn.setCheckable(True)
        self.correlation_sort_btn.clicked.connect(lambda: self.change_sort('correlation'))
        
        sort_layout.addWidget(self.importance_sort_btn)
        sort_layout.addWidget(self.correlation_sort_btn)
        sort_layout.addStretch()
        
        # Add buttons to layout
        main_layout.addWidget(sort_panel)
        
        # Add a splitter for results area
        results_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Create table for showing importance values
        self.importance_table = QTableWidget()
        self.importance_table.setColumnCount(3)
        self.importance_table.setHorizontalHeaderLabels(["Feature", "Importance", "Abs. Correlation"])
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
        
        # Update importance table to include correlation column
        self.importance_table.setColumnCount(3)
        self.importance_table.setHorizontalHeaderLabels(["Feature", "Importance", "Abs. Correlation"])
        self.importance_table.setRowCount(len(importance_df))
        
        # Using a timer for incremental updates
        self.importance_df = importance_df  # Store for incremental rendering
        self.current_row = 0
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(lambda: self.render_next_batch(10))
        self.render_timer.start(10)  # Update every 10ms

    def render_next_batch(self, batch_size):
        try:
            if self.current_row >= len(self.importance_df):
                # All rows rendered, now render the chart and stop the timer
                self.render_chart()
                self.render_timer.stop()
                return
            
            # Render a batch of rows
            end_row = min(self.current_row + batch_size, len(self.importance_df))
            for row in range(self.current_row, end_row):
                try:
                    # Check if row exists in dataframe to prevent index errors
                    if row < len(self.importance_df):
                        feature = self.importance_df.iloc[row]['feature']
                        importance_value = self.importance_df.iloc[row]['importance_value']
                        
                        # Add correlation if available
                        correlation = self.importance_df.iloc[row].get('correlation', None)
                        if correlation is not None:
                            self.importance_table.setItem(row, 0, QTableWidgetItem(str(feature)))
                            self.importance_table.setItem(row, 1, QTableWidgetItem(str(round(importance_value, 4))))
                            self.importance_table.setItem(row, 2, QTableWidgetItem(str(round(correlation, 4))))
                        else:
                            self.importance_table.setItem(row, 0, QTableWidgetItem(str(feature)))
                            self.importance_table.setItem(row, 1, QTableWidgetItem(str(round(importance_value, 4))))
                    else:
                        # Handle out of range index
                        print(f"Warning: Row {row} is out of range (max: {len(self.importance_df)-1})")
                        self.importance_table.setItem(row, 0, QTableWidgetItem("Error"))
                        self.importance_table.setItem(row, 1, QTableWidgetItem("Out of range"))
                        self.importance_table.setItem(row, 2, QTableWidgetItem("N/A"))
                except (IndexError, KeyError) as e:
                    # Enhanced error reporting for index and key errors
                    import traceback
                    trace = traceback.format_exc()
                    error_msg = f"Error rendering row {row}: {e.__class__.__name__}: {e}\n{trace}"
                    print(error_msg)
                    
                    # Handle missing data in the dataframe gracefully
                    self.importance_table.setItem(row, 0, QTableWidgetItem(f"Error: {e.__class__.__name__}"))
                    self.importance_table.setItem(row, 1, QTableWidgetItem(f"{str(e)[:20]}"))
                    self.importance_table.setItem(row, 2, QTableWidgetItem("Error"))
                except Exception as e:
                    # Catch any other exceptions
                    print(f"Unexpected error rendering row {row}: {e.__class__.__name__}: {e}")
                    self.importance_table.setItem(row, 0, QTableWidgetItem(f"Error: {e.__class__.__name__}"))
                    self.importance_table.setItem(row, 1, QTableWidgetItem("See console for details"))
                    self.importance_table.setItem(row, 2, QTableWidgetItem("Error"))
                
            self.current_row = end_row
            QApplication.processEvents()  # Allow UI to update
        except Exception as e:
            # Catch any exceptions in the rendering loop itself
            import traceback
            trace = traceback.format_exc()
            error_msg = f"Error in render_next_batch: {e.__class__.__name__}: {e}\n{trace}"
            print(error_msg)
            
            # Try to stop the timer to prevent further errors
            try:
                if self.render_timer and self.render_timer.isActive():
                    self.render_timer.stop()
            except:
                pass
            
            # Show error
            QMessageBox.critical(self, "Rendering Error", 
                               f"Error rendering results: {e.__class__.__name__}: {e}")
        
    def render_chart(self):
        # Create horizontal bar chart
        try:
            if self.importance_df is None or len(self.importance_df) == 0:
                # No data to render
                self.chart_view.axes.clear()
                self.chart_view.axes.text(0.5, 0.5, "No data available for chart", 
                                      ha='center', va='center', fontsize=12, color='gray')
                self.chart_view.axes.set_axis_off()
                self.chart_view.draw()
                return
                
            self.chart_view.axes.clear()
            
            # Get a sorted copy based on current sort key
            plot_df = self.importance_df.sort_values(by=self.current_sort, ascending=False).head(20).copy()
            
            # Verify we have data before proceeding
            if len(plot_df) == 0:
                self.chart_view.axes.text(0.5, 0.5, "No features found with importance values", 
                                      ha='center', va='center', fontsize=12, color='gray')
                self.chart_view.axes.set_axis_off()
                self.chart_view.draw()
                return
            
            # Check required columns exist
            required_columns = ['feature', 'importance_value']
            missing_columns = [col for col in required_columns if col not in plot_df.columns]
            if missing_columns:
                error_msg = f"Missing required columns: {', '.join(missing_columns)}"
                self.chart_view.axes.text(0.5, 0.5, error_msg, 
                                      ha='center', va='center', fontsize=12, color='red')
                self.chart_view.axes.set_axis_off()
                self.chart_view.draw()
                print(f"Chart rendering error: {error_msg}")
                return
            
            # Truncate long feature names for better display
            max_feature_length = 30
            plot_df['display_feature'] = plot_df['feature'].apply(
                lambda x: (str(x)[:max_feature_length] + '...') if len(str(x)) > max_feature_length else str(x)
            )
            
            # Reverse order for better display (highest at top)
            plot_df = plot_df.iloc[::-1].reset_index(drop=True)
            
            # Create a figure with two subplots side by side
            self.chart_view.figure.clear()
            gs = self.chart_view.figure.add_gridspec(1, 2, width_ratios=[3, 2])
            
            # First subplot for importance
            ax1 = self.chart_view.figure.add_subplot(gs[0, 0])
            
            # Create a colormap for better visualization
            cmap = plt.cm.Blues
            colors = cmap(np.linspace(0.4, 0.8, len(plot_df)))
            
            # Plot with custom colors
            bars = ax1.barh(
                plot_df['display_feature'], 
                plot_df['importance_value'],
                color=colors,
                height=0.7,  # Thinner bars for more spacing
                alpha=0.8
            )
            
            # Add values at the end of bars
            for bar in bars:
                width = bar.get_width()
                ax1.text(
                    width * 1.05, 
                    bar.get_y() + bar.get_height()/2, 
                    f'{width:.2f}', 
                    va='center',
                    fontsize=9,
                    fontweight='bold'
                )
            
            # Add grid for better readability
            ax1.grid(True, axis='x', linestyle='--', alpha=0.3)
            
            # Remove unnecessary spines
            for spine in ['top', 'right']:
                ax1.spines[spine].set_visible(False)
            
            # Make labels more readable
            ax1.tick_params(axis='y', labelsize=9)
            
            # Set title and labels
            ax1.set_title(f'Feature Importance for {self.column_selector.currentText()}')
            ax1.set_xlabel('Importance Value')
            
            # Add a note about the sorting order
            sort_label = "Sorted by: " + ("Importance" if self.current_sort == 'importance_value' else "Correlation")
            
            # Second subplot for correlation if available
            if 'correlation' in plot_df.columns:
                ax2 = self.chart_view.figure.add_subplot(gs[0, 1], sharey=ax1)
                
                # Create a colormap for correlation - use a different color
                cmap_corr = plt.cm.Reds
                colors_corr = cmap_corr(np.linspace(0.4, 0.8, len(plot_df)))
                
                # Plot correlation bars
                corr_bars = ax2.barh(
                    plot_df['display_feature'],
                    plot_df['correlation'],
                    color=colors_corr,
                    height=0.7,
                    alpha=0.8
                )
                
                # Add values at the end of correlation bars
                for bar in corr_bars:
                    width = bar.get_width()
                    ax2.text(
                        width * 1.05,
                        bar.get_y() + bar.get_height()/2,
                        f'{width:.2f}',
                        va='center',
                        fontsize=9,
                        fontweight='bold'
                    )
                
                # Add grid and styling
                ax2.grid(True, axis='x', linestyle='--', alpha=0.3)
                ax2.set_title('Absolute Correlation')
                ax2.set_xlabel('Correlation Value')
                
                # Hide y-axis labels since they're shared with the first plot
                ax2.set_yticklabels([])
                
                # Remove unnecessary spines
                for spine in ['top', 'right']:
                    ax2.spines[spine].set_visible(False)
            
            # Add a note about the current sort order
            self.chart_view.figure.text(0.5, 0.01, sort_label, ha='center', fontsize=9, style='italic')
            
            # Adjust figure size based on number of features
            feature_count = len(plot_df)
            self.chart_view.figure.set_figheight(max(5, min(4 + feature_count * 0.3, 12)))
            
            # Adjust layout and draw
            self.chart_view.figure.tight_layout(rect=[0, 0.03, 1, 0.97])  # Make room for sort label
            self.chart_view.draw()
            
        except IndexError as e:
            # Special handling for index errors with detailed information
            import traceback
            import inspect
            
            # Get stack trace information
            trace = traceback.format_exc()
            
            # Try to get line and context information
            try:
                frame = inspect.trace()[-1]
                frame_info = inspect.getframeinfo(frame[0])
                filename = frame_info.filename
                lineno = frame_info.lineno
                function = frame_info.function
                code_context = frame_info.code_context[0].strip() if frame_info.code_context else "Unknown code context"
                
                # Detailed error message
                detail_msg = f"IndexError at line {lineno} in {function}: {str(e)}\nCode: {code_context}"
                print(f"Chart rendering error: {detail_msg}\n{trace}")
                
                # Display error in chart
                self.chart_view.axes.clear()
                self.chart_view.axes.text(0.5, 0.5, 
                                     f"Index Error in chart rendering:\n{str(e)}\nAt line {lineno}: {code_context}", 
                                     ha='center', va='center', fontsize=12, color='red',
                                     wrap=True)
                self.chart_view.axes.set_axis_off()
                self.chart_view.draw()
            except Exception as inner_e:
                # Fallback if the detailed error reporting fails
                print(f"Error getting detailed error info: {inner_e}")
                print(f"Original error: {e}\n{trace}")
                
                self.chart_view.axes.clear()
                self.chart_view.axes.text(0.5, 0.5, f"Index Error: {str(e)}", 
                                     ha='center', va='center', fontsize=12, color='red')
                self.chart_view.axes.set_axis_off()
                self.chart_view.draw()
        except Exception as e:
            # Recover gracefully from any chart rendering errors with detailed information
            import traceback
            trace = traceback.format_exc()
            error_msg = f"Error rendering chart: {e.__class__.__name__}: {str(e)}"
            print(f"{error_msg}\n{trace}")
            
            self.chart_view.axes.clear()
            self.chart_view.axes.text(0.5, 0.5, error_msg, 
                                  ha='center', va='center', fontsize=12, color='red',
                                  wrap=True)
            self.chart_view.axes.set_axis_off()
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
        
        # Show error message with more details
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText("An error occurred during analysis")
        msg_box.setDetailedText(error_message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        
        # Show a message in the UI as well
        self.importance_table.setRowCount(1)
        self.importance_table.setColumnCount(3)
        self.importance_table.setHorizontalHeaderLabels(["Feature", "Importance", "Abs. Correlation"])
        self.importance_table.setItem(0, 0, QTableWidgetItem(f"Error: {error_message.split('\n')[0]}"))
        self.importance_table.setItem(0, 1, QTableWidgetItem(""))
        self.importance_table.setItem(0, 2, QTableWidgetItem(""))
        self.importance_table.resizeColumnsToContents()
        
        # Update the chart to show error
        self.chart_view.axes.clear()
        self.chart_view.axes.text(0.5, 0.5, f"Error calculating importance:\n{error_message.split('\n')[0]}", 
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
        if self.importance_df is None or row < 0 or row >= len(self.importance_df):
            return
            
        # Get the feature name and target column
        try:
            feature = self.importance_df.iloc[row]['feature']
            target = self.column_selector.currentText()
            
            # Verify both columns exist in the dataframe
            if feature not in self.df.columns:
                QMessageBox.warning(self, "Column Not Found", 
                                   f"Feature column '{feature}' not found in the dataframe")
                return
                
            if target not in self.df.columns:
                QMessageBox.warning(self, "Column Not Found",
                                   f"Target column '{target}' not found in the dataframe")
                return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error getting column data: {str(e)}")
            return
        
        # Create a dialog to show the visualization
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Relationship: {feature} vs {target}")
        dialog.resize(900, 700)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Create canvas for the plot
        canvas = MatplotlibCanvas(width=8, height=6, dpi=100)
        layout.addWidget(canvas)
        
        # Determine the data types
        feature_is_numeric = pd.api.types.is_numeric_dtype(self.df[feature])
        target_is_numeric = pd.api.types.is_numeric_dtype(self.df[target])
        
        # Get unique counts to determine if we have high cardinality
        feature_unique_count = self.df[feature].nunique()
        target_unique_count = self.df[target].nunique()
        
        # Define high cardinality threshold
        high_cardinality_threshold = 10
        
        # Clear the figure
        canvas.axes.clear()
        
        # Create a working copy of the dataframe
        working_df = self.df.copy()
        
        # Prepare data for high cardinality columns
        if not feature_is_numeric and feature_unique_count > high_cardinality_threshold:
            # Get the top N categories by frequency
            top_categories = self.df[feature].value_counts().nlargest(high_cardinality_threshold).index.tolist()
            # Create "Other" category for remaining values
            working_df[feature] = working_df[feature].apply(lambda x: x if x in top_categories else 'Other')
            
        if not target_is_numeric and target_unique_count > high_cardinality_threshold:
            top_categories = self.df[target].value_counts().nlargest(high_cardinality_threshold).index.tolist()
            working_df[target] = working_df[target].apply(lambda x: x if x in top_categories else 'Other')
        
        # Create appropriate visualization based on data types and cardinality
        if feature_is_numeric and target_is_numeric:
            # Scatter plot for numeric vs numeric
            # Use hexbin for large datasets to avoid overplotting
            if len(working_df) > 100:
                canvas.axes.hexbin(
                    working_df[feature], 
                    working_df[target], 
                    gridsize=25, 
                    cmap='Blues',
                    mincnt=1
                )
                canvas.axes.set_title(f"Hexbin Density Plot: {feature} vs {target}")
                canvas.axes.set_xlabel(feature)
                canvas.axes.set_ylabel(target)
                # Add a colorbar
                cbar = canvas.figure.colorbar(canvas.axes.collections[0], ax=canvas.axes)
                cbar.set_label('Count')
            else:
                # For smaller datasets, use a scatter plot with transparency
                sns.scatterplot(
                    x=feature, 
                    y=target, 
                    data=working_df, 
                    ax=canvas.axes,
                    alpha=0.6
                )
                # Add regression line
                sns.regplot(
                    x=feature, 
                    y=target, 
                    data=working_df, 
                    ax=canvas.axes, 
                    scatter=False, 
                    line_kws={"color": "red"}
                )
                canvas.axes.set_title(f"Scatter Plot: {feature} vs {target}")
            
        elif feature_is_numeric and not target_is_numeric:
            # Box plot for numeric vs categorical
            if target_unique_count <= high_cardinality_threshold * 2:
                # Standard boxplot for reasonable number of categories
                order = working_df[target].value_counts().nlargest(high_cardinality_threshold * 2).index
                sns.boxplot(
                    x=target, 
                    y=feature, 
                    data=working_df, 
                    ax=canvas.axes, 
                    order=order
                )
                canvas.axes.set_title(f"Box Plot: {feature} by {target}")
                # Rotate x-axis labels for better readability
                canvas.axes.set_xticklabels(
                    canvas.axes.get_xticklabels(), 
                    rotation=45, 
                    ha='right'
                )
            else:
                # For very high cardinality, use a violin plot with limited categories
                order = working_df[target].value_counts().nlargest(high_cardinality_threshold).index
                working_df_filtered = working_df[working_df[target].isin(order)]
                sns.violinplot(
                    x=target, 
                    y=feature, 
                    data=working_df_filtered, 
                    ax=canvas.axes,
                    inner='quartile',
                    cut=0
                )
                canvas.axes.set_title(f"Violin Plot: {feature} by Top {len(order)} {target} Categories")
                canvas.axes.set_xticklabels(
                    canvas.axes.get_xticklabels(), 
                    rotation=45, 
                    ha='right'
                )
            
        elif not feature_is_numeric and target_is_numeric:
            # Bar plot for categorical vs numeric
            if feature_unique_count <= high_cardinality_threshold * 2:
                # Use standard barplot for reasonable number of categories
                order = working_df[feature].value_counts().nlargest(high_cardinality_threshold * 2).index
                sns.barplot(
                    x=feature, 
                    y=target, 
                    data=working_df, 
                    ax=canvas.axes,
                    order=order,
                    estimator=np.mean,
                    errorbar=('ci', 95),
                    capsize=0.2
                )
                canvas.axes.set_title(f"Bar Plot: Average {target} by {feature}")
                
                # Add value labels on top of bars
                for p in canvas.axes.patches:
                    canvas.axes.annotate(
                        f'{p.get_height():.1f}', 
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', 
                        va='bottom', 
                        fontsize=8, 
                        rotation=0
                    )
                
                # Rotate x-axis labels if needed
                if feature_unique_count > 5:
                    canvas.axes.set_xticklabels(
                        canvas.axes.get_xticklabels(), 
                        rotation=45, 
                        ha='right'
                    )
            else:
                # For high cardinality, use a horizontal bar plot with top N categories
                top_n = 15  # Show top 15 categories
                # Calculate mean of target for each feature category
                grouped = working_df.groupby(feature)[target].agg(['mean', 'count', 'std']).reset_index()
                # Sort by mean and take top categories
                top_groups = grouped.nlargest(top_n, 'mean')
                
                # Sort by mean value for better visualization
                sns.barplot(
                    y=feature, 
                    x='mean', 
                    data=top_groups, 
                    ax=canvas.axes,
                    orient='h'
                )
                canvas.axes.set_title(f"Top {top_n} Categories by Average {target}")
                canvas.axes.set_xlabel(f"Average {target}")
                
                # Add count annotations
                for i, row in enumerate(top_groups.itertuples()):
                    canvas.axes.text(
                        row.mean + 0.1, 
                        i, 
                        f'n={row.count}', 
                        va='center',
                        fontsize=8
                    )
            
        else:
            # Both feature and target are categorical
            if feature_unique_count <= high_cardinality_threshold and target_unique_count <= high_cardinality_threshold:
                # Heatmap for categorical vs categorical with manageable cardinality
                crosstab = pd.crosstab(
                    working_df[feature], 
                    working_df[target],
                    normalize='index'
                )
                
                # Create heatmap with improved readability
                sns.heatmap(
                    crosstab, 
                    annot=True, 
                    cmap="YlGnBu", 
                    ax=canvas.axes,
                    fmt='.2f',
                    linewidths=0.5,
                    annot_kws={"size": 9 if crosstab.size < 30 else 7}
                )
                canvas.axes.set_title(f"Heatmap: {feature} vs {target} (proportions)")
            else:
                # For high cardinality in both, show a count plot of top categories
                feature_top = working_df[feature].value_counts().nlargest(8).index
                target_top = working_df[target].value_counts().nlargest(5).index
                
                # Filter data to only include top categories
                filtered_df = working_df[
                    working_df[feature].isin(feature_top) & 
                    working_df[target].isin(target_top)
                ]
                
                # Create a grouped count plot
                sns.countplot(
                    x=feature,
                    hue=target,
                    data=filtered_df,
                    ax=canvas.axes
                )
                canvas.axes.set_title(f"Count Plot: Top {len(feature_top)} {feature} by Top {len(target_top)} {target}")
                
                # Rotate x-axis labels
                canvas.axes.set_xticklabels(
                    canvas.axes.get_xticklabels(), 
                    rotation=45, 
                    ha='right'
                )
                
                # Move legend to a better position
                canvas.axes.legend(title=target, bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Add informational text about data reduction if applicable
        if (not feature_is_numeric and feature_unique_count > high_cardinality_threshold) or \
           (not target_is_numeric and target_unique_count > high_cardinality_threshold):
            canvas.figure.text(
                0.5, 0.01, 
                f"Note: Visualization simplified to show top categories only. Original data has {feature_unique_count} unique {feature} values and {target_unique_count} unique {target} values.",
                ha='center', 
                fontsize=8, 
                style='italic'
            )
        
        # Adjust layout and draw
        canvas.figure.tight_layout()
        canvas.draw()
        
        # Add a close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        # Show the dialog
        dialog.exec()
        
    def change_sort(self, sort_key):
        """Change the sort order of the results"""
        if self.importance_df is None:
            return
            
        # Update button states
        if sort_key == 'importance_value':
            self.importance_sort_btn.setChecked(True)
            self.correlation_sort_btn.setChecked(False)
        else:
            self.importance_sort_btn.setChecked(False)
            self.correlation_sort_btn.setChecked(True)
            
        # Store the current sort key
        self.current_sort = sort_key
        
        # Re-sort the dataframe
        self.importance_df = self.importance_df.sort_values(by=sort_key, ascending=False)
        
        # Reset rendering of the table
        self.importance_table.clearContents()
        self.importance_table.setRowCount(len(self.importance_df))
        self.current_row = 0
        
        # Start incremental rendering with the new sort order
        if self.render_timer and self.render_timer.isActive():
            self.render_timer.stop()
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(lambda: self.render_next_batch(10))
        self.render_timer.start(10)  # Update every 10ms

# Custom matplotlib canvas for embedding in Qt
class MatplotlibCanvas(FigureCanvasQTAgg):
    def __init__(self, width=5, height=4, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.figure.add_subplot(111)
        super().__init__(self.figure)

def visualize_profile(df: pd.DataFrame, column: str = None) -> None:
    """
    Launch a PyQt6 UI for visualizing column importance.
    
    Args:
        df: DataFrame containing the data
        column: Optional target column to analyze immediately
    """
    try:
        # Verify df is a valid DataFrame
        if not isinstance(df, pd.DataFrame):
            raise ValueError("Input must be a pandas DataFrame")
            
        # Verify df has data
        if len(df) == 0:
            raise ValueError("DataFrame is empty, cannot analyze")
            
        # Verify columns exist
        if column is not None and column not in df.columns:
            raise ValueError(f"Column '{column}' not found in the DataFrame")
            
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
    # Create a sample DataFrame with 40 columns
    np.random.seed(42)
    n = 1000
    
    # Generate core sample data with known relationships
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
    
    # Create the base DataFrame
    data = {
        'Age': age,
        'Experience': experience,
        'Department': departments,
        'Education': education,
        'Performance': performance,
        'Salary': salary
    }
    
    # Generate additional numeric columns
    for i in range(1, 15):
        # Create some columns with relationship to salary
        if i <= 5:
            data[f'Metric_{i}'] = salary * (0.01 * i) + np.random.normal(0, 5000, n)
        # Create columns with relationship to age
        elif i <= 10:
            data[f'Metric_{i}'] = age * (i-5) + np.random.normal(0, 10, n)
        # Create random columns
        else:
            data[f'Metric_{i}'] = np.random.normal(100, 50, n)
    
    # Generate additional categorical columns
    categories = [
        ['A', 'B', 'C', 'D'],
        ['Low', 'Medium', 'High'],
        ['North', 'South', 'East', 'West'],
        ['Type1', 'Type2', 'Type3'],
        ['Yes', 'No', 'Maybe'],
        ['Red', 'Green', 'Blue', 'Yellow'],
        ['Small', 'Medium', 'Large']
    ]
    
    for i in range(1, 10):
        # Pick a category list
        cat_list = categories[i % len(categories)]
        # Generate random categorical column
        data[f'Category_{i}'] = np.random.choice(cat_list, n)
    
    # Generate date and time related columns
    base_date = np.datetime64('2020-01-01')
    
    # Instead of datetime objects, convert to days since base date (numeric values)
    hire_days = np.array([365 * (35 - a) + np.random.randint(0, 30) for a in age])
    data['Hire_Days_Ago'] = hire_days
    
    promotion_days = np.array([np.random.randint(0, 1000) for _ in range(n)])
    data['Last_Promotion_Days_Ago'] = promotion_days
    
    review_days = np.array([np.random.randint(1000, 1200) for _ in range(n)])
    data['Next_Review_In_Days'] = review_days
    
    # For reference, also store the actual dates as strings instead of datetime64
    data['Hire_Date_Str'] = [str(base_date + np.timedelta64(int(days), 'D')) for days in hire_days]
    data['Last_Promotion_Date_Str'] = [str(base_date + np.timedelta64(int(days), 'D')) for days in promotion_days]
    data['Review_Date_Str'] = [str(base_date + np.timedelta64(int(days), 'D')) for days in review_days]
    
    # Binary columns
    data['IsManager'] = np.random.choice([0, 1], n, p=[0.8, 0.2])
    data['RemoteWorker'] = np.random.choice([0, 1], n)
    data['HasHealthInsurance'] = np.random.choice([0, 1], n, p=[0.1, 0.9])
    data['HasRetirementPlan'] = np.random.choice([0, 1], n, p=[0.15, 0.85])
    
    # Columns with missing values
    data['OptionalMetric_1'] = np.random.normal(50, 10, n)
    data['OptionalMetric_1'][np.random.choice([True, False], n, p=[0.2, 0.8])] = np.nan
    
    data['OptionalMetric_2'] = np.random.normal(100, 20, n)
    data['OptionalMetric_2'][np.random.choice([True, False], n, p=[0.3, 0.7])] = np.nan
    
    data['OptionalCategory'] = np.random.choice(['Option1', 'Option2', 'Option3', None], n, p=[0.3, 0.3, 0.3, 0.1])
    
    # High cardinality column (like an ID)
    data['ID'] = [f"ID_{i:06d}" for i in range(n)]
    
    # Create the DataFrame with 40 columns
    df = pd.DataFrame(data)
    
    print(f"Created sample DataFrame with {len(df.columns)} columns and {len(df)} rows")
    print("Columns:", ', '.join(df.columns))
    print("Launching PyQt6 Column Profiler application...")
    visualize_profile(df, 'Salary')  # Start with Salary analysis

if __name__ == "__main__":
    test_profile()
