"""
Tests for version detection in different runtime environments.

This module tests that the version is correctly detected in:
1. Development mode (reading from pyproject.toml relative to package)
2. Frozen/PyInstaller mode (reading from sys._MEIPASS)
3. Installed package mode (importlib.metadata)
4. Fallback to "0.0.0" when nothing works
"""

import sys
import tempfile
import shutil
from pathlib import Path
from unittest import mock

import pytest


# Get actual version from pyproject.toml for comparison
PROJECT_ROOT = Path(__file__).parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


def get_actual_version():
    """Read the actual version from pyproject.toml."""
    import re
    content = PYPROJECT_PATH.read_text()
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if match:
        return match.group(1)
    raise ValueError("Could not find version in pyproject.toml")


ACTUAL_VERSION = get_actual_version()


class TestVersionDetection:
    """Test version detection in various scenarios."""

    def test_version_matches_pyproject(self):
        """Test that the detected version matches pyproject.toml."""
        from sqlshell import __version__
        assert __version__ == ACTUAL_VERSION, (
            f"Version mismatch: __version__={__version__}, "
            f"pyproject.toml={ACTUAL_VERSION}"
        )

    def test_version_format(self):
        """Test that version follows semantic versioning format."""
        import re
        from sqlshell import __version__
        # Match semantic versioning: X.Y.Z with optional pre-release
        pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$'
        assert re.match(pattern, __version__), (
            f"Version {__version__} does not match semantic versioning format"
        )

    def test_get_version_function_exists(self):
        """Test that _get_version function is accessible."""
        from sqlshell import _get_version
        assert callable(_get_version)
        version = _get_version()
        assert isinstance(version, str)
        assert len(version) > 0


class TestFrozenExecutableVersion:
    """Test version detection in simulated frozen (PyInstaller) environment."""

    def test_frozen_mode_with_bundled_pyproject(self, temp_dir):
        """Test version detection when running as frozen executable with bundled pyproject.toml."""
        # Create a mock pyproject.toml in the temp directory
        mock_pyproject = temp_dir / "pyproject.toml"
        mock_pyproject.write_text(f'''
[project]
name = "sqlshell"
version = "1.2.3"
''')

        # Import the module fresh to test the function
        import importlib
        import sqlshell

        # Mock sys.frozen and sys._MEIPASS
        with mock.patch.object(sys, 'frozen', True, create=True):
            with mock.patch.object(sys, '_MEIPASS', str(temp_dir), create=True):
                # Reload the _get_version function behavior
                # We need to call _get_version directly to test with our mocks
                version = sqlshell._get_version()
                assert version == "1.2.3", (
                    f"Expected version 1.2.3 from bundled pyproject.toml, got {version}"
                )

    def test_frozen_mode_missing_pyproject_falls_through(self, temp_dir):
        """Test that frozen mode without pyproject.toml falls through to other methods."""
        import sqlshell

        # Create empty temp dir (no pyproject.toml)
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        with mock.patch.object(sys, 'frozen', True, create=True):
            with mock.patch.object(sys, '_MEIPASS', str(empty_dir), create=True):
                # Should fall through to development mode or metadata
                version = sqlshell._get_version()
                # Should still get a valid version (from dev mode or metadata)
                assert version == ACTUAL_VERSION or version == "0.0.0"


class TestDevelopmentModeVersion:
    """Test version detection in development mode."""

    def test_development_mode_reads_pyproject(self):
        """Test that development mode correctly reads from pyproject.toml."""
        import sqlshell

        # In development mode, sys.frozen should not be set
        assert not getattr(sys, 'frozen', False), "Test expects non-frozen environment"

        version = sqlshell._get_version()
        assert version == ACTUAL_VERSION, (
            f"Development mode should read version {ACTUAL_VERSION} "
            f"from pyproject.toml, got {version}"
        )


class TestMetadataFallback:
    """Test fallback to importlib.metadata."""

    def test_metadata_fallback_when_pyproject_missing(self, temp_dir):
        """Test that importlib.metadata is used when pyproject.toml is not found."""
        import sqlshell

        # Mock the pyproject.toml path check to fail
        original_parent = Path(sqlshell.__file__).parent

        def mock_exists(self):
            # Make pyproject.toml appear to not exist
            if "pyproject.toml" in str(self):
                return False
            return original_parent.exists()

        with mock.patch.object(sys, 'frozen', False, create=True):
            with mock.patch.object(Path, 'exists', mock_exists):
                # The function should fall through to importlib.metadata or "0.0.0"
                version = sqlshell._get_version()
                # Either gets it from metadata or falls back to 0.0.0
                assert isinstance(version, str)
                assert len(version) > 0


class TestFallbackVersion:
    """Test the final fallback to 0.0.0."""

    def test_fallback_to_zero_version(self, temp_dir):
        """Test that version falls back to 0.0.0 when all methods fail."""
        import sqlshell

        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        # Mock everything to fail
        with mock.patch.object(sys, 'frozen', True, create=True):
            with mock.patch.object(sys, '_MEIPASS', str(empty_dir), create=True):
                # Mock Path to make pyproject.toml not exist anywhere
                original_exists = Path.exists

                def mock_exists(self):
                    if "pyproject.toml" in str(self):
                        return False
                    return original_exists(self)

                # Mock importlib.metadata.version to raise
                with mock.patch.object(Path, 'exists', mock_exists):
                    with mock.patch('importlib.metadata.version', side_effect=Exception("No metadata")):
                        version = sqlshell._get_version()
                        assert version == "0.0.0", (
                            f"Expected fallback version 0.0.0, got {version}"
                        )


class TestVersionConsistency:
    """Test that version is consistent across different access methods."""

    def test_version_accessible_from_package(self):
        """Test that __version__ is accessible from the package."""
        from sqlshell import __version__
        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_version_in_menus(self):
        """Test that menus.get_version() returns the same version."""
        from sqlshell import __version__
        from sqlshell.menus import get_version

        menu_version = get_version()
        assert menu_version == __version__, (
            f"Menu version {menu_version} does not match package version {__version__}"
        )

    def test_version_not_zero_in_development(self):
        """Test that version is not 0.0.0 in development mode."""
        from sqlshell import __version__

        # In development mode, we should get the real version
        if not getattr(sys, 'frozen', False):
            assert __version__ != "0.0.0", (
                "Version should not be 0.0.0 in development mode"
            )


class TestPyInstallerCompatibility:
    """Test PyInstaller-specific compatibility."""

    def test_sys_meipass_handling(self, temp_dir):
        """Test that sys._MEIPASS is correctly handled."""
        import sqlshell

        # Create a valid pyproject.toml in temp dir
        pyproject = temp_dir / "pyproject.toml"
        pyproject.write_text('''
[project]
name = "sqlshell"
version = "9.9.9"
''')

        # Simulate frozen environment
        with mock.patch.object(sys, 'frozen', True, create=True):
            with mock.patch.object(sys, '_MEIPASS', str(temp_dir), create=True):
                version = sqlshell._get_version()
                assert version == "9.9.9"

    def test_frozen_attribute_checked_correctly(self):
        """Test that sys.frozen is checked with getattr for safety."""
        import sqlshell

        # Ensure the function doesn't crash if frozen isn't set
        # (which is the normal case in non-frozen Python)
        assert not hasattr(sys, 'frozen') or not sys.frozen

        # _get_version should work without raising AttributeError
        version = sqlshell._get_version()
        assert isinstance(version, str)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

