"""
Tests to verify all critical modules are importable and properly packaged.

This test suite ensures that:
1. All utility modules can be imported
2. All critical subpackages are accessible
3. Dynamic imports used in the application work correctly
4. The package configuration includes all required modules

These tests help catch issues like missing modules in PyInstaller builds
or incorrectly configured package data.
"""

import pytest
import importlib
import sys
import os


class TestCriticalImports:
    """Test that all critical modules can be imported."""
    
    # List of all modules that must be importable
    CRITICAL_MODULES = [
        # Core modules
        'sqlshell',
        'sqlshell.__main__',
        
        # Database modules
        'sqlshell.db',
        'sqlshell.db.database_manager',
        'sqlshell.db.export_manager',
        
        # UI modules
        'sqlshell.ui',
        'sqlshell.ui.filter_header',
        'sqlshell.ui.bar_chart_delegate',
        
        # Utility modules - these are often dynamically imported
        'sqlshell.utils',
        'sqlshell.utils.profile_column',
        'sqlshell.utils.profile_distributions',
        'sqlshell.utils.profile_entropy',
        'sqlshell.utils.profile_foreign_keys',
        'sqlshell.utils.profile_keys',
        'sqlshell.utils.profile_ohe',
        'sqlshell.utils.profile_ohe_advanced',
        'sqlshell.utils.profile_ohe_comparison',
        'sqlshell.utils.profile_prediction',
        'sqlshell.utils.profile_similarity',
        'sqlshell.utils.profile_cn2',
        'sqlshell.utils.search_in_df',
        
        # Other critical modules
        'sqlshell.syntax_highlighter',
        'sqlshell.editor',
        'sqlshell.query_tab',
        'sqlshell.styles',
        'sqlshell.menus',
        'sqlshell.table_list',
        'sqlshell.notification_manager',
        'sqlshell.context_suggester',
        'sqlshell.execution_handler',
        'sqlshell.widgets',
    ]
    
    @pytest.mark.parametrize("module_name", CRITICAL_MODULES)
    def test_module_importable(self, module_name):
        """Test that each critical module can be imported."""
        try:
            module = importlib.import_module(module_name)
            assert module is not None, f"Module {module_name} imported but is None"
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")
    
    def test_profile_column_has_visualize_profile(self):
        """Test the specific import that was failing - profile_column.visualize_profile"""
        try:
            from sqlshell.utils.profile_column import visualize_profile
            assert callable(visualize_profile), "visualize_profile should be callable"
        except ImportError as e:
            pytest.fail(f"Failed to import visualize_profile from profile_column: {e}")
    
    def test_profile_ohe_has_get_ohe(self):
        """Test that profile_ohe exports its main function."""
        try:
            from sqlshell.utils.profile_ohe import get_ohe, visualize_ohe
            assert callable(get_ohe), "get_ohe should be callable"
            assert callable(visualize_ohe), "visualize_ohe should be callable"
        except ImportError as e:
            pytest.fail(f"Failed to import from profile_ohe: {e}")
    
    def test_profile_entropy_has_exports(self):
        """Test that profile_entropy exports its main components."""
        try:
            from sqlshell.utils.profile_entropy import profile, visualize_profile, EntropyProfiler
            assert callable(profile), "profile should be callable"
            assert callable(visualize_profile), "visualize_profile should be callable"
        except ImportError as e:
            pytest.fail(f"Failed to import from profile_entropy: {e}")


class TestDynamicImportPatterns:
    """Test dynamic import patterns used in the application."""
    
    def test_dynamic_import_profile_column(self):
        """
        Test the dynamic import pattern used in __main__.py for 'Explain Column'.
        This is the exact pattern that failed in the PyInstaller build.
        """
        # Simulate the dynamic import pattern from __main__.py line 4030
        try:
            from sqlshell.utils.profile_column import visualize_profile
            assert visualize_profile is not None
        except ImportError as e:
            pytest.fail(
                f"Dynamic import of profile_column failed: {e}\n"
                "This import is used by the 'Explain Column' feature. "
                "Ensure sqlshell.utils is included in PyInstaller datas."
            )
    
    def test_dynamic_import_profile_ohe_advanced(self):
        """Test dynamic import of advanced OHE module."""
        try:
            from sqlshell.utils.profile_ohe_advanced import get_advanced_ohe
            assert get_advanced_ohe is not None
        except ImportError as e:
            pytest.fail(f"Dynamic import of profile_ohe_advanced failed: {e}")


class TestPackageStructure:
    """Test that the package structure is correct."""
    
    def test_utils_directory_exists(self):
        """Test that the utils directory exists and is a package."""
        import sqlshell.utils
        utils_path = os.path.dirname(sqlshell.utils.__file__)
        assert os.path.isdir(utils_path), f"Utils directory not found: {utils_path}"
        
        init_file = os.path.join(utils_path, '__init__.py')
        assert os.path.isfile(init_file), f"Utils __init__.py not found: {init_file}"
    
    def test_utils_contains_all_profile_modules(self):
        """Test that all profile modules exist in the utils directory."""
        import sqlshell.utils
        utils_path = os.path.dirname(sqlshell.utils.__file__)
        
        required_files = [
            'profile_column.py',
            'profile_cn2.py',
            'profile_distributions.py',
            'profile_entropy.py',
            'profile_foreign_keys.py',
            'profile_keys.py',
            'profile_ohe.py',
            'profile_ohe_advanced.py',
            'profile_ohe_comparison.py',
            'profile_prediction.py',
            'profile_similarity.py',
            'search_in_df.py',
        ]
        
        for filename in required_files:
            filepath = os.path.join(utils_path, filename)
            assert os.path.isfile(filepath), f"Required file missing: {filepath}"
    
    def test_db_directory_structure(self):
        """Test that the db directory is properly structured."""
        import sqlshell.db
        db_path = os.path.dirname(sqlshell.db.__file__)
        
        required_files = ['__init__.py', 'database_manager.py', 'export_manager.py']
        for filename in required_files:
            filepath = os.path.join(db_path, filename)
            assert os.path.isfile(filepath), f"Required db file missing: {filepath}"
    
    def test_ui_directory_structure(self):
        """Test that the ui directory is properly structured."""
        import sqlshell.ui
        ui_path = os.path.dirname(sqlshell.ui.__file__)
        
        required_files = ['__init__.py', 'filter_header.py', 'bar_chart_delegate.py']
        for filename in required_files:
            filepath = os.path.join(ui_path, filename)
            assert os.path.isfile(filepath), f"Required ui file missing: {filepath}"


class TestPyInstallerSpecConsistency:
    """Test that the PyInstaller spec file is consistent with the codebase."""
    
    @pytest.fixture
    def spec_content(self):
        """Read the PyInstaller spec file."""
        spec_path = os.path.join(os.path.dirname(__file__), '..', 'sqlshell.spec')
        if os.path.exists(spec_path):
            with open(spec_path, 'r') as f:
                return f.read()
        return None
    
    def test_spec_includes_utils_in_datas(self, spec_content):
        """Test that sqlshell/utils is included in the spec file datas."""
        if spec_content is None:
            pytest.skip("sqlshell.spec not found")
        
        # Check that utils is in the datas section
        assert "sqlshell', 'utils')" in spec_content or "sqlshell/utils" in spec_content, \
            "sqlshell/utils should be included in PyInstaller datas for dynamic imports"
    
    def test_spec_includes_critical_hiddenimports(self, spec_content):
        """Test that critical modules are in hiddenimports."""
        if spec_content is None:
            pytest.skip("sqlshell.spec not found")
        
        critical_imports = [
            'sqlshell.utils.profile_column',
            'sqlshell.utils.profile_ohe',
            'sqlshell.db.database_manager',
        ]
        
        for module in critical_imports:
            assert module in spec_content, \
                f"{module} should be in hiddenimports in sqlshell.spec"


class TestWheelPackageContents:
    """Test that the wheel package contains all required modules."""
    
    def test_pyproject_includes_utils_package(self):
        """Test that pyproject.toml includes sqlshell.utils in packages."""
        pyproject_path = os.path.join(os.path.dirname(__file__), '..', 'pyproject.toml')
        
        if not os.path.exists(pyproject_path):
            pytest.skip("pyproject.toml not found")
        
        with open(pyproject_path, 'r') as f:
            content = f.read()
        
        assert 'sqlshell.utils' in content, \
            "sqlshell.utils should be listed in pyproject.toml packages"
        assert 'sqlshell.db' in content, \
            "sqlshell.db should be listed in pyproject.toml packages"
        assert 'sqlshell.ui' in content, \
            "sqlshell.ui should be listed in pyproject.toml packages"

