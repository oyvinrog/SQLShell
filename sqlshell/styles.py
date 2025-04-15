def get_application_stylesheet(colors):
    """Generate the application's stylesheet using the provided color scheme.
    
    Args:
        colors: A dictionary containing color definitions for the application
        
    Returns:
        A string containing the complete Qt stylesheet
    """
    return f"""
        QMainWindow {{
            background-color: {colors['background']};
        }}
        
        QWidget {{
            color: {colors['text']};
            font-family: 'Segoe UI', 'Arial', sans-serif;
        }}
        
        QLabel {{
            font-size: 13px;
            padding: 2px;
        }}
        
        QLabel#header_label {{
            font-size: 16px;
            font-weight: bold;
            color: {colors['primary']};
            padding: 8px 0;
        }}
        
        QPushButton {{
            background-color: {colors['secondary']};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 13px;
            min-height: 30px;
        }}
        
        QPushButton:hover {{
            background-color: #2980B9;
        }}
        
        QPushButton:pressed {{
            background-color: #1F618D;
        }}
        
        QPushButton#primary_button {{
            background-color: {colors['accent']};
        }}
        
        QPushButton#primary_button:hover {{
            background-color: #16A085;
        }}
        
        QPushButton#primary_button:pressed {{
            background-color: #0E6655;
        }}
        
        QPushButton#danger_button {{
            background-color: {colors['error']};
        }}
        
        QPushButton#danger_button:hover {{
            background-color: #CB4335;
        }}
        
        QToolButton {{
            background-color: transparent;
            border: none;
            border-radius: 4px;
            padding: 4px;
        }}
        
        QToolButton:hover {{
            background-color: rgba(52, 152, 219, 0.2);
        }}
        
        QFrame#sidebar {{
            background-color: {colors['primary']};
            border-radius: 0px;
        }}
        
        QFrame#content_panel {{
            background-color: white;
            border-radius: 8px;
            border: 1px solid {colors['border']};
        }}
        
        QListWidget {{
            background-color: white;
            border-radius: 4px;
            border: 1px solid {colors['border']};
            padding: 4px;
            outline: none;
        }}
        
        QListWidget::item {{
            padding: 8px;
            border-radius: 4px;
        }}
        
        QListWidget::item:selected {{
            background-color: {colors['secondary']};
            color: white;
        }}
        
        QListWidget::item:hover:!selected {{
            background-color: #E3F2FD;
        }}
        
        QTableWidget {{
            background-color: white;
            alternate-background-color: #F8F9FA;
            border-radius: 4px;
            border: 1px solid {colors['border']};
            gridline-color: #E0E0E0;
            outline: none;
        }}
        
        QTableWidget::item {{
            padding: 4px;
        }}
        
        QTableWidget::item:selected {{
            background-color: rgba(52, 152, 219, 0.2);
            color: {colors['text']};
        }}
        
        QHeaderView::section {{
            background-color: {colors['primary']};
            color: white;
            padding: 8px;
            border: none;
            font-weight: bold;
        }}
        
        QSplitter::handle {{
            background-color: {colors['border']};
        }}
        
        QStatusBar {{
            background-color: {colors['primary']};
            color: white;
            padding: 8px;
        }}
        
        QTabWidget::pane {{
            border: 1px solid {colors['border']};
            border-radius: 4px;
            top: -1px;
            background-color: white;
        }}
        
        QTabBar::tab {{
            background-color: {colors['light_bg']};
            color: {colors['text']};
            border: 1px solid {colors['border']};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 8px 12px;
            margin-right: 2px;
            min-width: 80px;
        }}
        
        QTabBar::tab:selected {{
            background-color: white;
            border-bottom: 1px solid white;
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: #E3F2FD;
        }}
        
        QTabBar::close-button {{
            image: url(close.png);
            subcontrol-position: right;
        }}
        
        QTabBar::close-button:hover {{
            background-color: rgba(255, 0, 0, 0.2);
            border-radius: 2px;
        }}
        
        QPlainTextEdit, QTextEdit {{
            background-color: white;
            border-radius: 4px;
            border: 1px solid {colors['border']};
            padding: 8px;
            selection-background-color: #BBDEFB;
            selection-color: {colors['text']};
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 14px;
        }}
    """

def get_tab_corner_stylesheet():
    """Get the stylesheet for the tab corner widget with the + button"""
    return """
        QToolButton {
            background-color: transparent;
            border: none;
            border-radius: 4px;
            padding: 4px;
            font-weight: bold;
            font-size: 16px;
            color: #3498DB;
        }
        QToolButton:hover {
            background-color: rgba(52, 152, 219, 0.2);
        }
        QToolButton:pressed {
            background-color: rgba(52, 152, 219, 0.4);
        }
    """

def get_context_menu_stylesheet():
    """Get the stylesheet for context menus"""
    return """
        QMenu {
            background-color: white;
            border: 1px solid #BDC3C7;
            padding: 5px;
        }
        QMenu::item {
            padding: 5px 20px;
        }
        QMenu::item:selected {
            background-color: #3498DB;
            color: white;
        }
        QMenu::separator {
            height: 1px;
            background-color: #BDC3C7;
            margin: 5px 15px;
        }
    """

def get_header_label_stylesheet():
    """Get the stylesheet for header labels"""
    return "color: white; font-weight: bold; font-size: 14px;"

def get_db_info_label_stylesheet():
    """Get the stylesheet for database info label"""
    return "color: rgba(255, 255, 255, 0.8); padding: 8px 0; font-size: 13px;"

def get_tables_header_stylesheet():
    """Get the stylesheet for tables header"""
    return "color: white; font-weight: bold; font-size: 14px; margin-top: 8px;"

def get_row_count_label_stylesheet():
    """Get the stylesheet for row count label"""
    return "color: #7F8C8D; font-size: 12px; font-style: italic; padding: 8px 0;" 