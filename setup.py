from setuptools import setup, find_packages

setup(
    name = "insighta",
    version = "1.0.0",
    packages = find_packages(),
    install_requires= [
        "click",
        "requests",
        "rich",
    ],
    entry_points = {
        "console_scripts": [
            "insighta=insighta.main:cli",
        ],
    },
    python_requires = ">=3.10",
    author = "Chimereya",
    description = "CLI tool for Insighta Labs+ Profile Intelligence System",
)