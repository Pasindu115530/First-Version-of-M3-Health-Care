# build.py
import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    'main.py',
    '--name=SafeWarner',
    '--onefile',
    '--windowed',
    '--add-data=gui;gui',
    '--add-data=core;core', 
    '--add-data=utils;utils',
    '--hidden-import=PyQt5.QtCore',
    '--hidden-import=PyQt5.QtGui',
    '--hidden-import=PyQt5.QtWidgets',
    '--hidden-import=mediapipe',
    '--hidden-import=cv2',
    '--hidden-import=numpy',
    '--hidden-import=psutil',
    '--clean'
])