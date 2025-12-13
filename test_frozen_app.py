#!/usr/bin/env python3
"""
Test script to identify potential runtime issues in frozen/bundled applications.
Run this BEFORE building to catch dependency issues that PyInstaller might introduce.

This simulates what happens when the app is frozen and tests all critical imports.
"""

import sys
import importlib
import warnings

def test_critical_imports():
    """Test all imports that the application needs."""
    
    critical_modules = [
        # Core GUI
        ('PyQt6.QtWidgets', True),
        ('PyQt6.QtCore', True),
        ('PyQt6.QtGui', True),
        
        # Data processing
        ('pandas', True),
        ('numpy', True),
        ('duckdb', True),
        
        # File formats (fastparquet NOT pyarrow)
        ('fastparquet', True),
        ('openpyxl', True),
        ('xlrd', True),
        ('deltalake', True),
        
        # ML/Stats
        ('sklearn', True),
        ('scipy', True),
        ('matplotlib', True),
        ('seaborn', True),
        
        # NLP
        ('nltk', True),
        
        # Optional
        ('openai', False),
        
        # Should NOT be imported
        ('pyarrow', None),  # None means should NOT exist
    ]
    
    print("=" * 70)
    print("Testing Critical Imports")
    print("=" * 70)
    
    failed = []
    warnings_list = []
    
    for module_name, required in critical_modules:
        try:
            if required is None:
                # This module should NOT be importable
                try:
                    mod = importlib.import_module(module_name)
                    warnings_list.append(f"⚠️  {module_name:20} Should NOT be present but IS installed!")
                except ImportError:
                    print(f"✓ {module_name:20} Correctly excluded")
            else:
                mod = importlib.import_module(module_name)
                
                # Try to get version if available
                version = "?"
                for attr in ['__version__', 'VERSION', 'version']:
                    if hasattr(mod, attr):
                        version = getattr(mod, attr)
                        break
                
                print(f"✓ {module_name:20} {version}")
        except ImportError as e:
            if required:
                failed.append(f"✗ {module_name:20} MISSING (required)")
                print(f"✗ {module_name:20} MISSING")
            else:
                print(f"○ {module_name:20} Not installed (optional)")
        except Exception as e:
            failed.append(f"✗ {module_name:20} ERROR: {e}")
            print(f"✗ {module_name:20} ERROR: {e}")
    
    return failed, warnings_list


def test_pyinstaller_hooks():
    """Check for problematic PyInstaller runtime hooks."""
    print("\n" + "=" * 70)
    print("Checking PyInstaller Runtime Hooks")
    print("=" * 70)
    
    issues = []
    
    # Check if pyarrow is referenced anywhere in installed packages
    try:
        import site
        from pathlib import Path
        
        for site_dir in site.getsitepackages():
            pyinstaller_hooks = Path(site_dir) / 'PyInstaller' / 'hooks'
            if pyinstaller_hooks.exists():
                # Check for hooks that might reference pyarrow
                problem_hooks = []
                for hook_file in pyinstaller_hooks.glob('*.py'):
                    try:
                        content = hook_file.read_text()
                        if 'pyarrow' in content.lower():
                            problem_hooks.append(hook_file.name)
                    except:
                        pass
                
                if problem_hooks:
                    print(f"⚠️  Found PyInstaller hooks mentioning pyarrow:")
                    for hook in problem_hooks:
                        print(f"    - {hook}")
                    issues.append("PyInstaller hooks reference pyarrow")
                else:
                    print("✓ No problematic PyInstaller hooks found")
    except Exception as e:
        print(f"⚠️  Could not check hooks: {e}")
    
    return issues


def test_nltk_data():
    """Check if NLTK data is available."""
    print("\n" + "=" * 70)
    print("Checking NLTK Data")
    print("=" * 70)
    
    try:
        import nltk
        
        required_data = [
            ('tokenizers/punkt', 'punkt'),
            ('tokenizers/punkt_tab', 'punkt_tab'),
            ('corpora/stopwords', 'stopwords'),
        ]
        
        missing = []
        for path, name in required_data:
            try:
                nltk.data.find(path)
                print(f"✓ NLTK data: {name}")
            except LookupError:
                print(f"✗ NLTK data: {name} MISSING")
                missing.append(name)
        
        if missing:
            print(f"\n⚠️  Missing NLTK data will be downloaded at runtime")
            return [f"Missing NLTK data: {', '.join(missing)}"]
        
    except Exception as e:
        print(f"✗ Error checking NLTK: {e}")
        return [f"NLTK check failed: {e}"]
    
    return []


def test_qt_dependencies():
    """Check Qt dependencies on Linux."""
    print("\n" + "=" * 70)
    print("Checking Qt Dependencies")
    print("=" * 70)
    
    if sys.platform.startswith('linux'):
        try:
            import PyQt6
            from pathlib import Path
            
            qt_lib_path = Path(PyQt6.__file__).parent / 'Qt6' / 'lib'
            
            if not qt_lib_path.exists():
                print(f"✗ Qt6 lib directory not found: {qt_lib_path}")
                return ["Qt6 libraries not found"]
            
            # Check for ICU libraries
            icu_libs = ['libicudata.so', 'libicui18n.so', 'libicuuc.so']
            missing_icu = []
            
            for icu_lib in icu_libs:
                found = list(qt_lib_path.glob(f"{icu_lib}*"))
                if found:
                    print(f"✓ {icu_lib:20} Found: {found[0].name}")
                else:
                    print(f"✗ {icu_lib:20} MISSING")
                    missing_icu.append(icu_lib)
            
            if missing_icu:
                return [f"Missing ICU libraries: {', '.join(missing_icu)}"]
            
        except Exception as e:
            print(f"✗ Error checking Qt: {e}")
            return [f"Qt check failed: {e}"]
    else:
        print(f"○ Skipping (not Linux)")
    
    return []


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          SQLShell Pre-Build Dependency Check                      ║
║  Run this BEFORE building to catch potential runtime issues      ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    all_issues = []
    all_warnings = []
    
    # Run all tests
    failed, warnings_list = test_critical_imports()
    all_issues.extend(failed)
    all_warnings.extend(warnings_list)
    
    hook_issues = test_pyinstaller_hooks()
    all_issues.extend(hook_issues)
    
    nltk_issues = test_nltk_data()
    all_warnings.extend(nltk_issues)
    
    qt_issues = test_qt_dependencies()
    all_issues.extend(qt_issues)
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    if all_warnings:
        print("\n⚠️  WARNINGS:")
        for warning in all_warnings:
            print(f"  - {warning}")
    
    if all_issues:
        print("\n❌ CRITICAL ISSUES FOUND:")
        for issue in all_issues:
            print(f"  - {issue}")
        print("\n🛑 DO NOT BUILD until these issues are resolved!")
        print("   The built application WILL FAIL at runtime.")
        return 1
    else:
        print("\n✅ All critical checks passed!")
        if all_warnings:
            print("   Review warnings above, but safe to build.")
        else:
            print("   Safe to proceed with build.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
