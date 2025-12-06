#!/usr/bin/env python3
"""
Version Bump Script for SQLShell

This script manages version numbers across the project. It updates:
- pyproject.toml (the single source of truth)
- installer/linux/create_installer.sh
- installer/windows/sqlshell_inno.iss

All other files (build.py, sqlshell/__init__.py, sqlshell.spec) read the version
dynamically from pyproject.toml, so they don't need updating.

Usage:
    python bump_version.py                    # Show current version
    python bump_version.py 0.4.0             # Set specific version
    python bump_version.py --patch           # Bump patch: 0.3.3 -> 0.3.4
    python bump_version.py --minor           # Bump minor: 0.3.3 -> 0.4.0
    python bump_version.py --major           # Bump major: 0.3.3 -> 1.0.0
"""

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()

# Files that need manual version updates (can't read dynamically)
VERSION_FILES = {
    "pyproject.toml": {
        "pattern": r'^(version\s*=\s*["\'])([^"\']+)(["\'])',
        "flags": re.MULTILINE,
    },
    "installer/linux/create_installer.sh": {
        "pattern": r'^(APP_VERSION=")([^"]+)(")',
        "flags": re.MULTILINE,
    },
    "installer/windows/sqlshell_inno.iss": {
        "pattern": r'^(#define MyAppVersion ")([^"]+)(")',
        "flags": re.MULTILINE,
    },
}


def get_current_version() -> str:
    """Read current version from pyproject.toml."""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    content = pyproject.read_text()
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if match:
        return match.group(1)
    raise ValueError("Could not find version in pyproject.toml")


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse version string into (major, minor, patch)."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(current: str, bump_type: str) -> str:
    """Bump version based on type (major, minor, patch)."""
    major, minor, patch = parse_version(current)
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def update_file(filepath: Path, pattern: str, new_version: str, flags: int) -> bool:
    """Update version in a single file."""
    if not filepath.exists():
        print(f"  ⚠️  Skipped (file not found): {filepath.relative_to(PROJECT_ROOT)}")
        return False
    
    content = filepath.read_text()
    
    def replacer(match):
        return f"{match.group(1)}{new_version}{match.group(3)}"
    
    new_content, count = re.subn(pattern, replacer, content, flags=flags)
    
    if count == 0:
        print(f"  ⚠️  No match found in: {filepath.relative_to(PROJECT_ROOT)}")
        return False
    
    filepath.write_text(new_content)
    print(f"  ✅ Updated: {filepath.relative_to(PROJECT_ROOT)}")
    return True


def update_all_versions(new_version: str) -> None:
    """Update version in all version files."""
    print(f"\n📝 Updating version to {new_version}...\n")
    
    success_count = 0
    for relative_path, config in VERSION_FILES.items():
        filepath = PROJECT_ROOT / relative_path
        if update_file(filepath, config["pattern"], new_version, config["flags"]):
            success_count += 1
    
    print(f"\n✅ Updated {success_count}/{len(VERSION_FILES)} files")
    
    # Show files that read dynamically
    print("\n📖 These files read version dynamically (no update needed):")
    print("  • sqlshell/__init__.py")
    print("  • build.py")
    print("  • sqlshell.spec")


def main():
    parser = argparse.ArgumentParser(
        description="Manage SQLShell version numbers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="New version number (e.g., 0.4.0)"
    )
    parser.add_argument(
        "--major",
        action="store_true",
        help="Bump major version (X.0.0)"
    )
    parser.add_argument(
        "--minor",
        action="store_true",
        help="Bump minor version (0.X.0)"
    )
    parser.add_argument(
        "--patch",
        action="store_true",
        help="Bump patch version (0.0.X)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    
    args = parser.parse_args()
    
    current_version = get_current_version()
    
    # Count how many bump flags are set
    bump_flags = sum([args.major, args.minor, args.patch])
    
    if args.version and bump_flags > 0:
        print("Error: Cannot specify both a version and a bump flag")
        sys.exit(1)
    
    if bump_flags > 1:
        print("Error: Can only specify one of --major, --minor, --patch")
        sys.exit(1)
    
    # Determine new version
    if args.version:
        # Validate version format
        try:
            parse_version(args.version)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        new_version = args.version
    elif args.major:
        new_version = bump_version(current_version, "major")
    elif args.minor:
        new_version = bump_version(current_version, "minor")
    elif args.patch:
        new_version = bump_version(current_version, "patch")
    else:
        # No version specified, just show current
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                  SQLShell Version Manager                    ║
╚══════════════════════════════════════════════════════════════╝

Current version: {current_version}

Usage:
    python bump_version.py 0.4.0      # Set specific version
    python bump_version.py --patch    # {current_version} → {bump_version(current_version, "patch")}
    python bump_version.py --minor    # {current_version} → {bump_version(current_version, "minor")}
    python bump_version.py --major    # {current_version} → {bump_version(current_version, "major")}

Files that will be updated:
    • pyproject.toml (source of truth)
    • installer/linux/create_installer.sh
    • installer/windows/sqlshell_inno.iss

Files that read version dynamically (auto-updated):
    • sqlshell/__init__.py
    • build.py  
    • sqlshell.spec
""")
        return
    
    if args.dry_run:
        print(f"\n🔍 Dry run: Would update {current_version} → {new_version}")
        print("\nFiles that would be updated:")
        for relative_path in VERSION_FILES:
            filepath = PROJECT_ROOT / relative_path
            if filepath.exists():
                print(f"  • {relative_path}")
        return
    
    print(f"Version: {current_version} → {new_version}")
    update_all_versions(new_version)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    Version Updated!                          ║
╚══════════════════════════════════════════════════════════════╝

New version: {new_version}

Next steps:
  1. Review the changes: git diff
  2. Commit: git commit -am "Bump version to {new_version}"
  3. Tag: git tag v{new_version}
  4. Build: python build.py --installer
""")


if __name__ == "__main__":
    main()

