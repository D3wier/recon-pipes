from setuptools import setup, find_packages

setup(
    name="recon-pipes",
    version="0.1.0",
    description="Composable recon pipeline builder for bug bounty and security testing",
    author="D3wier",
    url="https://github.com/D3wier/recon-pipes",
    packages=find_packages(),
    install_requires=["pyyaml>=6.0"],
    entry_points={
        "console_scripts": [
            "recon-pipes=recon_pipes.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Security",
    ],
)
