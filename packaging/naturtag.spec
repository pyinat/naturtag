import glob
import shutil
import sys
from pathlib import Path

from PyInstaller.compat import is_darwin, is_linux, is_win
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

PROJECT_NAME = 'naturtag'
PROJECT_DIR = Path('.').absolute()
ASSETS_DIR = PROJECT_DIR / 'assets'
ICONS_DIR = ASSETS_DIR / 'icons'
ASSETS_DATA_DIR = ASSETS_DIR / 'data'
PACKAGE_DIR = PROJECT_DIR / 'naturtag'

# Detect the active Python environment's site-packages for pyexiv2 binaries
VENV_DIR = Path(sys.prefix)

LIB_DIR_WIN = VENV_DIR / 'Lib' / 'site-packages' / 'pyexiv2' / 'lib'
LIB_DIR_NIX = VENV_DIR / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'pyexiv2' / 'lib'

# Directory for rawpy bundled libraries (sibling to rawpy package)
RAWPY_LIBS_DIR_WIN = VENV_DIR / 'Lib' / 'site-packages' / 'rawpy.libs'
RAWPY_LIBS_DIR_NIX = VENV_DIR / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'rawpy.libs'


def collect_rawpy_libs(lib_dir: Path, file_extension: str) -> list:
    """Collect rawpy bundled libraries using glob patterns

    PyInstaller doesn't expand shell wildcards in binary specs, so we need to
    use glob.glob to find matching files and return them as individual entries.

    Note: Versioned libraries use patterns like 'libraw_r*.so.*' to match
    files with version suffixes (e.g., libraw_r.so.24.0.0)
    """
    if not lib_dir.exists():
        return []

    # Collect libraries matching the required patterns
    # Use .* pattern to match version suffixes like .24.0.0
    patterns = [
        f'libraw_r*.{file_extension}.*',  # Main LibRaw library
        f'liblcms2*.{file_extension}.*',  # Color management
        f'libjpeg*.{file_extension}.*',  # JPEG support
        f'libjasper*.{file_extension}.*',  # JPEG-2000 support
        f'libgomp*.{file_extension}.*',  # GCC OpenMP runtime
    ]

    collected = []
    for pattern in patterns:
        matched_files = glob.glob(str(lib_dir / pattern))
        for matched_file in matched_files:
            collected.append((matched_file, 'rawpy.libs'))

    if not collected:
        print(f'WARNING: No rawpy libraries found in {lib_dir}')
        print('RAW image support will not work in packaged executable')

    return collected


binaries = []
datas = [
    (str(ICONS_DIR / '*.ico'), 'assets/icons'),
    (str(ICONS_DIR / '*.png'), 'assets/icons'),
    (str(ASSETS_DATA_DIR / '*.json'), 'assets/data'),
    (str(ASSETS_DATA_DIR / '*.qss'), 'assets/data'),
    (str(ASSETS_DATA_DIR / '*.tar.gz'), 'assets/data'),
]

# Define platform-specific dependencies
if is_win:
    binaries = [
        (str(LIB_DIR_WIN / 'exiv2.dll'), 'pyexiv2/lib'),
        (str(LIB_DIR_WIN / 'exiv2api.pyd'), 'pyexiv2/lib'),
    ]
    # Bundle rawpy's bundled LibRaw libraries
    binaries += collect_rawpy_libs(RAWPY_LIBS_DIR_WIN, 'dll')
elif is_darwin:
    binaries = [
        (str(LIB_DIR_NIX / 'libexiv2.dylib'), 'pyexiv2/lib'),
        (str(LIB_DIR_NIX / 'exiv2api.so'), 'pyexiv2/lib'),
    ]
    # Bundle rawpy's bundled LibRaw libraries
    binaries += collect_rawpy_libs(RAWPY_LIBS_DIR_NIX, 'dylib')
elif is_linux:
    # pyexiv2/lib/__init__.py loads libexiv2.so by path (via ctypes.CDLL), then imports
    # exiv2api.so which has a dynamic dependency on libexiv2.so.28 (its SONAME). Both
    # names must exist in the same directory so the dynamic linker resolves the SONAME.
    _libexiv2_soname = LIB_DIR_NIX / 'libexiv2.so.28'
    shutil.copy2(str(LIB_DIR_NIX / 'libexiv2.so'), str(_libexiv2_soname))
    binaries = [
        (str(LIB_DIR_NIX / 'libexiv2.so'), 'pyexiv2/lib'),
        (str(_libexiv2_soname), 'pyexiv2/lib'),
        (str(LIB_DIR_NIX / 'exiv2api.so'), 'pyexiv2/lib'),
    ]
    # Bundle rawpy's bundled LibRaw libraries
    binaries += collect_rawpy_libs(RAWPY_LIBS_DIR_NIX, 'so')
else:
    raise NotImplementedError

# Ensure package metadata is available for importlib.metadata
datas += copy_metadata('naturtag')
datas += copy_metadata('pyinaturalist')
datas += collect_data_files('pyinaturalist_convert', include_py_files=True)

a = Analysis(
    [str(PACKAGE_DIR / 'app' / 'app.py')],
    pathex=[str(PROJECT_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports = [],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    [],
    icon=str(ICONS_DIR / 'logo.ico'),
    exclude_binaries=True,
    name=PROJECT_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=PROJECT_NAME,
    strip=False,
    upx=True,
    upx_exclude=[],
)
app = BUNDLE(
    coll,
    name=f'{PROJECT_NAME}.app',
    icon=str(ICONS_DIR / 'logo.icns'),
    bundle_identifier='org.pyinat.naturtag',
)
