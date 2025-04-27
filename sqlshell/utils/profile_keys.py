import sys
import itertools
import pandas as pd
import random
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


def propose_normalized_tables(cols, candidate_keys, fds):
    """
    Propose a set of normalized tables based on functional dependencies.
    Uses a simplified approach to create 3NF tables.
    
    Parameters:
    - cols: list of all columns
    - candidate_keys: list of candidate keys
    - fds: list of functional dependencies as (lhs, rhs) tuples
    
    Returns:
    - List of proposed tables as (table_name, primary_key, attributes) tuples
    """
    # Start with a set of all attributes
    all_attrs = set(cols)
    proposed_tables = []
    
    # Group FDs by their determinants (LHS)
    determinant_groups = {}
    for lhs, rhs in fds:
        lhs_key = tuple(sorted(lhs))
        if lhs_key not in determinant_groups:
            determinant_groups[lhs_key] = []
        determinant_groups[lhs_key].append(rhs)
    
    # Create tables for each determinant group
    table_counter = 1
    for lhs, rhs_list in determinant_groups.items():
        table_attrs = set(lhs) | set(rhs_list)
        if table_attrs:  # Skip empty tables
            table_name = f"Table_{table_counter}"
            primary_key = ", ".join(lhs)
            attributes = list(table_attrs)
            proposed_tables.append((table_name, primary_key, attributes))
            table_counter += 1
    
    # Create a table for any remaining attributes not in any FD
    # or create a table with a candidate key if none exists yet
    used_attrs = set()
    for _, _, attrs in proposed_tables:
        used_attrs.update(attrs)
    
    remaining_attrs = all_attrs - used_attrs
    if remaining_attrs:
        # If we have a candidate key, use it for remaining attributes
        for key in candidate_keys:
            key_set = set(key)
            if key_set & remaining_attrs:  # If key has overlap with remaining attrs
                table_name = f"Table_{table_counter}"
                primary_key = ", ".join(key)
                attributes = list(remaining_attrs | key_set)
                proposed_tables.append((table_name, primary_key, attributes))
                break
        else:  # No suitable candidate key
            table_name = f"Table_{table_counter}"
            primary_key = "id (suggested)"
            attributes = list(remaining_attrs)
            proposed_tables.append((table_name, primary_key, attributes))
    
    return proposed_tables


def profile(df: pd.DataFrame, max_combination_size: int = 2, max_lhs_size: int = 2):
    """
    Analyze a pandas DataFrame to suggest candidate keys and discover functional dependencies.

    Parameters:
    - df: pandas.DataFrame to analyze.
    - max_combination_size: max size of column combos to test for keys.
    - max_lhs_size: max size of LHS in discovered FDs.
    
    Returns:
    - Tuple of (fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size, normalized_tables)
    """
    n_rows = len(df)
    cols = list(df.columns)

    # Discover functional dependencies
    fds = find_functional_dependencies(df, max_lhs_size)

    # Prepare FD results
    fd_results = [(", ".join(lhs), rhs) for lhs, rhs in fds]

    # Profile keys (by uniqueness)
    all_keys = []
    for size in range(1, max_combination_size + 1):
        for combo in itertools.combinations(cols, size):
            unique_count = df.drop_duplicates(subset=combo).shape[0]
            unique_ratio = unique_count / n_rows
            is_key = unique_count == n_rows
            if is_key:
                all_keys.append(combo)
    
    # Distinguish between candidate keys and superkeys
    candidate_keys = []
    superkeys = []
    
    for key in all_keys:
        is_candidate = True
        # Check if any proper subset of this key is also a key
        for i in range(1, len(key)):
            for subset in itertools.combinations(key, i):
                if subset in all_keys:
                    is_candidate = False
                    break
            if not is_candidate:
                break
        
        if is_candidate:
            candidate_keys.append(key)
        else:
            superkeys.append(key)
    
    # Prepare results for all keys (both candidate keys and superkeys)
    results = []
    for size in range(1, max_combination_size + 1):
        for combo in itertools.combinations(cols, size):
            unique_count = df.drop_duplicates(subset=combo).shape[0]
            unique_ratio = unique_count / n_rows
            is_key = combo in all_keys
            is_candidate = combo in candidate_keys
            is_superkey = combo in superkeys
            
            # Use icons for different key types
            key_type = ""
            if is_candidate:
                key_type = "★ Candidate Key"  # Star for candidate keys
            elif is_superkey:
                key_type = "⊃ Superkey"       # Superset symbol for superkeys
            
            results.append((combo, unique_count, unique_ratio, is_key, key_type))
    
    results.sort(key=lambda x: (not x[3], -x[2], len(x[0])))
    key_results = [(", ".join(c), u, f"{u/n_rows:.2%}", k) 
                   for c, u, _, _, k in results]
    
    # Propose normalized tables
    normalized_tables = propose_normalized_tables(cols, candidate_keys, fds)
    
    return fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size, normalized_tables


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
    fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size, normalized_tables = profile(
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
        "★ Candidate keys are minimal combinations of columns that uniquely identify rows. "
        "⊃ Superkeys are non-minimal column sets that uniquely identify rows. "
        "Functional dependencies indicate when one column's values determine another's."
    )
    description.setAlignment(Qt.AlignmentFlag.AlignCenter)
    description.setWordWrap(True)
    description.setStyleSheet("margin-bottom: 10px;")
    layout.addWidget(description)
    
    # Add key for icons
    icons_key = QLabel("Key: ★ = Minimal Candidate Key | ⊃ = Non-minimal Superkey")
    icons_key.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icons_key.setStyleSheet("font-style: italic; margin-bottom: 15px;")
    layout.addWidget(icons_key)
    
    # Create tabs
    tabs = QTabWidget()
    
    # Tab for Candidate Keys
    key_tab = QWidget()
    key_layout = QVBoxLayout()
    
    key_header = QLabel("Keys (Column Combinations that Uniquely Identify Rows)")
    key_header.setStyleSheet("font-weight: bold;")
    key_layout.addWidget(key_header)
    
    key_table = QTableWidget(len(key_results), 4)
    key_table.setHorizontalHeaderLabels(["Columns", "Unique Count", "Uniqueness Ratio", "Key Type"])
    key_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    for row, (cols_str, count, ratio, key_type) in enumerate(key_results):
        key_table.setItem(row, 0, QTableWidgetItem(cols_str))
        key_table.setItem(row, 1, QTableWidgetItem(str(count)))
        key_table.setItem(row, 2, QTableWidgetItem(ratio))
        
        # Create item with appropriate styling
        type_item = QTableWidgetItem(key_type)
        if "Candidate Key" in key_type:
            type_item.setForeground(Qt.GlobalColor.darkGreen)
        elif "Superkey" in key_type:
            type_item.setForeground(Qt.GlobalColor.darkBlue)
        key_table.setItem(row, 3, type_item)
        
    key_layout.addWidget(key_table)
    key_tab.setLayout(key_layout)
    tabs.addTab(key_tab, "Keys")
    
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
    
    # Tab for Normalized Tables
    norm_tab = QWidget()
    norm_layout = QVBoxLayout()
    
    norm_header = QLabel("Proposed Normalized Tables (Based on Functional Dependencies)")
    norm_header.setStyleSheet("font-weight: bold;")
    norm_layout.addWidget(norm_header)
    
    norm_description = QLabel(
        "These tables represent a proposed normalized schema based on the discovered functional dependencies. "
        "Each table includes attributes that are functionally dependent on its primary key. "
        "This is an approximate 3NF decomposition and may need further refinement."
    )
    norm_description.setWordWrap(True)
    norm_description.setStyleSheet("margin-bottom: 10px;")
    norm_layout.addWidget(norm_description)
    
    norm_table = QTableWidget(len(normalized_tables), 3)
    norm_table.setHorizontalHeaderLabels(["Table Name", "Primary Key", "Attributes"])
    norm_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    for i, (table_name, primary_key, attributes) in enumerate(normalized_tables):
        norm_table.setItem(i, 0, QTableWidgetItem(table_name))
        
        pk_item = QTableWidgetItem(primary_key)
        pk_item.setForeground(Qt.GlobalColor.darkGreen)
        norm_table.setItem(i, 1, pk_item)
        
        norm_table.setItem(i, 2, QTableWidgetItem(", ".join(attributes)))
    
    norm_layout.addWidget(norm_table)
    norm_tab.setLayout(norm_layout)
    tabs.addTab(norm_tab, "Normalized Tables")
    
    layout.addWidget(tabs)
    
    # Show the window
    window.show()
    return window


def test_profile_keys(test_size=100):
    # Generate a dataframe with some realistic examples of a customer-product-order relationship
    # Create customer data
    customer_ids = list(range(1, 21))  # 20 customers
    customer_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Edward", "Fiona", "George", "Hannah"]
    
    # Create product data
    product_names = ["Apple", "Banana", "Orange", "Grape", "Mango", "Strawberry", "Blueberry", "Kiwi", "Pineapple", "Watermelon"]
    product_groups = ["Fruit"] * len(product_names)
    
    # Generate random orders
    random.seed(42)  # For reproducibility
    df_data = {
        "customer_id": [random.choice(customer_ids) for _ in range(test_size)],
        "customer_name": [customer_names[i % len(customer_names)] for i in range(test_size)],
        "product_name": [random.choice(product_names) for _ in range(test_size)],
        "product_group": ["Fruit" for _ in range(test_size)],
        "order_date": [pd.Timestamp("2021-01-01") + pd.Timedelta(days=random.randint(0, 30)) for _ in range(test_size)],
        "order_amount": [random.randint(100, 1000) for _ in range(test_size)]
    }
    
    # Ensure consistent relationships
    for i in range(test_size):
        # Ensure customer_name is consistently associated with customer_id
        customer_idx = df_data["customer_id"][i] % len(customer_names)
        df_data["customer_name"][i] = customer_names[customer_idx]
    
    df = pd.DataFrame(df_data)
    
    # Create and show visualization
    app = QApplication(sys.argv)
    window = visualize_profile(df, max_combination_size=3, max_lhs_size=2)
    sys.exit(app.exec())

# Only run the test function when script is executed directly
if __name__ == "__main__":
    test_profile_keys()