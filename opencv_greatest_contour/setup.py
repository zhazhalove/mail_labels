from setuptools import setup, find_packages

setup(
    name="opencv_greatest_contour",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "opencv-python",
        "numpy",
        "Pillow",
        "PyMuPDF",
    ],
    author="Your Name",
    description="A package to extract and highlight the largest contour in a PDF converted to an image",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
)
