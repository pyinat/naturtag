from os.path import abspath
from kivy_deps import sdl2, angle
from kivymd import hooks_path as kivymd_hooks_path
from PyInstaller.compat import is_win, is_linux, is_darwin

PROJECT_NAME = 'naturtag'

# Define platform-specific dependencies
binaries = []
hiddenimports = []
kivy_bins = []
if is_win:
    binaries = [
        # ( 'lib\\exiv2.dll', '.' ),
        # ( 'lib\\exiv2api.pyd', '.' ),
        ('venv\\Lib\\site-packages\\pyexiv2\\lib\\exiv2.dll', '.'),
        ('venv\\Lib\\site-packages\\pyexiv2\\lib\\win64-py37\\exiv2api.pyd', '.'),
    ]
    hiddenimports = ['win32timezone']
    kivy_bins = [Tree(p) for p in (sdl2.dep_bins + angle.dep_bins)]

print(kivy_bins[0])

a = Analysis(
    [f'{PROJECT_NAME}\\app\\app.py'],
    pathex=[abspath('.')],
    binaries=binaries,
    datas=[
        ('assets\\*.png' , 'assets'),
        ('assets\\atlas\\*' , 'assets\\atlas'),
        ('kv\\*.kv', 'kv'),
        ('libs\\garden\\garden.contextmenu\\*', 'kivy_garden\\contextmenu'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[kivymd_hooks_path],
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
    console=True,
)
coll = COLLECT(
    exe,
    Tree(f'{PROJECT_NAME}\\'),
    a.binaries,
    a.zipfiles,
    a.datas,
    *kivy_bins,
    name=PROJECT_NAME,
    strip=False,
    upx=True,
    upx_exclude=[],
)
