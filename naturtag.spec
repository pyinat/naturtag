from pathlib import Path

from PyInstaller.compat import is_darwin, is_linux, is_win

BUILD_PY_VERSION = '3.10'
PROJECT_NAME = 'naturtag'
PROJECT_DIR = Path('.').absolute()
ASSETS_DIR = PROJECT_DIR / 'assets'
PACKAGE_DIR = PROJECT_DIR / 'naturtag'
# LIB_DIR = PROJECT_DIR / 'lib'

LOCAL_VENV_DIR = Path('~/.virtualenvs/naturtag').expanduser().absolute()
CI_VENV_DIR = PROJECT_DIR / '.venv'
VENV_DIR = CI_VENV_DIR if CI_VENV_DIR.is_dir() else LOCAL_VENV_DIR

LIB_DIR_WIN = VENV_DIR / 'Lib' / 'site-packages' / 'pyexiv2' / 'lib'
LIB_DIR_NIX = VENV_DIR / 'lib' / f'python{BUILD_PY_VERSION}' / 'site-packages' / 'pyexiv2' / 'lib'

# Define platform-specific dependencies
binaries = []
hiddenimports = []
if is_win:
    binaries = [
        (str(LIB_DIR_WIN / 'exiv2.dll'), '.'),
        (str(LIB_DIR_WIN / f'py{BUILD_PY_VERSION}-win' / 'exiv2api.pyd'), '.'),
    ]
    hiddenimports = ['win32timezone']
elif is_darwin:
    binaries = [
        (str(LIB_DIR_NIX / 'libexiv2.dylib'), '.'),
        (str(LIB_DIR_NIX / f'py{BUILD_PY_VERSION}-darwin' / 'exiv2api.so'), '.'),
    ]
elif is_linux:
    binaries = [
        (str(LIB_DIR_NIX / 'libexiv2.so'), '.'),
        (str(LIB_DIR_NIX / f'py{BUILD_PY_VERSION}-linux' / 'exiv2api.so'), '.'),
    ]
else:
    raise NotImplementedError

a = Analysis(
    [str(PACKAGE_DIR / 'app' / 'app.py')],
    pathex=[str(PROJECT_DIR)],
    binaries=binaries,
    datas=[
        (str(ASSETS_DIR / '*.png'), 'assets'),
        (str(ASSETS_DIR / '*.qss'), 'assets'),
        (str(ASSETS_DIR / '*.tar.gz'), 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[PROJECT_DIR / 'coverage'],
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
