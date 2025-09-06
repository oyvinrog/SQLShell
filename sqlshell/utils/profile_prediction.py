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
warnings.filterwarnings('ignore')

from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
                            QTableView, QPushButton, QProgressBar, QComboBox, QCheckBox,
                            QTextEdit, QSplitter, QHeaderView, QMessageBox, QGroupBox,
                            QFormLayout, QSpinBox, QDoubleSpinBox)
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
        X = df.drop(columns=[target_column])
        y = df[target_column]
        
        # Remove rows with missing target values
        mask = ~pd.isna(y)
        X = X[mask]
        y = y[mask]
        
        if len(X) == 0:
            raise ValueError("No valid data after removing missing target values")
        
        # Handle categorical features
        categorical_cols = X.select_dtypes(include=['object', 'category']).columns
        numerical_cols = X.select_dtypes(include=[np.number]).columns
        
        # Encode categorical variables
        label_encoders = {}
        for col in categorical_cols:
            # Fill missing values with 'missing'
            X[col] = X[col].fillna('missing')
            
            # Only encode if column has reasonable cardinality
            if X[col].nunique() < len(X) * 0.5:  # Less than 50% unique values
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))
                label_encoders[col] = le
            else:
                # Drop high cardinality categorical columns
                X = X.drop(columns=[col])
        
        # Handle numerical features
        for col in numerical_cols:
            if col in X.columns:  # Column might have been dropped
                # Fill missing values with median
                X[col] = X[col].fillna(X[col].median())
        
        return X, y, label_encoders
    
    def run(self):
        try:
            if self._is_canceled:
                return
                
            self.progress.emit(10, "Preparing data...")
            
            # Check if target column exists
            if self.target_column not in self.df.columns:
                raise ValueError(f"Target column '{self.target_column}' not found")
            
            # Prepare features
            X, y, label_encoders = self.prepare_features(self.df, self.target_column)
            
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
                        # Make predictions on full dataset
                        full_pred = model.predict(scaler.transform(X))
                    else:
                        model.fit(X_train, y_train)
                        pred = model.predict(X_test)
                        # Make predictions on full dataset
                        full_pred = model.predict(X)
                    
                    scores[name] = {
                        'mse': mean_squared_error(y_test, pred),
                        'r2': r2_score(y_test, pred)
                    }
                    predictions[name] = full_pred
            
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
                        # Make predictions on full dataset
                        full_pred = model.predict(scaler.transform(X))
                    else:
                        model.fit(X_train, y_train)
                        pred = model.predict(X_test)
                        # Make predictions on full dataset
                        full_pred = model.predict(X)
                    
                    scores[name] = {
                        'accuracy': accuracy_score(y_test, pred)
                    }
                    predictions[name] = full_pred
            
            if self._is_canceled:
                return
            
            self.progress.emit(90, "Finalizing results...")
            
            # Select best model
            if prediction_type == 'regression':
                best_model = max(scores.keys(), key=lambda k: scores[k]['r2'])
            else:
                best_model = max(scores.keys(), key=lambda k: scores[k]['accuracy'])
            
            # Decode predictions if needed
            best_predictions = predictions[best_model]
            if target_encoder is not None:
                # Convert to original labels
                try:
                    best_predictions = target_encoder.inverse_transform(best_predictions.astype(int))
                except:
                    # If conversion fails, use numeric predictions
                    pass
            
            # Create results dictionary
            results = {
                'prediction_type': prediction_type,
                'target_column': self.target_column,
                'best_model': best_model,
                'predictions': best_predictions,
                'scores': scores,
                'feature_columns': list(X.columns),
                'target_encoder': target_encoder,
                'original_indices': X.index.tolist()
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
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
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
        summary = f"""Prediction Analysis Complete!

Target Column: {results['target_column']}
Prediction Type: {results['prediction_type']}
Best Model: {results['best_model']}
Features Used: {len(results['feature_columns'])} columns
Training Data: {len(results['original_indices'])} rows

Model Performance Summary:
"""
        for model_name, scores in results['scores'].items():
            summary += f"\n{model_name}:\n"
            for metric, score in scores.items():
                summary += f"  {metric}: {score:.4f}\n"
        
        self.results_text.setPlainText(summary)
        self.apply_button.setEnabled(True)
    
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
            predict_column_name = f"Predict {self.target_column}"
            
            # Prepare prediction values
            predictions = self.prediction_results['predictions']
            original_indices = self.prediction_results['original_indices']
            
            # Create prediction series with NaN values for all rows
            prediction_series = pd.Series([np.nan] * len(result_df), index=result_df.index, name=predict_column_name)
            
            # Fill predictions for rows that were used in training
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