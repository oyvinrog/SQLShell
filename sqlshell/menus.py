"""
Menu creation and management for SQLShell application.
This module contains functions to create and manage the application's menus.
"""

from PyQt6.QtWidgets import QMessageBox


def get_version():
    """Get the application version from pyproject.toml or __init__.py."""
    try:
        from sqlshell import __version__
        return __version__
    except ImportError:
        return "0.3.3"

def create_file_menu(main_window):
    """Create the File menu with project management actions.
    
    Args:
        main_window: The SQLShell main window instance
        
    Returns:
        The created File menu
    """
    # Create File menu
    file_menu = main_window.menuBar().addMenu('&File')
    
    # Project management actions
    new_project_action = file_menu.addAction('New Project')
    new_project_action.setShortcut('Ctrl+N')
    new_project_action.triggered.connect(main_window.new_project)
    
    open_project_action = file_menu.addAction('Open Project...')
    open_project_action.setShortcut('Ctrl+O')
    open_project_action.triggered.connect(main_window.open_project)
    
    # Add Recent Projects submenu
    main_window.recent_projects_menu = file_menu.addMenu('Recent Projects')
    main_window.update_recent_projects_menu()
    
    # Add Quick Access submenu for files
    main_window.quick_access_menu = file_menu.addMenu('Quick Access Files')
    main_window.update_quick_access_menu()
    
    save_project_action = file_menu.addAction('Save Project')
    save_project_action.setShortcut('Ctrl+S')
    save_project_action.triggered.connect(main_window.save_project)
    
    save_project_as_action = file_menu.addAction('Save Project As...')
    save_project_as_action.setShortcut('Ctrl+Shift+S')
    save_project_as_action.triggered.connect(main_window.save_project_as)
    
    file_menu.addSeparator()
    
    # Load data action (databases, CSV, Excel, Parquet, etc.)
    load_data_action = file_menu.addAction('Load Data...')
    load_data_action.setShortcut('Ctrl+L')
    load_data_action.triggered.connect(main_window.show_load_dialog)
    
    file_menu.addSeparator()
    
    exit_action = file_menu.addAction('Exit')
    exit_action.setShortcut('Ctrl+Q')
    exit_action.triggered.connect(main_window.close)
    
    return file_menu


def create_view_menu(main_window):
    """Create the View menu with window management options.
    
    Args:
        main_window: The SQLShell main window instance
        
    Returns:
        The created View menu
    """
    # Create View menu
    view_menu = main_window.menuBar().addMenu('&View')
    
    # Search action
    search_action = view_menu.addAction('Search in Results...')
    search_action.setShortcut('Ctrl+F')
    search_action.triggered.connect(main_window.show_search_dialog)
    
    view_menu.addSeparator()
    
    # Toggle sidebar visibility
    main_window.toggle_sidebar_action = view_menu.addAction('Toggle Sidebar')
    main_window.toggle_sidebar_action.setShortcut('Ctrl+B')
    main_window.toggle_sidebar_action.setCheckable(True)
    main_window.toggle_sidebar_action.setChecked(True)  # Sidebar visible by default
    main_window.toggle_sidebar_action.triggered.connect(main_window.toggle_sidebar)
    
    # Compact mode - reduces padding and hides secondary UI elements
    main_window.compact_mode_action = view_menu.addAction('Compact Mode')
    main_window.compact_mode_action.setShortcut('Ctrl+Shift+C')
    main_window.compact_mode_action.setCheckable(True)
    main_window.compact_mode_action.setChecked(False)
    main_window.compact_mode_action.triggered.connect(main_window.toggle_compact_mode)
    
    view_menu.addSeparator()
    
    # Maximized window option
    maximize_action = view_menu.addAction('Maximize Window')
    maximize_action.setShortcut('F11')
    maximize_action.triggered.connect(main_window.toggle_maximize_window)
    
    # Zoom submenu
    zoom_menu = view_menu.addMenu('Zoom')
    
    zoom_in_action = zoom_menu.addAction('Zoom In')
    zoom_in_action.setShortcut('Ctrl++')
    zoom_in_action.triggered.connect(lambda: main_window.change_zoom(1.1))
    
    zoom_out_action = zoom_menu.addAction('Zoom Out')
    zoom_out_action.setShortcut('Ctrl+-')
    zoom_out_action.triggered.connect(lambda: main_window.change_zoom(0.9))
    
    reset_zoom_action = zoom_menu.addAction('Reset Zoom')
    reset_zoom_action.setShortcut('Ctrl+0')
    reset_zoom_action.triggered.connect(lambda: main_window.reset_zoom())
    
    return view_menu


def create_tab_menu(main_window):
    """Create the Tab menu with tab management actions.
    
    Args:
        main_window: The SQLShell main window instance
        
    Returns:
        The created Tab menu
    """
    # Create Tab menu
    tab_menu = main_window.menuBar().addMenu('&Tab')
    
    new_tab_action = tab_menu.addAction('New Tab')
    new_tab_action.setShortcut('Ctrl+T')
    new_tab_action.triggered.connect(main_window.add_tab)
    
    duplicate_tab_action = tab_menu.addAction('Duplicate Current Tab')
    duplicate_tab_action.setShortcut('Ctrl+D')
    duplicate_tab_action.triggered.connect(main_window.duplicate_current_tab)
    
    rename_tab_action = tab_menu.addAction('Rename Current Tab')
    rename_tab_action.setShortcut('Ctrl+R')
    rename_tab_action.triggered.connect(main_window.rename_current_tab)
    
    close_tab_action = tab_menu.addAction('Close Current Tab')
    close_tab_action.setShortcut('Ctrl+W')
    close_tab_action.triggered.connect(main_window.close_current_tab)
    
    return tab_menu


def create_preferences_menu(main_window):
    """Create the Preferences menu with user settings.
    
    Args:
        main_window: The SQLShell main window instance
        
    Returns:
        The created Preferences menu
    """
    # Create Preferences menu
    preferences_menu = main_window.menuBar().addMenu('&Preferences')
    
    # Auto-load recent project option
    auto_load_action = preferences_menu.addAction('Auto-load Most Recent Project')
    auto_load_action.setCheckable(True)
    auto_load_action.setChecked(main_window.auto_load_recent_project)
    auto_load_action.triggered.connect(lambda checked: toggle_auto_load(main_window, checked))
    
    preferences_menu.addSeparator()
    
    # AI Autocomplete settings
    ai_settings_action = preferences_menu.addAction('🤖 AI Autocomplete Settings...')
    ai_settings_action.triggered.connect(lambda: show_ai_settings(main_window))
    
    return preferences_menu


def show_ai_settings(main_window):
    """Show the AI autocomplete settings dialog.
    
    Args:
        main_window: The SQLShell main window instance
    """
    from sqlshell.ai_settings_dialog import show_ai_settings_dialog
    show_ai_settings_dialog(main_window)


def toggle_auto_load(main_window, checked):
    """Toggle the auto-load recent project setting.
    
    Args:
        main_window: The SQLShell main window instance
        checked: Boolean indicating whether the option is checked
    """
    main_window.auto_load_recent_project = checked
    main_window.save_recent_projects()  # Save the preference
    main_window.statusBar().showMessage(
        f"Auto-load most recent project {'enabled' if checked else 'disabled'}", 
        2000
    )


def create_about_menu(main_window):
    """Create the About menu with version info and Easter egg.
    
    Args:
        main_window: The SQLShell main window instance
        
    Returns:
        The created About menu
    """
    # Create About menu
    about_menu = main_window.menuBar().addMenu('&About')
    
    # Version info action
    version_action = about_menu.addAction(f'Version: {get_version()}')
    version_action.setEnabled(False)  # Just display, not clickable
    
    about_menu.addSeparator()
    
    # About SQLShell action (opens Space Invaders!)
    about_action = about_menu.addAction('About SQLShell...')
    about_action.triggered.connect(lambda: show_about_dialog(main_window))
    
    return about_menu


def show_about_dialog(main_window):
    """Show the About dialog with Space Invaders game.
    
    Args:
        main_window: The SQLShell main window instance
    """
    from sqlshell.space_invaders import show_space_invaders
    show_space_invaders(main_window)


def setup_menubar(main_window):
    """Set up the complete menu bar for the application.
    
    Args:
        main_window: The SQLShell main window instance
    """
    # Create the menu bar (in case it doesn't exist)
    menubar = main_window.menuBar()
    
    # Create menus
    file_menu = create_file_menu(main_window)
    view_menu = create_view_menu(main_window)
    tab_menu = create_tab_menu(main_window)
    preferences_menu = create_preferences_menu(main_window)
    about_menu = create_about_menu(main_window)
    
    return menubar 