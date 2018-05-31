"""A setuptools based setup module for the pywot project

"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pywot',
    version='0.1',
    description='A Pythonic wrapper around the `webthing` module from Mozilla',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/twobraids/pywot',
    author='K Lars Lohn',
    author_email='twobraids@gmail.com',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Home Automation',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='web of things, internet of things',

    packages=find_packages(exclude=['pywot']),
    install_requires=['configman', 'webthing>=0.6'],

    project_urls={
        'Source': 'https://github.com/twobraids/pywot/',
    },
)
