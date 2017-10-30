import os
import re
from io import open
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

# Version extraction inspired from 'requests'
with open(os.path.join(here, 'version.py'), 'r') as fd:
    version = re.search(r'^VERSION\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('Cannot find version information')

with open('README.rst', encoding='utf-8') as f:
    readme = f.read()
    
with open('HISTORY.rst', encoding='utf-8') as f:
    history = f.read()
    
setup(
    name='smc-python-monitoring',
    version=version,
    description='Stonesoft Management Cetner Monitoring',
    long_description=readme + '\n\n' + history,
    license='Apache License',
    author='David LePage',
    author_email='dwlepage70@gmail.com',
    url='https://github.com/gabstopper/smc-python',
    #packages=['smc_monitoring'],
    packages=find_packages(),
    #namespace_packages=['smc_monitoring'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License"
        ],
    zip_safe=False,
    install_requires=[
        'smc-python >=0.5.6',
        'websocket-client'
    ],
)
