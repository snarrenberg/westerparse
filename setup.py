import setuptools

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="westerparse-pkg-snarrenberg", # Replace with your own username
    version="1.0.1-alpha",
    author="Robert Snarrenberg",
    author_email="snarrenberg@wustl.edu",
    description="An application for evaluating Westergaardian species counterpoint",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/snarrenberg/WesterParse",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        'music21',
        ],
)