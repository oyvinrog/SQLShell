# SQLShell Distribution & Installation

This directory contains scripts and configurations for building and distributing SQLShell.

## Quick Start

### Prerequisites

```bash
# Install PyInstaller
pip install pyinstaller

# For Linux installers
sudo apt install makeself    # Self-extracting installer

# Optional: AppImage tools
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage
sudo mv appimagetool-x86_64.AppImage /usr/local/bin/appimagetool
```

### Building the Executable

```bash
# From project root
cd /path/to/SQLShell

# Build executable (directory mode - recommended)
python build.py

# Build single-file executable (larger, slower startup)
python build.py --onefile

# Build with installer
python build.py --installer

# Clean build artifacts
python build.py --clean
```

## Build Outputs

After building, you'll find outputs in the `dist/` directory:

| File | Description |
|------|-------------|
| `SQLShell/` | Directory containing the application and dependencies |
| `SQLShell-x.x.x-linux-x64.tar.gz` | Portable tarball for Linux |
| `SQLShell-x.x.x-linux-x64-installer.run` | Self-extracting Linux installer |
| `SQLShell-x.x.x-linux-x64.AppImage` | Linux AppImage (if appimagetool available) |
| `sqlshell_x.x.x_amd64.deb` | Debian/Ubuntu package |
| `SQLShell-x.x.x-win64-setup.exe` | Windows installer |

## Platform-Specific Instructions

### Linux

#### Option 1: Self-Extracting Installer (Recommended)

```bash
# Build the application and installer
python build.py --installer

# Run the installer
chmod +x dist/SQLShell-*-linux-x64-installer.run
./dist/SQLShell-*-linux-x64-installer.run

# Or with sudo for system-wide installation
sudo ./dist/SQLShell-*-linux-x64-installer.run
```

#### Option 2: Tarball (Portable)

```bash
# Extract anywhere
tar -xzf SQLShell-*-linux-x64.tar.gz
cd SQLShell
./SQLShell
```

#### Option 3: Debian Package

```bash
# Build .deb package
python build.py --installer

# Install
sudo dpkg -i dist/sqlshell_*_amd64.deb

# Fix any dependency issues
sudo apt-get install -f
```

#### Option 4: AppImage

```bash
# Build AppImage
python build.py --installer

# Run directly (no installation needed)
chmod +x SQLShell-*-linux-x64.AppImage
./SQLShell-*-linux-x64.AppImage
```

### Windows

#### Building on Windows

```powershell
# Install dependencies
pip install pyinstaller pillow

# Build
python build.py

# Create installer (requires NSIS or Inno Setup)
python build.py --installer
```

#### Creating Windows Icon

The build script auto-creates `icon.ico` from `icon.png`. If manual creation is needed:

```python
from PIL import Image

img = Image.open('sqlshell/resources/icon.png')
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
icons = [img.resize(size, Image.Resampling.LANCZOS) for size in sizes]
icons[0].save('sqlshell/resources/icon.ico', format='ICO', sizes=sizes)
```

#### Building Installer with Inno Setup

1. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Build the application: `python build.py`
3. Open `installer/windows/sqlshell_inno.iss` in Inno Setup
4. Click Build > Compile

#### Building Installer with NSIS

1. Install [NSIS](https://nsis.sourceforge.io/)
2. Build the application: `python build.py`
3. Run: `makensis installer/windows/installer.nsi`

### macOS

```bash
# Build on macOS
python build.py

# Creates SQLShell.app bundle
# For DMG, run:
python build.py --installer
```

## Directory Structure

```
installer/
├── README.md              # This file
├── linux/
│   └── create_installer.sh    # Linux installer creator
└── windows/
    ├── installer.nsi          # NSIS script
    └── sqlshell_inno.iss      # Inno Setup script
```

## Troubleshooting

### Missing Modules

If you get import errors at runtime, add hidden imports to `sqlshell.spec`:

```python
hiddenimports += ['missing_module']
```

### Large File Size

To reduce size:
1. Use `--exclude-module` for unused packages
2. Use UPX compression (install UPX and PyInstaller will use it automatically)
3. Remove sample_data from the build

### PyQt6 Issues

If PyQt6 plugins aren't found:
```python
# Add to spec file
from PyInstaller.utils.hooks import collect_data_files
datas += collect_data_files('PyQt6')
```

### DuckDB Issues

DuckDB requires its shared library. Ensure it's included:
```python
datas += collect_data_files('duckdb')
```

## Signing (Production)

### Windows Code Signing

```powershell
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist\SQLShell-setup.exe
```

### macOS Code Signing

```bash
codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" dist/SQLShell.app
```

### Notarization (macOS)

```bash
xcrun notarytool submit SQLShell.dmg --apple-id your@email.com --password app-specific-password --team-id TEAMID
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Build

on:
  release:
    types: [created]

jobs:
  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pyinstaller
      - run: python build.py --installer
      - uses: actions/upload-artifact@v3
        with:
          name: linux-build
          path: dist/*.tar.gz

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pyinstaller
      - run: python build.py
      # Add Inno Setup compilation here
```

