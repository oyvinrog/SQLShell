# Contributing to SQLShell

Thank you for your interest in contributing to SQLShell! This guide covers the developer tools and workflows you'll need.

## Table of Contents

- [Development Setup](#development-setup)
- [Version Management](#version-management)
- [Running Tests](#running-tests)
- [Building Distributions](#building-distributions)
- [Release Workflow](#release-workflow)

---

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/oyvinrog/SQLShell.git
   cd SQLShell
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or: venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .  # Install in editable mode
   ```

4. **Run the application**
   ```bash
   python run.py
   # or: sqls (after pip install -e .)
   ```

---

## Version Management

### `bump_version.py`

SQLShell uses a centralized version management system. The version is defined in **one place** (`pyproject.toml`), and all other files read it dynamically or get updated by the bump script.

#### Show Current Version

```bash
python bump_version.py
```

Output:
```
╔══════════════════════════════════════════════════════════════╗
║                  SQLShell Version Manager                    ║
╚══════════════════════════════════════════════════════════════╝

Current version: 0.3.3

Usage:
    python bump_version.py 0.4.0      # Set specific version
    python bump_version.py --patch    # 0.3.3 → 0.3.4
    python bump_version.py --minor    # 0.3.3 → 0.4.0
    python bump_version.py --major    # 0.3.3 → 1.0.0
```

#### Bump Version

```bash
# Set a specific version
python bump_version.py 0.4.0

# Bump patch version (0.3.3 → 0.3.4)
python bump_version.py --patch

# Bump minor version (0.3.3 → 0.4.0)
python bump_version.py --minor

# Bump major version (0.3.3 → 1.0.0)
python bump_version.py --major

# Preview changes without applying them
python bump_version.py --patch --dry-run
```

#### How It Works

| File | Update Method |
|------|---------------|
| `pyproject.toml` | ✏️ Updated by `bump_version.py` (source of truth) |
| `sqlshell/__init__.py` | 🔄 Reads dynamically from `pyproject.toml` |
| `build.py` | 🔄 Reads dynamically from `pyproject.toml` |
| `sqlshell.spec` | 🔄 Reads dynamically from `pyproject.toml` |
| `installer/linux/create_installer.sh` | ✏️ Updated by `bump_version.py` |
| `installer/windows/sqlshell_inno.iss` | ✏️ Updated by `bump_version.py` |

---

## Running Tests

### `run_tests.py`

A unified test runner that wraps pytest with convenient options.

#### Basic Usage

```bash
# Run all tests
python run_tests.py

# Run with verbose output
python run_tests.py --verbose
# or: python run_tests.py -v
```

#### Test Modes

```bash
# Run only unit tests (fast)
python run_tests.py --unit

# Run only integration tests
python run_tests.py --integration

# Run quick tests (skip slow/performance tests)
python run_tests.py --quick

# Run tests for current branch features
python run_tests.py --branch
```

#### Coverage Reports

```bash
# Run with coverage report
python run_tests.py --coverage

# Coverage report is generated at: coverage_html/index.html
```

#### Specific Tests

```bash
# Run a specific test file
python run_tests.py --specific tests/test_database_manager.py

# Run a specific test directory
python run_tests.py --specific tests/f5_f9_functionality/
```

#### Utility Commands

```bash
# Show test status summary
python run_tests.py --status

# List all test files in the project
python run_tests.py --list

# Install test dependencies
python run_tests.py --install-deps

# Run tests in parallel (faster)
python run_tests.py --parallel
```

#### All Options

| Option | Short | Description |
|--------|-------|-------------|
| `--all` | `-a` | Run all tests (default) |
| `--unit` | `-u` | Run only unit tests |
| `--integration` | `-i` | Run only integration tests |
| `--quick` | `-q` | Skip slow/performance tests |
| `--coverage` | `-c` | Generate coverage report |
| `--verbose` | `-v` | Verbose output |
| `--parallel` | `-p` | Run tests in parallel |
| `--specific PATH` | `-s` | Run specific test file/directory |
| `--branch` | `-b` | Run branch-specific tests |
| `--status` | | Show test status summary |
| `--list` | `-l` | List all test files |
| `--install-deps` | | Install test dependencies |

---

## Building Distributions

### `build.py`

Creates standalone executables and platform-specific installers using PyInstaller.

#### Basic Build

```bash
# Build executable (directory mode - recommended)
python build.py

# Output: dist/SQLShell/
```

#### Build Options

```bash
# Build executable + platform installer
python build.py --installer

# Build single-file executable (larger, slower startup)
python build.py --onefile

# Build all distribution formats
python build.py --all

# Clean build artifacts
python build.py --clean
```

#### Platform-Specific Outputs

**Linux:**
- `dist/SQLShell/` - Directory with executable
- `dist/SQLShell-{version}-linux-x64.tar.gz` - Tarball
- `dist/sqlshell_{version}_amd64.deb` - Debian package (requires `dpkg-deb`)
- `dist/SQLShell-{version}-linux-x64.AppImage` - AppImage (requires `appimagetool`)

**Windows:**
- `dist/SQLShell/` - Directory with executable
- `dist/SQLShell-{version}-win64-setup.exe` - Installer (requires NSIS or Inno Setup)

**macOS:**
- `dist/SQLShell.app` - Application bundle
- `dist/SQLShell-{version}-macos.dmg` - Disk image

#### Requirements

- **All platforms:** PyInstaller, Pillow
- **Linux .deb:** `dpkg-deb` (usually pre-installed)
- **Linux AppImage:** [appimagetool](https://github.com/AppImage/AppImageKit/releases)
- **Windows installer:** [NSIS](https://nsis.sourceforge.io/) or [Inno Setup](https://jrsoftware.org/isinfo.php)

---

## Release Workflow

### Manual Release

1. **Bump the version**
   ```bash
   python bump_version.py 0.4.0
   ```

2. **Run tests**
   ```bash
   python run_tests.py
   ```

3. **Commit and tag**
   ```bash
   git commit -am "Bump version to 0.4.0"
   git tag v0.4.0
   git push && git push --tags
   ```

4. **Create GitHub Release**
   - Go to GitHub → Releases → Create new release
   - Select tag `v0.4.0`
   - GitHub Actions will automatically build and upload artifacts

### GitHub Actions

The CI/CD pipeline (`.github/workflows/build-release.yml`) automatically:

1. Publishes to PyPI
2. Builds Linux executable + .deb package
3. Builds Windows executable + installer
4. Builds macOS executable + .dmg
5. Uploads all artifacts to the GitHub Release

---

## Project Structure

```
SQLShell/
├── sqlshell/              # Main package
│   ├── __init__.py        # Version read from pyproject.toml
│   ├── __main__.py        # Application entry point
│   ├── db/                # Database management
│   ├── ui/                # UI components
│   ├── utils/             # Utilities
│   └── resources/         # Icons, images
├── tests/                 # Test suite
├── installer/             # Platform installers
│   ├── linux/
│   └── windows/
├── build.py               # Build script
├── bump_version.py        # Version management
├── run_tests.py           # Test runner
├── pyproject.toml         # Package config (VERSION SOURCE OF TRUTH)
├── sqlshell.spec          # PyInstaller spec
└── requirements.txt       # Dependencies
```

---

## Questions?

Open an issue on [GitHub](https://github.com/oyvinrog/SQLShell/issues) if you have questions or run into problems!

