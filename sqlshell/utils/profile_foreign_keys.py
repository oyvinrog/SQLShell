import sys
import itertools
import pandas as pd
from typing import List, Dict, Tuple, Set, Callable
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QMainWindow,
    QPushButton, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt


def find_foreign_keys(dfs: List[pd.DataFrame], df_names: List[str], min_match_ratio: float = 0.95):
    """
    Discover potential foreign key relationships between DataFrames.
    
    Parameters:
    - dfs: List of pandas DataFrames to analyze
    - df_names: Names of the DataFrames (used for reporting)
    - min_match_ratio: Minimum ratio of matching values to consider a foreign key
    
    Returns:
    - List of tuples (referenced_table, referenced_column, referencing_table, referencing_column, match_ratio)
    """
    foreign_keys = []
    
    # First, identify potential primary keys in each DataFrame
    pk_candidates = {}
    for i, df in enumerate(dfs):
        name = df_names[i]
        # Consider columns with unique values as potential primary keys
        for col in df.columns:
            if df[col].nunique() == len(df) and not df[col].isna().any():
                if name not in pk_candidates:
                    pk_candidates[name] = []
                pk_candidates[name].append(col)
    
    # For each DataFrame pair, check for foreign key relationships
    for i, df1 in enumerate(dfs):
        name1 = df_names[i]
        
        # Skip if this DataFrame has no primary key candidates
        if name1 not in pk_candidates:
            continue
        
        # For each potential primary key column
        for pk_col in pk_candidates[name1]:
            pk_values = set(df1[pk_col])
            
            # Check every other DataFrame for matching columns
            for j, df2 in enumerate(dfs):
                name2 = df_names[j]
                
                # Skip self-references
                if i == j:
                    continue
                
                # Check each column in df2 for potential foreign key relationship
                for fk_col in df2.columns:
                    # Skip if data types are incompatible
                    if df1[pk_col].dtype != df2[fk_col].dtype:
                        continue
                    
                    # Get unique values in potential foreign key column
                    fk_values = set(df2[fk_col].dropna())
                    
                    # Skip empty columns
                    if not fk_values:
                        continue
                    
                    # Check if foreign key values are a subset of primary key values
                    common_values = fk_values.intersection(pk_values)
                    match_ratio = len(common_values) / len(fk_values)
                    
                    # Consider it a foreign key if match ratio exceeds threshold
                    if match_ratio >= min_match_ratio:
                        foreign_keys.append((name1, pk_col, name2, fk_col, match_ratio))
    
    # Sort by match ratio (descending)
    foreign_keys.sort(key=lambda x: x[4], reverse=True)
    return foreign_keys


def find_inclusion_dependencies(dfs: List[pd.DataFrame], df_names: List[str], min_match_ratio: float = 0.8):
    """
    Find inclusion dependencies (more general than foreign keys) between DataFrames.
    An inclusion dependency exists when values in one column are a subset of values in another column.
    
    Parameters:
    - dfs: List of pandas DataFrames to analyze
    - df_names: Names of the DataFrames
    - min_match_ratio: Minimum ratio of matching values
    
    Returns:
    - List of tuples (referenced_table, referenced_column, referencing_table, referencing_column, match_ratio)
    """
    dependencies = []
    
    # For each pair of DataFrames
    for i, df1 in enumerate(dfs):
        name1 = df_names[i]
        
        for j, df2 in enumerate(dfs):
            name2 = df_names[j]
            
            # Skip self-comparison for the same index
            if i == j:
                continue
            
            # For each potential pair of columns
            for col1 in df1.columns:
                # Get unique values in the potential referenced column
                values1 = set(df1[col1].dropna())
                
                # Skip empty columns
                if not values1:
                    continue
                
                for col2 in df2.columns:
                    # Skip if data types are incompatible
                    if df1[col1].dtype != df2[col2].dtype:
                        continue
                    
                    # Get unique values in the potential referencing column
                    values2 = set(df2[col2].dropna())
                    
                    # Skip empty columns
                    if not values2:
                        continue
                    
                    # Check if values2 is approximately a subset of values1
                    common_values = values2.intersection(values1)
                    match_ratio = len(common_values) / len(values2)
                    
                    # Consider it an inclusion dependency if match ratio exceeds threshold
                    if match_ratio >= min_match_ratio:
                        dependencies.append((name1, col1, name2, col2, match_ratio))
    
    # Sort by match ratio (descending)
    dependencies.sort(key=lambda x: x[4], reverse=True)
    return dependencies


def profile_referential_integrity(dfs: List[pd.DataFrame], df_names: List[str], foreign_keys):
    """
    Profile the referential integrity of discovered foreign keys.
    
    Parameters:
    - dfs: List of pandas DataFrames
    - df_names: Names of the DataFrames
    - foreign_keys: List of foreign key relationships
    
    Returns:
    - Dictionary with referential integrity statistics
    """
    integrity_results = {}
    
    # Create lookup for DataFrames by name
    df_dict = {name: df for name, df in zip(df_names, dfs)}
    
    for pk_table, pk_col, fk_table, fk_col, _ in foreign_keys:
        pk_df = df_dict[pk_table]
        fk_df = df_dict[fk_table]
        
        # Get primary key values
        pk_values = set(pk_df[pk_col])
        
        # Get foreign key values
        fk_values = set(fk_df[fk_col].dropna())
        
        # Count values that violate referential integrity
        violations = fk_values - pk_values
        violation_count = len(violations)
        
        # Calculate violation ratio
        total_fk_values = len(fk_df[fk_col].dropna())
        violation_ratio = violation_count / total_fk_values if total_fk_values > 0 else 0
        
        # Record results
        key = (pk_table, pk_col, fk_table, fk_col)
        integrity_results[key] = {
            'violation_count': violation_count,
            'violation_ratio': violation_ratio,
            'total_fk_values': total_fk_values,
            'violations': list(violations)[:10]  # Only store first 10 violations for display
        }
    
    return integrity_results


def profile_foreign_keys(dfs: List[pd.DataFrame], df_names: List[str] = None, min_match_ratio: float = 0.95):
    """
    Analyze a list of pandas DataFrames to discover foreign key relationships.

    Parameters:
    - dfs: List of pandas DataFrames to analyze
    - df_names: Optional list of names for the DataFrames. If None, names will be generated.
    - min_match_ratio: Minimum ratio of matching values to consider a foreign key
    
    Returns:
    - Tuple of (foreign_keys, inclusion_dependencies, integrity_results)
    """
    # Generate default names if not provided
    if df_names is None:
        df_names = [f"Table_{i+1}" for i in range(len(dfs))]
    
    # Ensure we have the same number of names as DataFrames
    assert len(dfs) == len(df_names), "Number of DataFrames must match number of names"
    
    # Find foreign keys
    foreign_keys = find_foreign_keys(dfs, df_names, min_match_ratio)
    
    # Find more general inclusion dependencies
    inclusion_dependencies = find_inclusion_dependencies(dfs, df_names, min_match_ratio * 0.8)
    
    # Profile referential integrity
    integrity_results = profile_referential_integrity(dfs, df_names, foreign_keys)
    
    return foreign_keys, inclusion_dependencies, integrity_results


def visualize_foreign_keys(dfs: List[pd.DataFrame], df_names: List[str] = None, min_match_ratio: float = 0.95, 
                          on_generate_join: Callable = None, parent=None):
    """
    Create a visual representation of foreign key relationships between DataFrames.
    
    Parameters:
    - dfs: List of pandas DataFrames to analyze
    - df_names: Optional list of names for the DataFrames. If None, names will be generated.
    - min_match_ratio: Minimum ratio of matching values to consider a foreign key
    - on_generate_join: Callback function that will be called when the Generate JOIN button is clicked.
                        It receives a JOIN query string as its argument.
    - parent: Parent widget for the QMainWindow. Typically the main application window.
    
    Returns:
    - QMainWindow: The visualization window
    """
    # Generate default names if not provided
    if df_names is None:
        df_names = [f"Table_{i+1}" for i in range(len(dfs))]
    
    # Get profile results
    foreign_keys, inclusion_dependencies, integrity_results = profile_foreign_keys(
        dfs, df_names, min_match_ratio
    )
    
    # Create main window
    window = QMainWindow(parent)
    window.setWindowTitle("Foreign Key Analysis")
    window.resize(900, 700)
    
    # Create central widget and layout
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    
    # Add header
    header = QLabel(f"Analyzed {len(dfs)} tables with potential foreign key relationships")
    header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    header.setStyleSheet("font-size: 14pt; font-weight: bold; margin: 10px;")
    layout.addWidget(header)
    
    # Add description
    description = QLabel(
        "This analysis helps identify potential foreign key relationships between tables. "
        "Foreign keys are columns in one table that reference the primary key of another table. "
        "The match ratio indicates how many values in the foreign key column exist in the referenced column."
    )
    description.setAlignment(Qt.AlignmentFlag.AlignCenter)
    description.setWordWrap(True)
    description.setStyleSheet("margin-bottom: 10px;")
    layout.addWidget(description)
    
    # Create tabs
    tabs = QTabWidget()
    
    # Define the "Add to editor" function to handle JOIN queries
    def handle_join_query(query):
        if on_generate_join:
            on_generate_join(query)
            QMessageBox.information(window, "JOIN Query Generated", 
                                   f"The following query has been added to the editor:\n\n{query}")
    
    # Tab for Foreign Keys
    fk_tab = QWidget()
    fk_layout = QVBoxLayout()
    
    fk_header = QLabel("Potential Foreign Key Relationships")
    fk_header.setStyleSheet("font-weight: bold;")
    fk_layout.addWidget(fk_header)
    
    fk_table = QTableWidget(len(foreign_keys), 6)  # Added column for Generate JOIN button
    fk_table.setHorizontalHeaderLabels([
        "Referenced Table", "Referenced Column", "Referencing Table", "Referencing Column", "Match Ratio", "Action"
    ])
    fk_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    
    # Set minimum width for the Action column
    fk_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
    fk_table.setColumnWidth(5, 140)  # Set a fixed width for action column
    
    for row, (pk_table, pk_col, fk_table_name, fk_col, match_ratio) in enumerate(foreign_keys):
        fk_table.setItem(row, 0, QTableWidgetItem(pk_table))
        fk_table.setItem(row, 1, QTableWidgetItem(pk_col))
        fk_table.setItem(row, 2, QTableWidgetItem(fk_table_name))
        fk_table.setItem(row, 3, QTableWidgetItem(fk_col))
        
        # Format match ratio with color coding
        ratio_item = QTableWidgetItem(f"{match_ratio:.2%}")
        if match_ratio >= 0.99:
            ratio_item.setForeground(Qt.GlobalColor.darkGreen)
        elif match_ratio >= 0.9:
            ratio_item.setForeground(Qt.GlobalColor.darkBlue)
        else:
            ratio_item.setForeground(Qt.GlobalColor.darkYellow)
        fk_table.setItem(row, 4, ratio_item)
        
        # Add Generate JOIN hyperlink - optimized for better visibility
        if on_generate_join is not None:
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.setContentsMargins(0, 0, 0, 0)  # Minimal margins
            button_layout.setSpacing(0)  # No spacing
            
            # Create a styled hyperlink label
            join_link = QLabel("<a href='#' style='color: #3498DB; font-weight: bold;'>Generate JOIN</a>")
            join_link.setTextFormat(Qt.TextFormat.RichText)
            join_link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            join_link.setCursor(Qt.CursorShape.PointingHandCursor)
            join_link.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the text
            join_query = f"SELECT * FROM {fk_table_name} JOIN {pk_table} ON {fk_table_name}.{fk_col} = {pk_table}.{pk_col}"
            
            # Connect linkActivated signal to handle the JOIN query
            join_link.linkActivated.connect(lambda link, q=join_query: handle_join_query(q))
            
            button_layout.addWidget(join_link)
            fk_table.setCellWidget(row, 5, button_widget)
        
    fk_layout.addWidget(fk_table)
    fk_tab.setLayout(fk_layout)
    tabs.addTab(fk_tab, "Foreign Keys")
    
    # Tab for Inclusion Dependencies
    id_tab = QWidget()
    id_layout = QVBoxLayout()
    
    id_header = QLabel("Inclusion Dependencies (Values in one column are a subset of another)")
    id_header.setStyleSheet("font-weight: bold;")
    id_layout.addWidget(id_header)
    
    id_table = QTableWidget(len(inclusion_dependencies), 6)  # Added column for Generate JOIN button
    id_table.setHorizontalHeaderLabels([
        "Referenced Table", "Referenced Column", "Referencing Table", "Referencing Column", "Match Ratio", "Action"
    ])
    id_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    
    # Set minimum width for the Action column
    id_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
    id_table.setColumnWidth(5, 140)  # Set a fixed width for action column
    
    for row, (table1, col1, table2, col2, match_ratio) in enumerate(inclusion_dependencies):
        id_table.setItem(row, 0, QTableWidgetItem(table1))
        id_table.setItem(row, 1, QTableWidgetItem(col1))
        id_table.setItem(row, 2, QTableWidgetItem(table2))
        id_table.setItem(row, 3, QTableWidgetItem(col2))
        
        # Format match ratio with color coding
        ratio_item = QTableWidgetItem(f"{match_ratio:.2%}")
        if match_ratio >= 0.95:
            ratio_item.setForeground(Qt.GlobalColor.darkGreen)
        elif match_ratio >= 0.8:
            ratio_item.setForeground(Qt.GlobalColor.darkBlue)
        else:
            ratio_item.setForeground(Qt.GlobalColor.darkYellow)
        id_table.setItem(row, 4, ratio_item)
        
        # Add Generate JOIN hyperlink - optimized for better visibility
        if on_generate_join is not None:
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.setContentsMargins(0, 0, 0, 0)  # Minimal margins
            button_layout.setSpacing(0)  # No spacing
            
            # Create a styled hyperlink label
            join_link = QLabel("<a href='#' style='color: #3498DB; font-weight: bold;'>Generate JOIN</a>")
            join_link.setTextFormat(Qt.TextFormat.RichText)
            join_link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            join_link.setCursor(Qt.CursorShape.PointingHandCursor)
            join_link.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the text
            join_query = f"SELECT * FROM {table2} JOIN {table1} ON {table2}.{col2} = {table1}.{col1}"
            
            # Connect linkActivated signal to handle the JOIN query
            join_link.linkActivated.connect(lambda link, q=join_query: handle_join_query(q))
            
            button_layout.addWidget(join_link)
            id_table.setCellWidget(row, 5, button_widget)
        
    id_layout.addWidget(id_table)
    id_tab.setLayout(id_layout)
    tabs.addTab(id_tab, "Inclusion Dependencies")
    
    # Tab for Referential Integrity
    ri_tab = QWidget()
    ri_layout = QVBoxLayout()
    
    ri_header = QLabel("Referential Integrity Analysis")
    ri_header.setStyleSheet("font-weight: bold;")
    ri_layout.addWidget(ri_header)
    
    ri_description = QLabel(
        "This table shows referential integrity violations for discovered foreign keys. "
        "A violation occurs when a value in the foreign key column doesn't exist in the referenced column."
    )
    ri_description.setWordWrap(True)
    ri_layout.addWidget(ri_description)
    
    # Create table for referential integrity
    ri_table = QTableWidget(len(integrity_results), 6)  # Added column for Generate JOIN button
    ri_table.setHorizontalHeaderLabels([
        "Relationship", "Violations", "Total FK Values", "Violation %", "Example Violations", "Action"
    ])
    ri_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    
    # Set minimum width for the Action column
    ri_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
    ri_table.setColumnWidth(5, 140)  # Set a fixed width for action column
    
    row = 0
    for key, stats in integrity_results.items():
        pk_table, pk_col, fk_table, fk_col = key
        relationship = f"{fk_table}.{fk_col} → {pk_table}.{pk_col}"
        
        ri_table.setItem(row, 0, QTableWidgetItem(relationship))
        ri_table.setItem(row, 1, QTableWidgetItem(str(stats['violation_count'])))
        ri_table.setItem(row, 2, QTableWidgetItem(str(stats['total_fk_values'])))
        
        # Format violation ratio with color coding
        ratio_item = QTableWidgetItem(f"{stats['violation_ratio']:.2%}")
        if stats['violation_ratio'] == 0:
            ratio_item.setForeground(Qt.GlobalColor.darkGreen)
        elif stats['violation_ratio'] < 0.01:
            ratio_item.setForeground(Qt.GlobalColor.darkBlue)
        else:
            ratio_item.setForeground(Qt.GlobalColor.darkRed)
        ri_table.setItem(row, 3, ratio_item)
        
        # Show example violations
        examples = ', '.join([str(v) for v in stats['violations']])
        if stats['violation_count'] > len(stats['violations']):
            examples += f" (and {stats['violation_count'] - len(stats['violations'])} more)"
        ri_table.setItem(row, 4, QTableWidgetItem(examples))
        
        # Add Generate JOIN hyperlink - optimized for better visibility
        if on_generate_join is not None:
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.setContentsMargins(0, 0, 0, 0)  # Minimal margins
            button_layout.setSpacing(0)  # No spacing
            
            # Create a styled hyperlink label
            join_link = QLabel("<a href='#' style='color: #3498DB; font-weight: bold;'>Generate JOIN</a>")
            join_link.setTextFormat(Qt.TextFormat.RichText)
            join_link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            join_link.setCursor(Qt.CursorShape.PointingHandCursor)
            join_link.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the text
            join_query = f"SELECT * FROM {fk_table} LEFT JOIN {pk_table} ON {fk_table}.{fk_col} = {pk_table}.{pk_col}"
            
            # Connect linkActivated signal to handle the JOIN query
            join_link.linkActivated.connect(lambda link, q=join_query: handle_join_query(q))
            
            button_layout.addWidget(join_link)
            ri_table.setCellWidget(row, 5, button_widget)
        
        row += 1
        
    ri_layout.addWidget(ri_table)
    ri_tab.setLayout(ri_layout)
    tabs.addTab(ri_tab, "Referential Integrity")
    
    layout.addWidget(tabs)
    
    # Show the window
    window.show()
    return window


def test_profile_foreign_keys():
    """
    Test function to demonstrate foreign key detection with sample data.
    """
    # Create test data with clear foreign key relationships
    
    # Customers table
    customers_data = {
        "customer_id": list(range(1, 21)),
        "customer_name": ["Customer " + str(i) for i in range(1, 21)],
        "city": ["City " + str(i % 5) for i in range(1, 21)]
    }
    customers_df = pd.DataFrame(customers_data)
    
    # Products table
    products_data = {
        "product_id": list(range(101, 111)),
        "product_name": ["Product " + str(i) for i in range(101, 111)],
        "category": ["Category " + str(i % 3) for i in range(101, 111)]
    }
    products_df = pd.DataFrame(products_data)
    
    # Orders table (with foreign keys to customers and products)
    import random
    random.seed(42)
    
    orders_data = {
        "order_id": list(range(1001, 1101)),
        "customer_id": [random.randint(1, 20) for _ in range(100)],
        "order_date": [pd.Timestamp("2021-01-01") + pd.Timedelta(days=i) for i in range(100)]
    }
    orders_df = pd.DataFrame(orders_data)
    
    # Order details table (with foreign keys to orders and products)
    order_details_data = {
        "order_detail_id": list(range(10001, 10201)),
        "order_id": [random.choice(orders_data["order_id"]) for _ in range(200)],
        "product_id": [random.choice(products_data["product_id"]) for _ in range(200)],
        "quantity": [random.randint(1, 10) for _ in range(200)]
    }
    order_details_df = pd.DataFrame(order_details_data)
    
    # Add some referential integrity violations
    # Add some non-existent customer IDs
    orders_df.loc[95:99, "customer_id"] = [25, 26, 27, 28, 29]
    
    # Define a callback function to handle JOIN generation
    def handle_join_query(query):
        print(f"Generated JOIN query: {query}")
        # In a real application, this would insert the query into the query editor
    
    # Create and show visualization
    dfs = [customers_df, products_df, orders_df, order_details_df]
    df_names = ["Customers", "Products", "Orders", "OrderDetails"]
    
    app = QApplication(sys.argv)
    window = visualize_foreign_keys(dfs, df_names, min_match_ratio=0.9, on_generate_join=handle_join_query)
    sys.exit(app.exec())

# Only run the test function when script is executed directly
if __name__ == "__main__":
    test_profile_foreign_keys() 