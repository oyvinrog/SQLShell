import shap
import pandas as pd
import xgboost as xgb
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, 
                             QVBoxLayout, QHBoxLayout, QLabel, QWidget, QComboBox, 
                             QPushButton, QSplitter, QHeaderView, QFrame)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QPalette, QColor, QBrush, QPainter, QPen
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

def explain(df: pd.DataFrame, column: str) -> pd.DataFrame:
    # Separate features and target
    X = df.drop(columns=[column])
    y = df[column]

    # Encode categorical features
    for col in X.select_dtypes(include='object').columns:
        X[col] = LabelEncoder().fit_transform(X[col].astype(str))
    if y.dtype == 'object':
        y = LabelEncoder().fit_transform(y.astype(str))

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train a tree-based model
    model = xgb.XGBRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # SHAP values
    explainer = shap.Explainer(model, X_train)
    shap_values = explainer(X_test)

    # Compute mean absolute SHAP values for each feature
    shap_importance = pd.DataFrame({
        'feature': X.columns,
        'mean_abs_shap': shap_values.abs.mean(axis=0).values
    }).sort_values(by='mean_abs_shap', ascending=False)

    return shap_importance

class MatplotlibCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MatplotlibCanvas, self).__init__(fig)

class ColumnProfilerApp(QMainWindow):
    def __init__(self, df=None):
        super().__init__()
        self.df = df
        self.setWindowTitle("Column Profiler")
        self.resize(1000, 700)
        self.setup_ui()
        
    def setup_ui(self):
        # Create the central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # Create splitter for top and bottom sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Top section - Controls and Data Preview
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.column_selector = QComboBox()
        controls_layout.addWidget(QLabel("Target Column:"))
        controls_layout.addWidget(self.column_selector)
        analyze_button = QPushButton("Analyze Column")
        analyze_button.clicked.connect(self.analyze_column)
        controls_layout.addWidget(analyze_button)
        controls_layout.addStretch()
        top_layout.addLayout(controls_layout)
        
        # Data preview table
        preview_label = QLabel("Data Preview:")
        top_layout.addWidget(preview_label)
        self.data_table = QTableWidget()
        top_layout.addWidget(self.data_table)
        
        # Bottom section - Results
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        
        # Feature importance table
        importance_frame = QFrame()
        importance_layout = QVBoxLayout(importance_frame)
        importance_layout.addWidget(QLabel("Feature Importance:"))
        self.importance_table = QTableWidget()
        self.importance_table.setColumnCount(2)
        self.importance_table.setHorizontalHeaderLabels(["Feature", "Importance"])
        self.importance_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        importance_layout.addWidget(self.importance_table)
        
        # Chart view
        chart_frame = QFrame()
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.addWidget(QLabel("Importance Visualization:"))
        self.chart_view = MatplotlibCanvas(self, width=5, height=4, dpi=100)
        chart_layout.addWidget(self.chart_view)
        
        # Add the two frames to bottom layout
        bottom_layout.addWidget(importance_frame)
        bottom_layout.addWidget(chart_frame)
        
        # Add widgets to splitter
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([300, 400])
        
        # Initialize with data if provided
        if self.df is not None:
            self.load_dataframe(self.df)
        
    def load_dataframe(self, df):
        self.df = df
        
        # Populate column selector
        self.column_selector.clear()
        self.column_selector.addItems(df.columns)
        
        # Update data preview table
        self.data_table.setRowCount(min(10, len(df)))
        self.data_table.setColumnCount(len(df.columns))
        self.data_table.setHorizontalHeaderLabels(df.columns)
        
        # Fill preview data
        for row in range(min(10, len(df))):
            for col, column_name in enumerate(df.columns):
                value = str(df.iloc[row, col])
                self.data_table.setItem(row, col, QTableWidgetItem(value))
        
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    
    def analyze_column(self):
        if self.df is None or self.column_selector.currentText() == "":
            return
            
        target_column = self.column_selector.currentText()
        
        # Get feature importance
        importance_df = explain(self.df, target_column)
        
        # Update importance table
        self.importance_table.setRowCount(len(importance_df))
        for row, (_, item) in enumerate(importance_df.iterrows()):
            self.importance_table.setItem(row, 0, QTableWidgetItem(item['feature']))
            self.importance_table.setItem(row, 1, QTableWidgetItem(str(round(item['mean_abs_shap'], 4))))
            
        # Create horizontal bar chart
        self.chart_view.axes.clear()
        
        # Plot with custom colors
        bars = self.chart_view.axes.barh(
            importance_df['feature'], 
            importance_df['mean_abs_shap'],
            color='skyblue'
        )
        
        # Add values at the end of bars
        for bar in bars:
            width = bar.get_width()
            self.chart_view.axes.text(
                width * 1.05, 
                bar.get_y() + bar.get_height()/2, 
                f'{width:.1f}', 
                va='center'
            )
            
        self.chart_view.axes.set_title(f'Feature Importance for Predicting {target_column}')
        self.chart_view.axes.set_xlabel('Mean Absolute SHAP Value')
        self.chart_view.figure.tight_layout()
        self.chart_view.draw()
        
def visualize_profile(df: pd.DataFrame, column: str = None) -> None:
    """
    Launch a PyQt6 UI for visualizing column importance.
    
    Args:
        df: DataFrame containing the data
        column: Optional target column to analyze immediately
    """
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    # Set modern dark theme
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
    window.show()
    
    # If a specific column is provided, analyze it immediately
    if column is not None and column in df.columns:
        window.column_selector.setCurrentText(column)
        window.analyze_column()
    
    sys.exit(app.exec())

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
