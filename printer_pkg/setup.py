from setuptools import setup, find_packages

setup(
    name="printer_pkg",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pywin32"
    ],
    author="Zhazhalove",
    description="A package for abstract printer handling and Dymo printer implementation",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.10",
)
