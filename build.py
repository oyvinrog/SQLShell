#!/usr/bin/env python3
"""
Build script for SQLShell distribution
Creates standalone executables and installers for different platforms.

Usage:
    python build.py              # Build executable only
    python build.py --installer  # Build executable + installer
    python build.py --clean      # Clean build artifacts
    python build.py --onefile    # Build single-file executable
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Configuration
APP_NAME = "SQLShell"
APP_AUTHOR = "SQLShell Team"
APP_DESCRIPTION = "A powerful SQL shell with GUI interface for data analysis"

def get_version_from_pyproject() -> str:
    """Read version from pyproject.toml (single source of truth)."""
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    content = pyproject_path.read_text()
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if match:
        return match.group(1)
    raise ValueError("Could not find version in pyproject.toml")

APP_VERSION = get_version_from_pyproject()

SCRIPT_DIR = Path(__file__).parent.resolve()
BUILD_DIR = SCRIPT_DIR / "build"
DIST_DIR = SCRIPT_DIR / "dist"
INSTALLER_DIR = SCRIPT_DIR / "installer"


def run_command(cmd: list, cwd: Path = None) -> int:
    """Run a command and return exit code."""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def clean_build():
    """Remove build artifacts."""
    print("Cleaning build artifacts...")
    
    dirs_to_remove = [
        BUILD_DIR,
        DIST_DIR / APP_NAME,
        INSTALLER_DIR,
    ]
    
    files_to_remove = [
        DIST_DIR / f"{APP_NAME}.exe",
        DIST_DIR / f"{APP_NAME}",
        DIST_DIR / f"{APP_NAME}-{APP_VERSION}-linux-x64.tar.gz",
        DIST_DIR / f"{APP_NAME}-{APP_VERSION}-linux-x64.AppImage", 
        DIST_DIR / f"{APP_NAME}-{APP_VERSION}-win64-setup.exe",
        DIST_DIR / f"{APP_NAME}-{APP_VERSION}-macos.dmg",
    ]
    
    for d in dirs_to_remove:
        if d.exists():
            print(f"  Removing directory: {d}")
            shutil.rmtree(d)
    
    for f in files_to_remove:
        if f.exists():
            print(f"  Removing file: {f}")
            f.unlink()
    
    print("Clean complete!")


def check_dependencies():
    """Check if required dependencies are installed."""
    print("Checking dependencies...")
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"  ✓ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("  ✗ PyInstaller not found. Installing...")
        run_command([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Check PyQt6 (critical for Linux builds to ensure ICU libraries are available)
    try:
        import PyQt6
        from pathlib import Path
        pyqt6_path = Path(PyQt6.__file__).parent
        print(f"  ✓ PyQt6 installed at {pyqt6_path}")
        
        # On Linux, verify Qt6 libraries exist
        if platform.system() == "Linux":
            qt6_lib_path = pyqt6_path / "Qt6" / "lib"
            if qt6_lib_path.exists():
                icu_libs = list(qt6_lib_path.glob("libicu*.so*"))
                if icu_libs:
                    print(f"  ✓ Found {len(icu_libs)} ICU libraries in PyQt6")
                else:
                    print("  ⚠ WARNING: ICU libraries not found in PyQt6!")
                    print("    Build may fail on target systems.")
            else:
                print(f"  ⚠ WARNING: Qt6 lib directory not found: {qt6_lib_path}")
    except ImportError:
        print("  ✗ PyQt6 not found! Please install: pip install PyQt6")
        sys.exit(1)


def check_icons():
    """Check if required icon files exist."""
    icon_source = SCRIPT_DIR / "sqlshell" / "resources" / "icon.png"
    if not icon_source.exists():
        print(f"  ✗ Warning: Icon source not found at {icon_source}")
        return False
    
    print(f"  ✓ Icon files present")
    return True


def build_executable(onefile: bool = False):
    """Build the executable using PyInstaller."""
    print(f"\nBuilding {APP_NAME} executable...")
    
    if onefile:
        # Single file mode - creates one large executable
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name", APP_NAME,
            "--windowed",
            "--onefile",
            "--clean",
            "--noconfirm",
            # Add data files
            "--add-data", f"sqlshell/resources{os.pathsep}sqlshell/resources",
            "--add-data", f"sqlshell/data{os.pathsep}sqlshell/data",
            # Hidden imports for complex packages
            "--hidden-import", "pandas",
            "--hidden-import", "numpy", 
            "--hidden-import", "scipy",
            "--hidden-import", "sklearn",
            "--hidden-import", "duckdb",
            "--hidden-import", "PyQt6",
            "--hidden-import", "fastparquet",
            "--hidden-import", "matplotlib",
            "--hidden-import", "seaborn",
            "--hidden-import", "nltk",
            # Collect all submodules
            "--collect-all", "duckdb",
            "--collect-all", "sklearn",
            "--collect-all", "PyQt6",
            # Exclude unnecessary
            "--exclude-module", "tkinter",
            "--exclude-module", "test",
            "--exclude-module", "pytest",
        ]
        
        # Add icon based on platform
        icon_path = SCRIPT_DIR / "sqlshell" / "resources" / "icon.png"
        if platform.system() == "Windows":
            ico_path = SCRIPT_DIR / "sqlshell" / "resources" / "icon.ico"
            if ico_path.exists():
                cmd.extend(["--icon", str(ico_path)])
        elif platform.system() == "Darwin":
            icns_path = SCRIPT_DIR / "sqlshell" / "resources" / "icon.icns"
            if icns_path.exists():
                cmd.extend(["--icon", str(icns_path)])
        elif icon_path.exists():
            cmd.extend(["--icon", str(icon_path)])
        
        cmd.append("sqlshell/__main__.py")
    else:
        # Use spec file for directory mode (recommended)
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            str(SCRIPT_DIR / "sqlshell.spec"),
        ]
    
    result = run_command(cmd, cwd=SCRIPT_DIR)
    
    if result == 0:
        print(f"\n✓ Build successful! Output in: {DIST_DIR / APP_NAME}")
    else:
        print(f"\n✗ Build failed with exit code {result}")
        sys.exit(result)
    
    return result == 0


def create_linux_tarball():
    """Create a tarball distribution for Linux."""
    print("\nCreating Linux tarball...")
    
    output_name = f"{APP_NAME}-{APP_VERSION}-linux-x64.tar.gz"
    output_path = DIST_DIR / output_name
    
    import tarfile
    
    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(
            DIST_DIR / APP_NAME,
            arcname=APP_NAME
        )
    
    print(f"  Created: {output_path}")
    return output_path


def create_linux_appimage():
    """Create an AppImage for Linux (requires appimagetool)."""
    print("\nCreating Linux AppImage...")
    
    appdir = INSTALLER_DIR / f"{APP_NAME}.AppDir"
    appdir.mkdir(parents=True, exist_ok=True)
    
    # Copy application files
    shutil.copytree(DIST_DIR / APP_NAME, appdir / "usr" / "bin", dirs_exist_ok=True)
    
    # Create AppRun script
    apprun = appdir / "AppRun"
    apprun.write_text(f"""#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${{SELF%/*}}
export PATH="${{HERE}}/usr/bin:${{PATH}}"
export LD_LIBRARY_PATH="${{HERE}}/usr/lib:${{LD_LIBRARY_PATH}}"
exec "${{HERE}}/usr/bin/{APP_NAME}" "$@"
""")
    apprun.chmod(0o755)
    
    # Create .desktop file
    desktop = appdir / f"{APP_NAME.lower()}.desktop"
    desktop.write_text(f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Exec={APP_NAME}
Icon={APP_NAME.lower()}
Categories=Development;Database;
Comment={APP_DESCRIPTION}
Terminal=false
""")
    
    # Copy icon
    icon_src = SCRIPT_DIR / "sqlshell" / "resources" / "icon.png"
    if icon_src.exists():
        shutil.copy(icon_src, appdir / f"{APP_NAME.lower()}.png")
    
    # Check for appimagetool
    appimagetool = shutil.which("appimagetool")
    if appimagetool:
        output_name = f"{APP_NAME}-{APP_VERSION}-linux-x64.AppImage"
        output_path = DIST_DIR / output_name
        run_command([appimagetool, str(appdir), str(output_path)])
        print(f"  Created: {output_path}")
        return output_path
    else:
        print("  Warning: appimagetool not found. AppImage not created.")
        print("  Download from: https://github.com/AppImage/AppImageKit/releases")
        return None


def create_linux_deb():
    """Create a .deb package for Debian/Ubuntu."""
    print("\nCreating Debian package...")
    
    deb_root = INSTALLER_DIR / "deb" / APP_NAME.lower()
    deb_root.mkdir(parents=True, exist_ok=True)
    
    # Create directory structure
    (deb_root / "DEBIAN").mkdir(exist_ok=True)
    (deb_root / "usr" / "bin").mkdir(parents=True, exist_ok=True)
    (deb_root / "usr" / "share" / "applications").mkdir(parents=True, exist_ok=True)
    (deb_root / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps").mkdir(parents=True, exist_ok=True)
    (deb_root / "opt" / APP_NAME.lower()).mkdir(parents=True, exist_ok=True)
    
    # Copy application
    shutil.copytree(DIST_DIR / APP_NAME, deb_root / "opt" / APP_NAME.lower() / "bin", dirs_exist_ok=True)
    
    # Create launcher script
    launcher = deb_root / "usr" / "bin" / APP_NAME.lower()
    launcher.write_text(f"""#!/bin/bash
exec /opt/{APP_NAME.lower()}/bin/{APP_NAME} "$@"
""")
    launcher.chmod(0o755)
    
    # Create control file
    import subprocess
    arch = subprocess.check_output(["dpkg", "--print-architecture"]).decode().strip()
    
    control = deb_root / "DEBIAN" / "control"
    # Calculate installed size (in KB)
    installed_size = sum(f.stat().st_size for f in (deb_root / "opt").rglob("*") if f.is_file()) // 1024
    
    control.write_text(f"""Package: {APP_NAME.lower()}
Version: {APP_VERSION}
Section: database
Priority: optional
Architecture: {arch}
Installed-Size: {installed_size}
Maintainer: {APP_AUTHOR}
Description: {APP_DESCRIPTION}
 SQLShell is a powerful SQL query tool with GUI interface
 for data analysis. It supports DuckDB, SQLite, and various
 file formats including CSV, Parquet, and Excel.
""")
    
    # Create .desktop file
    desktop = deb_root / "usr" / "share" / "applications" / f"{APP_NAME.lower()}.desktop"
    desktop.write_text(f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Exec={APP_NAME.lower()}
Icon={APP_NAME.lower()}
Categories=Development;Database;
Comment={APP_DESCRIPTION}
Terminal=false
""")
    
    # Copy icon
    icon_src = SCRIPT_DIR / "sqlshell" / "resources" / "icon.png"
    if icon_src.exists():
        shutil.copy(
            icon_src,
            deb_root / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{APP_NAME.lower()}.png"
        )
    
    # Build .deb package
    output_name = f"{APP_NAME.lower()}_{APP_VERSION}_{arch}.deb"
    output_path = DIST_DIR / output_name
    
    result = run_command(["dpkg-deb", "--build", str(deb_root), str(output_path)])
    
    if result == 0:
        print(f"  Created: {output_path}")
        return output_path
    else:
        print("  Error: Failed to create .deb package")
        return None


def create_windows_installer():
    """Create a Windows installer using NSIS."""
    print("\nCreating Windows installer...")
    
    nsis_script = INSTALLER_DIR / "windows" / "installer.nsi"
    nsis_script.parent.mkdir(parents=True, exist_ok=True)
    
    # Create NSIS script
    nsis_content = f"""
; SQLShell Windows Installer Script
; Requires NSIS 3.x

!include "MUI2.nsh"
!include "FileFunc.nsh"

; General
Name "{APP_NAME}"
OutFile "..\\..\\dist\\{APP_NAME}-{APP_VERSION}-win64-setup.exe"
InstallDir "$PROGRAMFILES64\\{APP_NAME}"
InstallDirRegKey HKLM "Software\\{APP_NAME}" "InstallDir"
RequestExecutionLevel admin

; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "..\\..\\sqlshell\\resources\\icon.ico"
!define MUI_UNICON "..\\..\\sqlshell\\resources\\icon.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\\..\\sqlshell\\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer Section
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Copy all files from dist
    File /r "..\\..\\dist\\{APP_NAME}\\*.*"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
    
    ; Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\\{APP_NAME}"
    CreateShortcut "$SMPROGRAMS\\{APP_NAME}\\{APP_NAME}.lnk" "$INSTDIR\\{APP_NAME}.exe"
    CreateShortcut "$SMPROGRAMS\\{APP_NAME}\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"
    
    ; Create Desktop shortcut
    CreateShortcut "$DESKTOP\\{APP_NAME}.lnk" "$INSTDIR\\{APP_NAME}.exe"
    
    ; Registry entries for Add/Remove Programs
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "DisplayName" "{APP_NAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "UninstallString" "$INSTDIR\\Uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "DisplayIcon" "$INSTDIR\\{APP_NAME}.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "Publisher" "{APP_AUTHOR}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "DisplayVersion" "{APP_VERSION}"
    
    ; Get installed size
    ${{GetSize}} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "EstimatedSize" "$0"
SectionEnd

; Uninstaller Section
Section "Uninstall"
    ; Remove files
    RMDir /r "$INSTDIR"
    
    ; Remove Start Menu shortcuts
    RMDir /r "$SMPROGRAMS\\{APP_NAME}"
    
    ; Remove Desktop shortcut
    Delete "$DESKTOP\\{APP_NAME}.lnk"
    
    ; Remove registry entries
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}"
    DeleteRegKey HKLM "Software\\{APP_NAME}"
SectionEnd
"""
    
    nsis_script.write_text(nsis_content)
    print(f"  Created NSIS script: {nsis_script}")
    
    # Check for NSIS compiler
    makensis = shutil.which("makensis")
    if makensis:
        result = run_command([makensis, str(nsis_script)])
        if result == 0:
            output_path = DIST_DIR / f"{APP_NAME}-{APP_VERSION}-win64-setup.exe"
            print(f"  Created: {output_path}")
            return output_path
    else:
        print("  Warning: NSIS not found. Installer script created but not compiled.")
        print("  Install NSIS from: https://nsis.sourceforge.io/")
    
    return nsis_script


def create_macos_dmg():
    """Create a macOS DMG installer."""
    print("\nCreating macOS DMG...")
    
    if platform.system() != "Darwin":
        print("  Warning: DMG creation only available on macOS")
        return None
    
    app_path = DIST_DIR / f"{APP_NAME}.app"
    if not app_path.exists():
        print(f"  Error: {app_path} not found. Build with spec file first.")
        return None
    
    output_name = f"{APP_NAME}-{APP_VERSION}-macos.dmg"
    output_path = DIST_DIR / output_name
    
    # Create DMG using hdiutil
    temp_dmg = DIST_DIR / "temp.dmg"
    
    # Create temporary DMG
    run_command([
        "hdiutil", "create",
        "-volname", APP_NAME,
        "-srcfolder", str(app_path),
        "-ov",
        str(temp_dmg)
    ])
    
    # Convert to compressed DMG
    run_command([
        "hdiutil", "convert",
        str(temp_dmg),
        "-format", "UDZO",
        "-o", str(output_path)
    ])
    
    temp_dmg.unlink()
    
    print(f"  Created: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description=f"Build {APP_NAME} distribution")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts")
    parser.add_argument("--installer", action="store_true", help="Create platform installer")
    parser.add_argument("--onefile", action="store_true", help="Create single-file executable")
    parser.add_argument("--all", action="store_true", help="Build all distribution formats")
    args = parser.parse_args()
    
    if args.clean:
        clean_build()
        return
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    {APP_NAME} Build Script                      ║
║                      Version {APP_VERSION}                          ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Check dependencies
    check_dependencies()
    
    # Check platform icons exist
    check_icons()
    
    # Build executable
    success = build_executable(onefile=args.onefile)
    
    if not success:
        return
    
    # Create installers if requested
    if args.installer or args.all:
        INSTALLER_DIR.mkdir(exist_ok=True)
        
        system = platform.system()
        
        if system == "Linux":
            create_linux_tarball()
            create_linux_appimage()
            if shutil.which("dpkg-deb"):
                create_linux_deb()
        elif system == "Windows":
            create_windows_installer()
        elif system == "Darwin":
            create_macos_dmg()
        
        # Always create tarball for portable distribution
        if system != "Linux":
            create_linux_tarball()
    
    # Run build verification
    print("\n" + "="*60)
    print("Running build verification...")
    print("="*60 + "\n")
    
    verify_script = SCRIPT_DIR / "verify_build.py"
    if verify_script.exists():
        result = run_command([sys.executable, str(verify_script)])
        if result != 0:
            print("\n⚠ WARNING: Build verification found issues!")
            print("Review the output above before distributing.")
    else:
        print("⚠ verify_build.py not found, skipping verification")
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                      Build Complete!                         ║
╚══════════════════════════════════════════════════════════════╝

Distribution files are in: {DIST_DIR}

To test the build:
  cd dist/{APP_NAME}
  ./{APP_NAME}

To verify on a clean system, test in a container or VM:
  docker run --rm -v $(pwd)/dist:/dist ubuntu:latest /dist/{APP_NAME}/{APP_NAME}

""")


if __name__ == "__main__":
    main()

