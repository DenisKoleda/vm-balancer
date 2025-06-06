#!/usr/bin/env python3
"""
Setup script for VM Balancer package
"""

import os

from setuptools import find_packages, setup

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()


# Read requirements from requirements.txt
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


setup(
    name="vm-balancer",
    version="2.0.1",
    author="Denis Koleda",
    author_email="deniskoleda6@gmail.com",
    description="Intelligent auto-balancer for VMManager 6 virtual machines",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DenisKoleda/vm-balancer",
    project_urls={
        "Bug Tracker": "https://github.com/DenisKoleda/vm-balancer/issues",
        "Documentation": "https://vm-balancer.readthedocs.io/",
        "Source Code": "https://github.com/DenisKoleda/vm-balancer",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Clustering",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "isort>=5.10.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vm-balancer=vm_balancer.main:main",
        ],
    },
    keywords="vmmanager virtualization load-balancing cluster automation",
    include_package_data=True,
    zip_safe=False,
)
