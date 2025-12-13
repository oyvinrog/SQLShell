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
# Note: Using fastparquet instead of pyarrow (saves 147MB)
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
    
    # System
    'psutil',
]

# Collect all submodules for complex packages
hiddenimports += collect_submodules('pandas')
hiddenimports += collect_submodules('numpy')
hiddenimports += collect_submodules('scipy')
hiddenimports += collect_submodules('sklearn')
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
    for pyqt6_lib_path in pyqt6_lib_paths:
        # Get all .so and .so.* files
        for lib_file in pyqt6_lib_path.glob('*.so*'):
            if lib_file.is_file() and not lib_file.is_symlink():
                binaries.append((str(lib_file), '.'))
                collected_count += 1
                # Print critical libraries for verification
                if any(x in lib_file.name for x in ['libicu', 'libQt6', 'libssl', 'libcrypto']):
                    print(f"[SQLShell Build] Adding critical library: {lib_file.name}")
    
    if collected_count > 0:
        print(f"[SQLShell Build] Total Qt6 libraries collected: {collected_count}")
    else:
        print("[SQLShell Build] ERROR: No Qt6 libraries found! Build may fail on target systems.")
        print("[SQLShell Build] Please ensure PyQt6 is installed in the build environment.")

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
        # Note: Do NOT exclude pyarrow - deltalake requires it
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

