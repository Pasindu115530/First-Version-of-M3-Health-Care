# hook-mediapipe.py
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# Include all mediapipe data files
datas = collect_data_files('mediapipe')
binaries = collect_dynamic_libs('mediapipe')

# Also include OpenCV data files if needed
datas += collect_data_files('cv2')