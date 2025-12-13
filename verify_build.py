#!/usr/bin/env python3
"""
Verify that the SQLShell build includes all necessary dependencies.
Run this after building to ensure the executable will work on target systems.

Usage:
    python verify_build.py
"""

import sys
from pathlib import Path

def verify_build():
    """Verify the build contains all required libraries."""
    
    print("=" * 70)
    print("SQLShell Build Verification")
    print("=" * 70)
    
    # Check if dist directory exists
    dist_dir = Path(__file__).parent / "dist" / "SQLShell"
    if not dist_dir.exists():
        print(f"❌ ERROR: Build directory not found: {dist_dir}")
        print("   Please run 'python build.py' first.")
        return False
    
    print(f"✓ Build directory found: {dist_dir}")
    
    # Required files/patterns to check
    required_checks = [
        ("SQLShell executable", ["SQLShell"], True),
        ("Python libraries", ["_internal", "lib"], False),
    ]
    
    # Critical libraries for Linux
    if sys.platform.startswith('linux'):
        critical_libs = [
            ("ICU Data library", "libicudata.so"),
            ("ICU i18n library", "libicui18n.so"),
            ("ICU UC library", "libicuuc.so"),
        ]
        
        print("\n" + "=" * 70)
        print("Checking Critical Qt6 Dependencies (Linux)")
        print("=" * 70)
        
        all_libs_found = True
        for lib_name, lib_pattern in critical_libs:
            # Search recursively for the library
            found_files = list(dist_dir.rglob(f"{lib_pattern}*"))
            
            if found_files:
                print(f"✓ {lib_name:30} Found: {found_files[0].name}")
            else:
                print(f"❌ {lib_name:30} MISSING!")
                all_libs_found = False
        
        if not all_libs_found:
            print("\n❌ CRITICAL: Some required libraries are missing!")
            print("   The executable may fail with 'cannot open shared object file' errors.")
            print("   Please rebuild with the updated sqlshell.spec file.")
            return False
    
    # Check for common Qt6 plugins
    print("\n" + "=" * 70)
    print("Checking Qt6 Plugins")
    print("=" * 70)
    
    qt_plugin_dirs = ["platforms", "platformthemes", "xcbglintegrations"]
    for plugin_dir in qt_plugin_dirs:
        plugin_paths = list(dist_dir.rglob(plugin_dir))
        if plugin_paths:
            plugin_files = list(plugin_paths[0].glob("*.so"))
            print(f"✓ {plugin_dir:20} Found: {len(plugin_files)} plugins")
        else:
            print(f"⚠ {plugin_dir:20} Not found (may be optional)")
    
    # Check executable size
    print("\n" + "=" * 70)
    print("Build Statistics")
    print("=" * 70)
    
    exe_path = dist_dir / "SQLShell"
    if exe_path.exists():
        exe_size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"Executable size: {exe_size_mb:.1f} MB")
    
    # Calculate total directory size
    total_size = sum(f.stat().st_size for f in dist_dir.rglob('*') if f.is_file())
    total_size_mb = total_size / (1024 * 1024)
    print(f"Total build size: {total_size_mb:.1f} MB")
    
    # Count total files
    total_files = sum(1 for f in dist_dir.rglob('*') if f.is_file())
    print(f"Total files: {total_files}")
    
    print("\n" + "=" * 70)
    print("✓ Build verification completed successfully!")
    print("=" * 70)
    print("\nRecommended tests before distribution:")
    print("  1. Test the executable on the build system:")
    print(f"     cd {dist_dir}")
    print("     ./SQLShell")
    print("  2. Test on a clean system (VM or container) to verify all dependencies")
    print("  3. Check console output for any library loading warnings")
    
    return True


if __name__ == "__main__":
    success = verify_build()
    sys.exit(0 if success else 1)
