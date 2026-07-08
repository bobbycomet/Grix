from setuptools import setup, find_packages

setup(
    name="grix",
    version="0.1.0",
    description="Grix: a friendly Linux system troubleshooter and learning companion",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "grix": [
            "assets/*.png",
            "plugins/*/plugin.json",
            "plugins/*/plugin.py",
        ],
    },
    install_requires=[
        "PyQt6>=6.6.0",
    ],
    entry_points={
        "console_scripts": [
            "grix=grix.main:main",
        ],
    },
    python_requires=">=3.10",
)
