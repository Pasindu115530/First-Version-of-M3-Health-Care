# build.spec
import os
import sys
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller import __main__ as pyi

# Collect all data files from mediapipe and other packages
mediapipe_datas = collect_data_files('mediapipe')
opencv_datas = collect_data_files('cv2')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],  # Add current directory to path
    binaries=[],
    datas=[
        # Include mediapipe data files
        *mediapipe_datas,
        *opencv_datas,
        
        # Include your project folders
        ('gui/', 'gui'),
        ('core/', 'core'),
        ('utils/', 'utils'),
    ],
    hiddenimports=[
        'mediapipe',
        'cv2',
        'numpy',
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        'PyQt5.QtMultimedia',
        'PyQt5.QtMultimediaWidgets',
        'psutil',
        'sys',
        'os',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SafeWarner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress the executable (set to False if issues)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True if you need console window for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # You can add an icon file here later
)