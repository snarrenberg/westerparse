from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'README.rst').read_text(encoding='utf-8')

setup(
    name='westerparse-pkg-snarrenberg',
    version='1.0.1-alpha',
    description='An application for evaluating Westergaardian species counterpoint',
    long_description=long_description,
    long_description_content_type='text/x-rst', 
    url='https://github.com/snarrenberg/westerparse',
    author='Robert Snarrenberg',
    author_email='snarrenberg@wustl.edu',
    classifiers = ['Programming Language :: Python :: 3',
                   'Operating System :: OS Independent'
                   'License :: OSI Approved :: BSD-3-Clause or LGPL',
    ],
    package_dir={'': 'src'},
    packages=find_packages(where='src'), 
    python_requires='>=3.5, <4',
    install_requires=['music21'],
    #dependency_links['https://github.com/cuthbertLab/music21']
)