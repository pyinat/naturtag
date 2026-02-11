from pathlib import Path

from PyInstaller.compat import is_darwin, is_linux, is_win
from PyInstaller.utils.hooks import copy_metadata

BUILD_PY_VERSION = '3.14'
PROJECT_NAME = 'naturtag'
PROJECT_DIR = Path('.').absolute()
ASSETS_DIR = PROJECT_DIR / 'assets'
ICONS_DIR = ASSETS_DIR / 'icons'
ASSETS_DATA_DIR = ASSETS_DIR / 'data'
PACKAGE_DIR = PROJECT_DIR / 'naturtag'

LOCAL_VENV_DIR = Path('~/.virtualenvs/naturtag').expanduser().absolute()
CI_VENV_DIR = PROJECT_DIR / '.venv'
VENV_DIR = CI_VENV_DIR if CI_VENV_DIR.is_dir() else LOCAL_VENV_DIR

LIB_DIR_WIN = VENV_DIR / 'Lib' / 'site-packages' / 'pyexiv2' / 'lib'
LIB_DIR_NIX = VENV_DIR / 'lib' / f'python{BUILD_PY_VERSION}' / 'site-packages' / 'pyexiv2' / 'lib'

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
        (str(LIB_DIR_WIN / 'exiv2.dll'), '.'),
        (str(LIB_DIR_WIN / 'exiv2api.pyd'), '.'),
    ]
elif is_darwin:
    binaries = [
        (str(LIB_DIR_NIX / 'libexiv2.dylib'), '.'),
        (str(LIB_DIR_NIX / 'exiv2api.so'), '.'),
    ]
elif is_linux:
    binaries = [
        (str(LIB_DIR_NIX / 'libexiv2.so'), '.'),
        (str(LIB_DIR_NIX / 'exiv2api.so'), '.'),
    ]
else:
    raise NotImplementedError

# Ensure package metadata is available for importlib.metadata
datas += copy_metadata('naturtag')

a = Analysis(
    [str(PACKAGE_DIR / 'app' / 'app.py')],
    pathex=[str(PROJECT_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports = [],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['**/__pycache__', PROJECT_DIR / 'coverage', PACKAGE_DIR / 'py.typed'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
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
    Tree(f'{PROJECT_NAME}/'),
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
