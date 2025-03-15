from setuptools import setup, find_packages
import os

# Read version from __init__.py
with open(os.path.join('sqlshell', '__init__.py'), 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[1].strip().strip('"\'')
            break

setup(
    name="sqlshell",
    version=version,
    packages=find_packages(),
    install_requires=[
        'pandas>=2.0.0',
        'numpy>=1.24.0',
        'PyQt6>=6.4.0',
        'duckdb>=0.9.0',
        'openpyxl>=3.1.0',
        'pyarrow>=14.0.1',
        'fastparquet>=2023.10.1',
        'xlrd>=2.0.1'
    ],
    entry_points={
        'console_scripts': [
            'sqls=sqlshell.main:main',
        ],
    },
    author="SQLShell Team",
    description="A powerful SQL shell with GUI interface for data analysis",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    keywords="sql, data analysis, gui, duckdb",
    url="https://github.com/yourusername/sqlshell",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    include_package_data=True,
    package_data={
        'sqlshell': ['*.db'],
    },
) 