from setuptools import setup, find_packages
from pathlib import Path

this_dir = Path(__file__).parent
readme = (this_dir / "README.md").read_text(encoding="utf-8") if (this_dir / "README.md").exists() else ""

setup(
    name="fnctl",
    version="0.1.2",
    description="Self-hosted functions (Lambda-like) runtime and CLI",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Vedant M",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "fnctl": [
            "templates/python/main.py",
        ]
    },
    entry_points={
        "console_scripts": [
            "fnctl=fnctl.cli:main",
        ]
    },
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: System :: Systems Administration",
    ],
)
