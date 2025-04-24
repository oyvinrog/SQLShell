import sys
import itertools
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QMainWindow
)
from PyQt6.QtCore import Qt


def find_functional_dependencies(df: pd.DataFrame, max_lhs_size: int = 2):
    """
    Discover all functional dependencies X -> A in the DataFrame for |X| <= max_lhs_size.
    Returns a list of tuples (lhs, rhs).
    """
    fds = []
    cols = list(df.columns)
    n_rows = len(df)

    for size in range(1, max_lhs_size + 1):
        for lhs in itertools.combinations(cols, size):
            # for each potential dependent attribute not in lhs
            lhs_df = df[list(lhs)]
            # group by lhs and count distinct values of each other column
            grouped = df.groupby(list(lhs))
            for rhs in cols:
                if rhs in lhs:
                    continue
                # Check if for each group, rhs has only one distinct value
                distinct_counts = grouped[rhs].nunique(dropna=False)
                if (distinct_counts <= 1).all():
                    fds.append((lhs, rhs))
    return fds


def profile(df: pd.DataFrame, max_combination_size: int = 2, max_lhs_size: int = 2):
    """
    Analyze a pandas DataFrame to suggest candidate keys and discover functional dependencies.

    Parameters:
    - df: pandas.DataFrame to analyze.
    - max_combination_size: max size of column combos to test for keys.
    - max_lhs_size: max size of LHS in discovered FDs.
    
    Returns:
    - Tuple of (fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size)
    """
    n_rows = len(df)
    cols = list(df.columns)

    # Discover functional dependencies
    fds = find_functional_dependencies(df, max_lhs_size)

    # Prepare FD results
    fd_results = [(", ".join(lhs), rhs) for lhs, rhs in fds]

    # Profile candidate keys (by uniqueness)
    results = []
    for size in range(1, max_combination_size + 1):
        for combo in itertools.combinations(cols, size):
            unique_count = df.drop_duplicates(subset=combo).shape[0]
            unique_ratio = unique_count / n_rows
            is_key = unique_count == n_rows
            results.append((combo, unique_count, unique_ratio, is_key))
    results.sort(key=lambda x: (not x[3], -x[2], len(x[0])))
    key_results = [(", ".join(c), u, f"{u/n_rows:.2%}", "✅" if k else "")
                   for c, u, _, k in results]
    
    return fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size

def visualize_profile(df: pd.DataFrame, max_combination_size: int = 2, max_lhs_size: int = 2):
    """
    Create a visual representation of the key profile for a dataframe.
    
    Parameters:
    - df: pandas.DataFrame to analyze.
    - max_combination_size: max size of column combos to test for keys.
    - max_lhs_size: max size of LHS in discovered FDs.
    
    Returns:
    - QMainWindow: The visualization window
    """
    # Get profile results
    fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size = profile(
        df, max_combination_size, max_lhs_size
    )
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Table Profile: Keys & Dependencies")
    window.resize(900, 700)
    
    # Create central widget and layout
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    
    # Add header
    header = QLabel(f"Analyzed {n_rows} rows × {len(cols)} columns; key combos up to size {max_combination_size}, FDs up to LHS size {max_lhs_size}")
    header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    header.setStyleSheet("font-size: 14pt; font-weight: bold; margin: 10px;")
    layout.addWidget(header)
    
    # Add description
    description = QLabel(
        "This profile helps identify candidate keys and functional dependencies in your data. "
        "Candidate keys are combinations of columns that uniquely identify rows. "
        "Functional dependencies indicate when one column's values determine another's."
    )
    description.setAlignment(Qt.AlignmentFlag.AlignCenter)
    description.setWordWrap(True)
    description.setStyleSheet("margin-bottom: 10px;")
    layout.addWidget(description)
    
    # Create tabs
    tabs = QTabWidget()
    
    # Tab for Candidate Keys
    key_tab = QWidget()
    key_layout = QVBoxLayout()
    
    key_header = QLabel("Candidate Keys (Column Combinations that Uniquely Identify Rows)")
    key_header.setStyleSheet("font-weight: bold;")
    key_layout.addWidget(key_header)
    
    key_table = QTableWidget(len(key_results), 4)
    key_table.setHorizontalHeaderLabels(["Columns", "Unique Count", "Uniqueness Ratio", "Candidate Key?"])
    key_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    for row, (cols_str, count, ratio, mark) in enumerate(key_results):
        key_table.setItem(row, 0, QTableWidgetItem(cols_str))
        key_table.setItem(row, 1, QTableWidgetItem(str(count)))
        key_table.setItem(row, 2, QTableWidgetItem(ratio))
        key_table.setItem(row, 3, QTableWidgetItem(mark))
    key_layout.addWidget(key_table)
    key_tab.setLayout(key_layout)
    tabs.addTab(key_tab, "Candidate Keys")
    
    # Tab for FDs
    fd_tab = QWidget()
    fd_layout = QVBoxLayout()
    
    fd_header = QLabel("Functional Dependencies (When Values in One Set of Columns Determine Another Column)")
    fd_header.setStyleSheet("font-weight: bold;")
    fd_layout.addWidget(fd_header)
    
    fd_table = QTableWidget(len(fd_results), 2)
    fd_table.setHorizontalHeaderLabels(["Determinant (LHS)", "Dependent (RHS)"])
    fd_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    for i, (lhs, rhs) in enumerate(fd_results):
        lhs_item = QTableWidgetItem(lhs)
        lhs_item.setFlags(lhs_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
        fd_table.setItem(i, 0, lhs_item)
        fd_table.setItem(i, 1, QTableWidgetItem(rhs))
    fd_layout.addWidget(fd_table)
    fd_tab.setLayout(fd_layout)
    tabs.addTab(fd_tab, "Functional Dependencies")
    
    layout.addWidget(tabs)
    
    # Show the window
    window.show()
    return window

def test_profile_keys():
    # Generate a dataframe with some realistic examples 
    df = pd.DataFrame({
                       "customer_id": [1, 2, 3, 4, 5],
                       "customer_name": ["John", "Jane", "John", "Jane", "John"],
                       "product_name": ["Apple", "Banana", "Apple", "Banana", "Apple"],
                       "product_group": ["Fruit", "Fruit", "Fruit", "Fruit", "Fruit"],
                       "order_date": ["2021-01-01", "2021-01-01", "2021-01-02", "2021-01-02", "2021-01-03"],
                       "order_amount": [100, 200, 150, 250, 120]})
    
    # Create and show visualization
    app = QApplication(sys.argv)
    window = visualize_profile(df, max_combination_size=2)
    sys.exit(app.exec())

# Only run the test function when script is executed directly
if __name__ == "__main__":
    test_profile_keys()