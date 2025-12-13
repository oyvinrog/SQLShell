# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SQLShell
Build command: pyinstaller sqlshell.spec
"""

import sys
import os
import re
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# Get the project root directory
SPEC_ROOT = os.path.dirname(os.path.abspath(SPEC))

# Read version from pyproject.toml (single source of truth)
def get_version():
    pyproject_path = os.path.join(SPEC_ROOT, "pyproject.toml")
    with open(pyproject_path, "r") as f:
        content = f.read()
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if match:
        return match.group(1)
    return "0.0.0"

APP_VERSION = get_version()

# Collect data files from various packages
datas = [
    # SQLShell resources
    (os.path.join(SPEC_ROOT, 'sqlshell', 'resources'), 'sqlshell/resources'),
    (os.path.join(SPEC_ROOT, 'sqlshell', 'data'), 'sqlshell/data'),
    # SQLShell utils - include as source files for dynamic imports
    (os.path.join(SPEC_ROOT, 'sqlshell', 'utils'), 'sqlshell/utils'),
    # SQLShell db - include as source files for dynamic imports
    (os.path.join(SPEC_ROOT, 'sqlshell', 'db'), 'sqlshell/db'),
    # SQLShell ui - include as source files for dynamic imports
    (os.path.join(SPEC_ROOT, 'sqlshell', 'ui'), 'sqlshell/ui'),
    # Include pyproject.toml for version reading in frozen builds
    (os.path.join(SPEC_ROOT, 'pyproject.toml'), '.'),
]

# Add sample data (optional - comment out for smaller builds)
if os.path.exists(os.path.join(SPEC_ROOT, 'sample_data')):
    datas.append((os.path.join(SPEC_ROOT, 'sample_data'), 'sample_data'))

# Collect data files from dependencies
datas += collect_data_files('duckdb')
# Note: pyarrow is required by deltalake for Delta table support
datas += collect_data_files('pyarrow')
datas += collect_data_files('deltalake')  # Includes native binaries (_internal.abi3.so)
# Note: XGBoost removed - using scikit-learn RandomForest instead (saves 207MB + 383MB CUDA)
datas += collect_data_files('sklearn')
datas += collect_data_files('nltk')

# Include NLTK data files (punkt tokenizer, stopwords) - required for text encoding features
# NLTK data is typically in ~/nltk_data or system locations
import os
nltk_data_paths = [
    os.path.expanduser('~/nltk_data'),
    '/usr/share/nltk_data',
    '/usr/local/share/nltk_data',
]
for nltk_path in nltk_data_paths:
    if os.path.exists(nltk_path):
        # Include tokenizers (punkt, punkt_tab)
        tokenizers_path = os.path.join(nltk_path, 'tokenizers')
        if os.path.exists(tokenizers_path):
            datas.append((tokenizers_path, 'nltk_data/tokenizers'))
        # Include corpora (stopwords)
        corpora_path = os.path.join(nltk_path, 'corpora')
        if os.path.exists(corpora_path):
            datas.append((corpora_path, 'nltk_data/corpora'))
        break  # Use first available path

# Hidden imports that PyInstaller might miss
hiddenimports = [
    # PyQt6 plugins
    'PyQt6.QtCore',
    'PyQt6.QtGui', 
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    
    # SQLShell modules
    'sqlshell',
    'sqlshell.db',
    'sqlshell.db.database_manager',
    'sqlshell.db.export_manager',
    'sqlshell.ui',
    'sqlshell.ui.filter_header',
    'sqlshell.ui.bar_chart_delegate',
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
    'sqlshell.utils.search_in_df',
    'sqlshell.resources',
    'sqlshell.data',
    'sqlshell.syntax_highlighter',
    'sqlshell.editor',
    'sqlshell.query_tab',
    'sqlshell.styles',
    'sqlshell.menus',
    'sqlshell.table_list',
    'sqlshell.notification_manager',
    'sqlshell.splash_screen',
    'sqlshell.context_suggester',
    'sqlshell.suggester_integration',
    'sqlshell.execution_handler',
    'sqlshell.editor_integration',
    'sqlshell.widgets',
    'sqlshell.create_test_data',
    
    # Data science stack
    'pandas',
    'pandas._libs',
    'pandas._libs.tslibs',
    'numpy',
    'numpy.core',
    'scipy',
    'scipy.stats',
    'scipy.special',
    
    # Database
    'duckdb',
    'sqlite3',
    
    # File formats
    'fastparquet',
    'pyarrow',  # Required by deltalake
    'openpyxl',
    'xlrd',
    'deltalake',
    
    # ML libraries
    'sklearn',
    'sklearn.ensemble',
    'sklearn.preprocessing',
    'sklearn.model_selection',
    # Note: XGBoost removed - using scikit-learn RandomForest instead
    
    # Visualization
    'matplotlib',
    'matplotlib.backends.backend_qt5agg',
    'matplotlib.backends.backend_qtagg',
    'seaborn',
    
    # NLP
    'nltk',
    'nltk.corpus',
    'nltk.tokenize',

    # ML model persistence
    'joblib',  # Used by sklearn and profile_prediction.py

    # AI/LLM (optional - only loaded if user configures API key)
    'openai',

    # System
    'psutil',
]

# Collect all submodules for complex packages
hiddenimports += collect_submodules('pandas')
hiddenimports += collect_submodules('numpy')
hiddenimports += collect_submodules('scipy')
hiddenimports += collect_submodules('sklearn')
hiddenimports += collect_submodules('pyarrow')  # Required by deltalake and pandas
hiddenimports += collect_submodules('PyQt6')

# Binaries to include (platform-specific DLLs/SOs will be auto-detected)
binaries = []

# Collect PyQt6 dynamic libraries (fixes ICU library issues on Linux)
binaries += collect_dynamic_libs('PyQt6')

# On Linux, manually collect ALL Qt6 libraries to prevent missing dependencies
if sys.platform.startswith('linux'):
    import site
    from pathlib import Path
    
    # Find Qt6 library paths in PyQt6 installation
    pyqt6_lib_paths = []
    
    # Method 1: Check PyQt6 package location directly (most reliable)
    try:
        import PyQt6
        pyqt6_pkg_path = Path(PyQt6.__file__).parent / 'Qt6' / 'lib'
        if pyqt6_pkg_path.exists():
            pyqt6_lib_paths.append(pyqt6_pkg_path)
            print(f"[SQLShell Build] Found PyQt6 libs at: {pyqt6_pkg_path}")
    except ImportError:
        print("[SQLShell Build] WARNING: PyQt6 not found during spec file execution")
    
    # Method 2: Check site-packages (fallback)
    for site_dir in site.getsitepackages() + [site.getusersitepackages()]:
        if site_dir:
            pyqt6_path = Path(site_dir) / 'PyQt6' / 'Qt6' / 'lib'
            if pyqt6_path.exists() and pyqt6_path not in pyqt6_lib_paths:
                pyqt6_lib_paths.append(pyqt6_path)
                print(f"[SQLShell Build] Found PyQt6 libs at: {pyqt6_path}")
    
    # Collect ALL .so files from Qt6/lib to ensure nothing is missed
    # This includes ICU, SSL, and other Qt dependencies
    collected_count = 0
    collected_libs = set()  # Track collected libraries to avoid duplicates

    for pyqt6_lib_path in pyqt6_lib_paths:
        # Get all .so and .so.* files - DON'T resolve symlinks, add them as-is
        # PyInstaller will preserve symlinks when we add them directly
        for lib_file in pyqt6_lib_path.glob('*.so*'):
            lib_path = str(lib_file)
            lib_name = lib_file.name
            
            # Skip if already added (avoid duplicates)
            if lib_path in collected_libs:
                continue
            
            # Add to binaries - this will include both symlinks and actual files
            binaries.append((lib_path, '.'))
            collected_libs.add(lib_path)
            collected_count += 1
            
            # Print critical libraries for verification
            if any(x in lib_name for x in ['libicu', 'libQt6', 'libssl', 'libcrypto', 'libEGL']):
                symlink_info = " (symlink)" if lib_file.is_symlink() else ""
                print(f"[SQLShell Build] Adding critical library: {lib_name}{symlink_info}")
    
    if collected_count > 0:
        print(f"[SQLShell Build] Total Qt6 libraries collected: {collected_count}")
    else:
        print("[SQLShell Build] ERROR: No Qt6 libraries found! Build may fail on target systems.")
        print("[SQLShell Build] Please ensure PyQt6 is installed in the build environment.")
    
    # Try to find and bundle system EGL libraries if not already collected
    # libEGL is typically a system library that Qt6 depends on
    import shutil
    egl_paths = [
        '/usr/lib/x86_64-linux-gnu/libEGL.so.1',
        '/usr/lib/libEGL.so.1',
        '/usr/lib64/libEGL.so.1',
    ]
    for egl_path in egl_paths:
        egl_file = Path(egl_path)
        if egl_file.exists() and str(egl_file) not in collected_libs:
            binaries.append((str(egl_file), '.'))
            collected_libs.add(str(egl_file))
            print(f"[SQLShell Build] Found and bundling system EGL library: {egl_path}")
            # Also try to find and bundle related EGL libraries
            egl_dir = egl_file.parent
            for related_lib in egl_dir.glob('libEGL*.so*'):
                if related_lib.is_file() and str(related_lib) not in collected_libs:
                    binaries.append((str(related_lib), '.'))
                    collected_libs.add(str(related_lib))
                    print(f"[SQLShell Build] Bundling EGL-related library: {related_lib.name}")
            break  # Only use first found location

# Note: XGBoost dynamic libraries no longer needed - scikit-learn uses standard NumPy/SciPy libs

# Analysis
a = Analysis(
    [os.path.join(SPEC_ROOT, 'sqlshell', '__main__.py')],
    pathex=[SPEC_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'tcl',
        'tk',
        'test',
        # Note: unittest is needed by sklearn internals (unittest.mock) - don't exclude it
        'pytest',
        'pytest_cov',
        'pytest_xdist',
        'pytest_timeout',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# OPTIMIZATION: Filter out NVIDIA/CUDA libraries even though we removed XGBoost
# In case any other library tries to include them
a.binaries = [
    (name, path, typecode) 
    for name, path, typecode in a.binaries
    if not any(x in name.lower() for x in [
        'cuda', 'cudnn', 'cublas', 'cufft', 'curand', 'cusparse',
        'cusolver', 'nccl', 'nvrtc', 'nvidia', 'nvml'
    ])
]

# Remove duplicate entries
a.datas = list(set(a.datas))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Determine icon path based on platform
if sys.platform == 'win32':
    icon_file = os.path.join(SPEC_ROOT, 'sqlshell', 'resources', 'icon.ico')
    if not os.path.exists(icon_file):
        icon_file = None
elif sys.platform == 'darwin':
    icon_file = os.path.join(SPEC_ROOT, 'sqlshell', 'resources', 'icon.icns')
    if not os.path.exists(icon_file):
        icon_file = None
else:
    icon_file = os.path.join(SPEC_ROOT, 'sqlshell', 'resources', 'icon.png')
    if not os.path.exists(icon_file):
        icon_file = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SQLShell',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SQLShell',
)

# Linux-specific post-build: Set RPATH to find libraries in current directory
if sys.platform.startswith('linux'):
    import os
    import subprocess
    from pathlib import Path

    dist_dir = Path(SPEC_ROOT) / 'dist' / 'SQLShell'
    exe_path = dist_dir / 'SQLShell'

    if exe_path.exists():
        try:
            # Set RPATH to look in the same directory as the executable
            # This allows the binary to find .so files without LD_LIBRARY_PATH
            subprocess.run(['patchelf', '--set-rpath', '$ORIGIN', str(exe_path)], check=True)
            print(f"[SQLShell Build] Set RPATH for: {exe_path}")
        except FileNotFoundError:
            print("[SQLShell Build] WARNING: patchelf not found. Libraries may not be found at runtime.")
            print("[SQLShell Build] Install patchelf: sudo apt-get install patchelf")
        except subprocess.CalledProcessError as e:
            print(f"[SQLShell Build] WARNING: Failed to set RPATH: {e}")
            
        # Verify ICU and EGL libraries are present (symlinks should have been copied by PyInstaller)
        icu_libs = list(dist_dir.glob('libicu*.so*'))
        egl_libs = list(dist_dir.glob('libEGL*.so*'))
        
        if icu_libs:
            print(f"[SQLShell Build] Verified {len(icu_libs)} ICU libraries in dist:")
            for lib in sorted(icu_libs):
                symlink_info = " (symlink)" if lib.is_symlink() else ""
                print(f"  - {lib.name}{symlink_info}")
        else:
            print("[SQLShell Build] ERROR: No ICU libraries found in dist directory!")
            print("[SQLShell Build] The built binary will likely fail to run.")
        
        if egl_libs:
            print(f"[SQLShell Build] Verified {len(egl_libs)} EGL libraries in dist:")
            for lib in sorted(egl_libs):
                symlink_info = " (symlink)" if lib.is_symlink() else ""
                print(f"  - {lib.name}{symlink_info}")
        else:
            print("[SQLShell Build] WARNING: No EGL libraries found in dist directory.")
            print("[SQLShell Build] EGL should be available as system dependency (libegl1).")

# macOS app bundle (only on macOS)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='SQLShell.app',
        icon=icon_file,
        bundle_identifier='com.sqlshell.app',
        info_plist={
            'CFBundleName': 'SQLShell',
            'CFBundleDisplayName': 'SQLShell',
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
        },
    )

