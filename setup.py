from setuptools import setup, find_packages

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='westerparse',
    version='1.0.3-alpha',
    description='An application for evaluating Westergaardian species counterpoint',
    long_description=long_description,
    long_description_content_type='text/markdown', 
    url='https://github.com/snarrenberg/westerparse',
    author='Robert Snarrenberg',
    author_email='snarrenberg@wustl.edu',
    classifiers = ['Programming Language :: Python :: 3',
                   'Operating System :: OS Independent',
                   'License :: OSI Approved :: BSD License',
    ],
    package_dir={'': 'src'},
    packages=find_packages(where='src'), 
    python_requires='>=3.5, <4',
    install_requires=['music21'],
    #dependency_links['https://github.com/cuthbertLab/music21']
)