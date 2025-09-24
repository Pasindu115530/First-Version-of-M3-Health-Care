# setup.py
from setuptools import setup, find_packages

setup(
    name="safe_warner",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt5>=5.15.0",
        "opencv-python>=4.5.0", 
        "numpy>=1.21.0",
        "psutil>=5.8.0",
        "mediapipe>=0.10.0",  # Add this line
    ],
    extras_require={
        'windows': ['pywin32>=300'],
    },
    python_requires=">=3.7",
)