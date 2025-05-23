"""Export functionality for SQLShell application."""

import os
import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Any

class ExportManager:
    """Manages data export functionality for SQLShell."""
    
    def __init__(self, db_manager):
        """Initialize the export manager.
        
        Args:
            db_manager: The database manager instance to use for table registration
        """
        self.db_manager = db_manager
    
    def export_to_excel(self, df: pd.DataFrame, file_name: str) -> Tuple[str, Dict[str, Any]]:
        """Export data to Excel format.
        
        Args:
            df: The DataFrame to export
            file_name: The target file path
            
        Returns:
            Tuple containing:
            - The generated table name
            - Dictionary with export metadata
        """
        try:
            # Export to Excel
            df.to_excel(file_name, index=False)
            
            # Generate table name from file name
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            table_name = self.db_manager.sanitize_table_name(base_name)
            
            # Ensure unique table name
            original_name = table_name
            counter = 1
            while table_name in self.db_manager.loaded_tables:
                table_name = f"{original_name}_{counter}"
                counter += 1
            
            # Register the table in the database manager
            self.db_manager.register_dataframe(df, table_name, file_name)
            
            # Update tracking
            self.db_manager.loaded_tables[table_name] = file_name
            self.db_manager.table_columns[table_name] = df.columns.tolist()
            
            return table_name, {
                'file_path': file_name,
                'columns': df.columns.tolist(),
                'row_count': len(df)
            }
            
        except Exception as e:
            raise Exception(f"Failed to export to Excel: {str(e)}")
    
    def export_to_parquet(self, df: pd.DataFrame, file_name: str) -> Tuple[str, Dict[str, Any]]:
        """Export data to Parquet format.
        
        Args:
            df: The DataFrame to export
            file_name: The target file path
            
        Returns:
            Tuple containing:
            - The generated table name
            - Dictionary with export metadata
        """
        try:
            # Export to Parquet
            df.to_parquet(file_name, index=False)
            
            # Generate table name from file name
            base_name = os.path.splitext(os.path.basename(file_name))[0]
            table_name = self.db_manager.sanitize_table_name(base_name)
            
            # Ensure unique table name
            original_name = table_name
            counter = 1
            while table_name in self.db_manager.loaded_tables:
                table_name = f"{original_name}_{counter}"
                counter += 1
            
            # Register the table in the database manager
            self.db_manager.register_dataframe(df, table_name, file_name)
            
            # Update tracking
            self.db_manager.loaded_tables[table_name] = file_name
            self.db_manager.table_columns[table_name] = df.columns.tolist()
            
            return table_name, {
                'file_path': file_name,
                'columns': df.columns.tolist(),
                'row_count': len(df)
            }
            
        except Exception as e:
            raise Exception(f"Failed to export to Parquet: {str(e)}")
    
    def convert_table_to_dataframe(self, table_widget) -> Optional[pd.DataFrame]:
        """Convert a QTableWidget to a pandas DataFrame with proper data types.
        
        Args:
            table_widget: The QTableWidget containing the data
            
        Returns:
            DataFrame with properly typed data, or None if conversion fails
        """
        if not table_widget or table_widget.rowCount() == 0:
            return None
            
        # Get headers
        headers = [table_widget.horizontalHeaderItem(i).text() 
                  for i in range(table_widget.columnCount())]
        
        # Get data
        data = []
        for row in range(table_widget.rowCount()):
            row_data = []
            for column in range(table_widget.columnCount()):
                item = table_widget.item(row, column)
                row_data.append(item.text() if item else '')
            data.append(row_data)
        
        # Create DataFrame from raw string data
        df_raw = pd.DataFrame(data, columns=headers)
        
        # Try to use the original dataframe's dtypes if available
        if hasattr(table_widget, 'current_df') and table_widget.current_df is not None:
            original_df = table_widget.current_df
            
            # Create a new DataFrame with appropriate types
            df_typed = pd.DataFrame()
            
            for col in df_raw.columns:
                if col in original_df.columns:
                    # Get the original column type
                    orig_type = original_df[col].dtype
                    
                    # Special handling for different data types
                    if pd.api.types.is_numeric_dtype(orig_type):
                        try:
                            numeric_col = pd.to_numeric(
                                df_raw[col].str.replace(',', '').replace('NULL', np.nan)
                            )
                            df_typed[col] = numeric_col
                        except:
                            df_typed[col] = df_raw[col]
                    elif pd.api.types.is_datetime64_dtype(orig_type):
                        try:
                            df_typed[col] = pd.to_datetime(df_raw[col].replace('NULL', np.nan))
                        except:
                            df_typed[col] = df_raw[col]
                    elif pd.api.types.is_bool_dtype(orig_type):
                        try:
                            df_typed[col] = df_raw[col].map({'True': True, 'False': False}).replace('NULL', np.nan)
                        except:
                            df_typed[col] = df_raw[col]
                    else:
                        df_typed[col] = df_raw[col]
                else:
                    df_typed[col] = df_raw[col]
                    
            return df_typed
            
        else:
            # If we don't have the original dataframe, try to infer types
            df_raw.replace('NULL', np.nan, inplace=True)
            
            for col in df_raw.columns:
                try:
                    df_raw[col] = pd.to_numeric(df_raw[col].str.replace(',', ''))
                except:
                    try:
                        df_raw[col] = pd.to_datetime(df_raw[col])
                    except:
                        try:
                            if df_raw[col].dropna().isin(['True', 'False']).all():
                                df_raw[col] = df_raw[col].map({'True': True, 'False': False})
                        except:
                            pass
            
            return df_raw 