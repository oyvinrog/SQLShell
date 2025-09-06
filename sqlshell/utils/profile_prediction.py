"""
Column Prediction Module

This module provides prediction functionality for columns using modern machine learning techniques.
It creates a new "Predict <column_name>" column with predictions based on other columns in the dataframe.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import mean_squared_error, accuracy_score, r2_score
import warnings
import joblib
import os
import json
from datetime import datetime
warnings.filterwarnings('ignore')

from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
                            QTableView, QPushButton, QProgressBar, QComboBox, QCheckBox,
                            QTextEdit, QSplitter, QHeaderView, QMessageBox, QGroupBox,
                            QFormLayout, QSpinBox, QDoubleSpinBox, QFileDialog)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QPalette, QBrush


class PredictionThread(QThread):
    """Worker thread for background prediction model training and evaluation"""
    
    progress = pyqtSignal(int, str)
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, df, target_column, prediction_type='auto', test_size=0.2, random_state=42):
        super().__init__()
        self.df = df.copy()
        self.target_column = target_column
        self.prediction_type = prediction_type
        self.test_size = test_size
        self.random_state = random_state
        self._is_canceled = False
        
    def cancel(self):
        """Mark the thread as canceled"""
        self._is_canceled = True
        
    def detect_prediction_type(self, target_series):
        """Automatically detect whether to use regression or classification"""
        if pd.api.types.is_numeric_dtype(target_series):
            # Check if it looks like a categorical variable (few unique values)
            unique_count = target_series.nunique()
            total_count = len(target_series.dropna())
            
            if unique_count <= 10 or (unique_count / total_count) < 0.05:
                return 'classification'
            else:
                return 'regression'
        else:
            return 'classification'
    
    def prepare_features(self, df, target_column):
        """Prepare features for machine learning"""
        # Separate features and target
        X_all = df.drop(columns=[target_column])
        y_all = df[target_column]
        
        # Identify rows with non-null targets (for training/testing)
        # and rows with null targets (for prediction)
        non_null_mask = ~pd.isna(y_all)
        null_mask = pd.isna(y_all)
        
        # Get training data (non-null targets only)
        X_train_data = X_all[non_null_mask]
        y_train_data = y_all[non_null_mask]
        
        if len(X_train_data) == 0:
            raise ValueError("No valid data with non-missing target values for training")
        
        # Handle categorical features for ALL data (including null targets)
        categorical_cols = X_all.select_dtypes(include=['object', 'category']).columns
        numerical_cols = X_all.select_dtypes(include=[np.number]).columns
        
        # Process features consistently across all data
        X_processed = X_all.copy()
        label_encoders = {}
        
        # Encode categorical variables
        for col in categorical_cols:
            # Fill missing values with 'missing'
            X_processed[col] = X_processed[col].fillna('missing')
            
            # Only encode if column has reasonable cardinality (based on training data)
            if X_train_data[col].fillna('missing').nunique() < len(X_train_data) * 0.5:
                le = LabelEncoder()
                # Fit encoder on all data (including null targets) to handle unseen categories
                le.fit(X_processed[col].astype(str))
                X_processed[col] = le.transform(X_processed[col].astype(str))
                label_encoders[col] = le
            else:
                # Drop high cardinality categorical columns
                X_processed = X_processed.drop(columns=[col])
        
        # Handle numerical features
        for col in numerical_cols:
            if col in X_processed.columns:  # Column might have been dropped
                # Fill missing values with median (computed from training data)
                median_val = X_train_data[col].median()
                X_processed[col] = X_processed[col].fillna(median_val)
        
        # Return processed features for training and the target values
        return X_processed[non_null_mask], y_train_data, label_encoders, X_processed, null_mask
    
    def run(self):
        try:
            if self._is_canceled:
                return
                
            self.progress.emit(10, "Preparing data...")
            
            # Check if target column exists
            if self.target_column not in self.df.columns:
                raise ValueError(f"Target column '{self.target_column}' not found")
            
            # Prepare features
            X, y, label_encoders, X_all, null_mask = self.prepare_features(self.df, self.target_column)
            
            if self._is_canceled:
                return
            
            self.progress.emit(25, "Determining prediction type...")
            
            # Determine prediction type if auto
            if self.prediction_type == 'auto':
                prediction_type = self.detect_prediction_type(y)
            else:
                prediction_type = self.prediction_type
            
            self.progress.emit(35, f"Using {prediction_type} approach...")
            
            # Encode target variable if classification
            target_encoder = None
            if prediction_type == 'classification' and not pd.api.types.is_numeric_dtype(y):
                target_encoder = LabelEncoder()
                y = target_encoder.fit_transform(y.astype(str))
            
            if self._is_canceled:
                return
            
            self.progress.emit(50, "Training models...")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.test_size, random_state=self.random_state
            )
            
            # Scale features for linear models
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            models = {}
            scores = {}
            predictions = {}
            
            if prediction_type == 'regression':
                # Train regression models
                models['Random Forest'] = RandomForestRegressor(
                    n_estimators=100, random_state=self.random_state, n_jobs=-1
                )
                models['Linear Regression'] = LinearRegression()
                
                for name, model in models.items():
                    if self._is_canceled:
                        return
                    
                    # Use scaled features for linear models
                    if 'Linear' in name:
                        model.fit(X_train_scaled, y_train)
                        pred = model.predict(X_test_scaled)
                        # Make predictions on test set + null target rows
                        # Test set predictions for validation
                        test_pred = pred
                        # Null target predictions (the main goal)
                        null_pred = model.predict(scaler.transform(X_all[null_mask])) if null_mask.any() else []
                    else:
                        model.fit(X_train, y_train)
                        pred = model.predict(X_test)
                        # Make predictions on test set + null target rows
                        # Test set predictions for validation
                        test_pred = pred
                        # Null target predictions (the main goal)
                        null_pred = model.predict(X_all[null_mask]) if null_mask.any() else []
                    
                    scores[name] = {
                        'mse': mean_squared_error(y_test, pred),
                        'r2': r2_score(y_test, pred)
                    }
                    # Combine test predictions and null predictions
                    all_pred = {
                        'test_predictions': test_pred,
                        'test_indices': X_test.index.tolist(),
                        'null_predictions': null_pred,
                        'null_indices': X_all[null_mask].index.tolist()
                    }
                    predictions[name] = all_pred
            
            else:  # classification
                # Train classification models
                models['Random Forest'] = RandomForestClassifier(
                    n_estimators=100, random_state=self.random_state, n_jobs=-1
                )
                models['Logistic Regression'] = LogisticRegression(
                    random_state=self.random_state, max_iter=1000
                )
                
                for name, model in models.items():
                    if self._is_canceled:
                        return
                    
                    # Use scaled features for linear models
                    if 'Logistic' in name:
                        model.fit(X_train_scaled, y_train)
                        pred = model.predict(X_test_scaled)
                        # Make predictions on test set + null target rows
                        # Test set predictions for validation
                        test_pred = pred
                        # Null target predictions (the main goal)
                        null_pred = model.predict(scaler.transform(X_all[null_mask])) if null_mask.any() else []
                    else:
                        model.fit(X_train, y_train)
                        pred = model.predict(X_test)
                        # Make predictions on test set + null target rows
                        # Test set predictions for validation
                        test_pred = pred
                        # Null target predictions (the main goal)
                        null_pred = model.predict(X_all[null_mask]) if null_mask.any() else []
                    
                    scores[name] = {
                        'accuracy': accuracy_score(y_test, pred)
                    }
                    # Combine test predictions and null predictions
                    all_pred = {
                        'test_predictions': test_pred,
                        'test_indices': X_test.index.tolist(),
                        'null_predictions': null_pred,
                        'null_indices': X_all[null_mask].index.tolist()
                    }
                    predictions[name] = all_pred
            
            if self._is_canceled:
                return
            
            self.progress.emit(90, "Finalizing results...")
            
            # Select best model
            if prediction_type == 'regression':
                best_model = max(scores.keys(), key=lambda k: scores[k]['r2'])
            else:
                best_model = max(scores.keys(), key=lambda k: scores[k]['accuracy'])
            
            # Get best predictions
            best_pred_dict = predictions[best_model]
            
            # Combine test and null predictions into single arrays
            combined_predictions = []
            combined_indices = []
            
            # Add test predictions
            test_preds = best_pred_dict['test_predictions']
            test_indices = best_pred_dict['test_indices']
            combined_predictions.extend(test_preds)
            combined_indices.extend(test_indices)
            
            # Add null predictions
            null_preds = best_pred_dict['null_predictions']
            null_indices = best_pred_dict['null_indices']
            combined_predictions.extend(null_preds)
            combined_indices.extend(null_indices)
            
            # Decode predictions if needed
            if target_encoder is not None and len(combined_predictions) > 0:
                # Convert to original labels
                try:
                    combined_predictions = target_encoder.inverse_transform(np.array(combined_predictions).astype(int))
                except:
                    # If conversion fails, use numeric predictions
                    pass
            
            # Create results dictionary with detailed breakdown
            results = {
                'prediction_type': prediction_type,
                'target_column': self.target_column,
                'best_model': best_model,
                'predictions': combined_predictions,
                'scores': scores,
                'feature_columns': list(X.columns),
                'target_encoder': target_encoder,
                'original_indices': combined_indices,  # Both test and null indices
                # Store trained models and preprocessing objects for saving
                'trained_models': models,
                'scaler': scaler,
                'label_encoders': label_encoders,
                # Additional info to help detect data leakage
                'data_breakdown': {
                    'total_rows': len(self.df),
                    'training_rows': len(X_train),
                    'test_rows': len(X_test),
                    'null_target_rows': null_mask.sum(),
                    'predicted_rows': len(combined_indices),
                    'test_size_percentage': self.test_size * 100
                }
            }
            
            self.progress.emit(100, "Complete!")
            self.result.emit(results)
            
        except Exception as e:
            self.error.emit(f"Prediction error: {str(e)}")


class PredictionResultsModel(QAbstractTableModel):
    """Table model for displaying prediction results"""
    
    def __init__(self, results_data):
        super().__init__()
        self.results_data = results_data
        self.headers = ['Model', 'Performance Metric', 'Score']
        
    def rowCount(self, parent=QModelIndex()):
        return len(self.results_data)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        row = index.row()
        col = index.column()
        
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.results_data[row][col])
        elif role == Qt.ItemDataRole.BackgroundRole and row == 0:
            # Highlight best model
            return QBrush(QColor(200, 255, 200))
            
        return None
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None


class PredictionDialog(QMainWindow):
    """Main dialog for displaying prediction results and applying predictions"""
    
    predictionApplied = pyqtSignal(object)  # Signal emitted when predictions are applied
    
    def __init__(self, df, target_column, parent=None):
        super().__init__(parent)
        self.df = df
        self.target_column = target_column
        self.prediction_results = None
        self.worker_thread = None
        
        self.setWindowTitle(f"Predict {target_column}")
        self.setGeometry(100, 100, 900, 700)
        
        # Make window stay on top and be modal
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create header
        header_label = QLabel(f"<h2>Predict Column: {target_column}</h2>")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)
        
        # Create info panel
        info_group = QGroupBox("Prediction Settings")
        info_layout = QFormLayout(info_group)
        
        # Test size spinner
        self.test_size_spin = QDoubleSpinBox()
        self.test_size_spin.setRange(0.1, 0.5)
        self.test_size_spin.setValue(0.2)
        self.test_size_spin.setSingleStep(0.05)
        info_layout.addRow("Test Size:", self.test_size_spin)
        
        # Prediction type combo
        self.prediction_type_combo = QComboBox()
        self.prediction_type_combo.addItems(['auto', 'regression', 'classification'])
        info_layout.addRow("Prediction Type:", self.prediction_type_combo)
        
        layout.addWidget(info_group)
        
        # Create splitter for results
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready to start prediction...")
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        # Results table
        self.results_table = QTableView()
        self.results_table.setMinimumHeight(200)
        
        # Results text area
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(150)
        self.results_text.setPlainText("Click 'Start Prediction' to begin analysis...")
        
        splitter.addWidget(progress_widget)
        splitter.addWidget(self.results_table)
        splitter.addWidget(self.results_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Prediction")
        self.start_button.clicked.connect(self.start_prediction)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_prediction)
        self.cancel_button.hide()
        
        self.apply_button = QPushButton(f"Apply Predictions (Add 'Predict {target_column}' Column)")
        self.apply_button.clicked.connect(self.apply_predictions)
        self.apply_button.setEnabled(False)
        
        self.save_model_button = QPushButton("Save Model")
        self.save_model_button.clicked.connect(self.save_model)
        self.save_model_button.setEnabled(False)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.save_model_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # Show the window and bring it to front
        print(f"DEBUG: About to show prediction dialog window")
        self.show()
        self.raise_()  # Bring to front
        self.activateWindow()  # Make it the active window
        
        # Additional window focus methods
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        
        print(f"DEBUG: Dialog window shown. Visible: {self.isVisible()}, Position: {self.geometry()}")
        print(f"DEBUG: Window title: {self.windowTitle()}")
    
    def start_prediction(self):
        """Start the prediction analysis"""
        try:
            self.start_button.setEnabled(False)
            self.apply_button.setEnabled(False)
            self.cancel_button.show()
            
            # Get settings
            test_size = self.test_size_spin.value()
            prediction_type = self.prediction_type_combo.currentText()
            
            self.progress_label.setText("Starting prediction analysis...")
            self.progress_bar.setValue(0)
            
            # Create and start worker thread
            self.worker_thread = PredictionThread(
                self.df, self.target_column, 
                prediction_type=prediction_type,
                test_size=test_size
            )
            self.worker_thread.progress.connect(self.update_progress)
            self.worker_thread.result.connect(self.handle_results)
            self.worker_thread.error.connect(self.handle_error)
            self.worker_thread.finished.connect(self.on_analysis_finished)
            self.worker_thread.start()
            
        except Exception as e:
            self.handle_error(f"Failed to start prediction: {str(e)}")
    
    def cancel_prediction(self):
        """Cancel the current prediction"""
        if self.worker_thread:
            self.worker_thread.cancel()
            self.worker_thread.quit()
            self.worker_thread.wait()
        self.on_analysis_finished()
    
    def update_progress(self, value, message):
        """Update progress bar and label"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def handle_results(self, results):
        """Handle prediction results"""
        self.prediction_results = results
        
        # Create table data for model comparison
        table_data = []
        for model_name, scores in results['scores'].items():
            if results['prediction_type'] == 'regression':
                table_data.append([
                    model_name,
                    'R² Score',
                    f"{scores['r2']:.4f}"
                ])
                table_data.append([
                    model_name,
                    'MSE',
                    f"{scores['mse']:.4f}"
                ])
            else:
                table_data.append([
                    model_name,
                    'Accuracy',
                    f"{scores['accuracy']:.4f}"
                ])
        
        # Sort by best performing model first
        if results['prediction_type'] == 'regression':
            table_data.sort(key=lambda x: float(x[2]) if x[1] == 'R² Score' else -float(x[2]), reverse=True)
        else:
            table_data.sort(key=lambda x: float(x[2]), reverse=True)
        
        # Set up table model
        model = PredictionResultsModel(table_data)
        self.results_table.setModel(model)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Update results text
        breakdown = results['data_breakdown']
        summary = f"""Prediction Analysis Complete!

Target Column: {results['target_column']}
Prediction Type: {results['prediction_type']}
Best Model: {results['best_model']}
Features Used: {len(results['feature_columns'])} columns

📊 DATA BREAKDOWN (for leak detection):
Total Rows: {breakdown['total_rows']}
Training Rows: {breakdown['training_rows']} ({breakdown['training_rows']/breakdown['total_rows']*100:.1f}%)
Test Rows: {breakdown['test_rows']} ({breakdown['test_size_percentage']:.1f}%)
NULL Target Rows: {breakdown['null_target_rows']}
Predicted Rows: {breakdown['predicted_rows']} (test + null targets)

⚠️  MODEL PERFORMANCE (on test set only):
Note: Scores below are ONLY on {breakdown['test_rows']} unseen test rows.
High scores are good, but should be realistic for your data.
"""
        for model_name, scores in results['scores'].items():
            summary += f"\n{model_name}:\n"
            for metric, score in scores.items():
                summary += f"  {metric}: {score:.4f}\n"
        
        summary += f"""
🔍 LEAK DETECTION GUIDE:
✅ GOOD: R² between 0.3-0.9 (depending on your data)
❌ SUSPICIOUS: R² > 0.95 (likely overfit or leakage)
✅ TRAINING SIZE: {breakdown['training_rows']} rows ({breakdown['training_rows']/breakdown['total_rows']*100:.1f}%)
✅ TEST SIZE: {breakdown['test_rows']} rows ({breakdown['test_size_percentage']:.1f}%)
✅ PREDICTIONS: Made for {breakdown['null_target_rows']} missing values + {breakdown['test_rows']} test rows"""
        
        self.results_text.setPlainText(summary)
        self.apply_button.setEnabled(True)
        self.save_model_button.setEnabled(True)
    
    def handle_error(self, error_message):
        """Handle prediction errors"""
        self.results_text.setPlainText(f"Error: {error_message}")
        QMessageBox.critical(self, "Prediction Error", error_message)
    
    def on_analysis_finished(self):
        """Handle cleanup when analysis is finished"""
        self.start_button.setEnabled(True)
        self.cancel_button.hide()
        self.progress_label.setText("Analysis complete")
    
    def apply_predictions(self):
        """Apply predictions to the dataframe"""
        if not self.prediction_results:
            return
        
        try:
            # Create a copy of the original dataframe
            result_df = self.df.copy()
            
            # Create prediction column name
            predict_column_name = f"Predict_{self.target_column}"
            
            # Prepare prediction values
            predictions = self.prediction_results['predictions']
            original_indices = self.prediction_results['original_indices']
            
            # Create prediction series with NaN values for all rows
            prediction_series = pd.Series([np.nan] * len(result_df), index=result_df.index, name=predict_column_name)
            
            # Fill predictions for rows that were in the test set AND rows with null targets
            for i, idx in enumerate(original_indices):
                if i < len(predictions) and idx in prediction_series.index:
                    prediction_series.loc[idx] = predictions[i]
            
            # Find the position of the target column
            target_column_index = result_df.columns.get_loc(self.target_column)
            
            # Insert the prediction column right after the target column
            # Split the dataframe into before and after the target column
            cols_before = result_df.columns[:target_column_index + 1].tolist()
            cols_after = result_df.columns[target_column_index + 1:].tolist()
            
            # Create new column order with prediction column inserted
            new_columns = cols_before + [predict_column_name] + cols_after
            
            # Add the prediction column to the dataframe
            result_df[predict_column_name] = prediction_series
            
            # Reorder columns to place prediction column next to target column
            result_df = result_df[new_columns]
            
            # Emit signal with the updated dataframe
            self.predictionApplied.emit(result_df)
            
            # Show success message
            QMessageBox.information(
                self, 
                "Predictions Applied", 
                f"Successfully added '{predict_column_name}' column with predictions from {self.prediction_results['best_model']} model."
            )
            
            self.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Apply Error", f"Failed to apply predictions: {str(e)}")
    
    def save_model(self):
        """Save the trained prediction model and preprocessing objects"""
        if not self.prediction_results:
            QMessageBox.warning(self, "No Model", "No model available to save. Please run prediction first.")
            return
        
        try:
            # Get the best model and preprocessing objects
            best_model_name = self.prediction_results['best_model']
            best_model = self.prediction_results['trained_models'][best_model_name]
            
            # Open file dialog to choose save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Prediction Model",
                f"{self.target_column}_prediction_model.pkl",
                "Pickle Files (*.pkl);;All Files (*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Create model package with all necessary components
            model_package = {
                'model': best_model,
                'model_name': best_model_name,
                'prediction_type': self.prediction_results['prediction_type'],
                'target_column': self.prediction_results['target_column'],
                'feature_columns': self.prediction_results['feature_columns'],
                'scaler': self.prediction_results['scaler'],
                'label_encoders': self.prediction_results['label_encoders'],
                'target_encoder': self.prediction_results['target_encoder'],
                'scores': self.prediction_results['scores'][best_model_name],
                'created_date': datetime.now().isoformat(),
                'sqlshell_version': '1.0',  # Could be made dynamic
                'sklearn_version': None  # Will be filled by joblib
            }
            
            # Save the model package
            joblib.dump(model_package, file_path)
            
            # Show success message
            QMessageBox.information(
                self,
                "Model Saved",
                f"Model saved successfully to:\n{file_path}\n\n"
                f"Model: {best_model_name}\n"
                f"Target: {self.target_column}\n"
                f"Features: {len(self.prediction_results['feature_columns'])} columns"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save model: {str(e)}")


def create_prediction_dialog(df, target_column, parent=None):
    """
    Main function to create and show the prediction dialog.
    
    Args:
        df (pd.DataFrame): The dataframe to analyze
        target_column (str): The column to predict
        parent: Parent window for the dialog
    
    Returns:
        PredictionDialog: The prediction dialog window
    """
    if df is None or df.empty:
        raise ValueError("DataFrame is empty or None")
    
    if target_column not in df.columns:
        raise ValueError(f"Column '{target_column}' not found in DataFrame")
    
    # Check if there are enough features for prediction
    if len(df.columns) < 2:
        raise ValueError("Need at least 2 columns for prediction (target + features)")
    
    # Create and return the dialog
    dialog = PredictionDialog(df, target_column, parent)
    return dialog


def load_and_apply_model(df, parent=None):
    """
    Load a saved prediction model and apply it to a new dataset.
    
    Args:
        df (pd.DataFrame): The dataframe to apply predictions to
        parent: Parent window for dialogs
    
    Returns:
        pd.DataFrame: DataFrame with predictions added, or None if cancelled/error
    """
    try:
        # Open file dialog to select model file
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Load Prediction Model",
            "",
            "Pickle Files (*.pkl);;All Files (*)"
        )
        
        if not file_path:
            return None  # User cancelled
        
        # Load the model package
        try:
            model_package = joblib.load(file_path)
        except Exception as e:
            QMessageBox.critical(parent, "Load Error", f"Failed to load model file:\n{str(e)}")
            return None
        
        # Validate model package structure
        required_keys = ['model', 'model_name', 'prediction_type', 'target_column', 
                        'feature_columns', 'scaler', 'label_encoders']
        missing_keys = [key for key in required_keys if key not in model_package]
        if missing_keys:
            QMessageBox.critical(
                parent, 
                "Invalid Model", 
                f"Model file is missing required components: {missing_keys}"
            )
            return None
        
        # Check feature compatibility
        model_features = set(model_package['feature_columns'])
        df_columns = set(df.columns)
        missing_features = model_features - df_columns
        
        if missing_features:
            QMessageBox.critical(
                parent,
                "Feature Mismatch",
                f"The current dataset is missing required features:\n{list(missing_features)}\n\n"
                f"Model requires: {model_package['feature_columns']}\n"
                f"Dataset has: {list(df.columns)}"
            )
            return None
        
        # Show model info and ask for confirmation
        model_info = f"""Model Information:
        
Model Name: {model_package['model_name']}
Original Target: {model_package['target_column']}
Prediction Type: {model_package['prediction_type']}
Features Required: {len(model_package['feature_columns'])} columns
Created: {model_package.get('created_date', 'Unknown')}

This will add a new 'Predict_{model_package['target_column']}' column to your dataset.

Continue with prediction?"""
        
        reply = QMessageBox.question(
            parent,
            "Apply Model",
            model_info,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return None
        
        # Apply the model
        result_df = apply_loaded_model_to_dataframe(df, model_package)
        
        if result_df is not None:
            QMessageBox.information(
                parent,
                "Predictions Applied",
                f"Successfully applied '{model_package['model_name']}' model.\n"
                f"Added 'Predict_{model_package['target_column']}' column with predictions."
            )
        
        return result_df
        
    except Exception as e:
        QMessageBox.critical(parent, "Error", f"Failed to apply model: {str(e)}")
        return None


def apply_loaded_model_to_dataframe(df, model_package):
    """
    Apply a loaded model package to a dataframe.
    
    Args:
        df (pd.DataFrame): The dataframe to apply predictions to
        model_package (dict): The loaded model package
    
    Returns:
        pd.DataFrame: DataFrame with predictions added
    """
    try:
        # Extract components from model package
        model = model_package['model']
        scaler = model_package['scaler']
        label_encoders = model_package['label_encoders']
        target_encoder = model_package.get('target_encoder')
        feature_columns = model_package['feature_columns']
        model_name = model_package['model_name']
        target_column = model_package['target_column']
        
        # Prepare features using the same preprocessing as during training
        X = df[feature_columns].copy()
        
        # Apply label encoders to categorical features
        for col, encoder in label_encoders.items():
            if col in X.columns:
                # Handle unseen categories by replacing with 'unknown'
                unique_train_values = set(encoder.classes_)
                X[col] = X[col].astype(str)
                X[col] = X[col].apply(lambda x: x if x in unique_train_values else 'unknown')
                
                # Add 'unknown' to encoder if not present
                if 'unknown' not in encoder.classes_:
                    # Create a new encoder with 'unknown' category
                    new_classes = list(encoder.classes_) + ['unknown']
                    encoder.classes_ = np.array(new_classes)
                
                X[col] = encoder.transform(X[col])
        
        # Handle missing values for numerical features
        numerical_cols = X.select_dtypes(include=[np.number]).columns
        for col in numerical_cols:
            if X[col].isnull().any():
                # Use median from the scaler's fitted data (approximate)
                median_val = X[col].median()
                X[col] = X[col].fillna(median_val)
        
        # Apply scaling
        if 'Linear' in model_name or 'Logistic' in model_name:
            X_processed = scaler.transform(X)
        else:
            X_processed = X.values
        
        # Make predictions
        predictions = model.predict(X_processed)
        
        # Decode predictions if target encoder exists
        if target_encoder is not None and len(predictions) > 0:
            try:
                predictions = target_encoder.inverse_transform(predictions.astype(int))
            except:
                # If decoding fails, keep numeric predictions
                pass
        
        # Create result dataframe
        result_df = df.copy()
        predict_column_name = f"Predict_{target_column}"
        result_df[predict_column_name] = predictions
        
        return result_df
        
    except Exception as e:
        raise Exception(f"Failed to apply model: {str(e)}")


def show_load_model_dialog(df, parent=None):
    """
    Convenience function to show load model dialog and apply predictions.
    
    Args:
        df (pd.DataFrame): The dataframe to apply predictions to
        parent: Parent window for dialogs
    
    Returns:
        pd.DataFrame: DataFrame with predictions added, or None if cancelled/error
    """
    if df is None or df.empty:
        QMessageBox.warning(parent, "No Data", "No data available. Please load some data first.")
        return None
    
    return load_and_apply_model(df, parent)