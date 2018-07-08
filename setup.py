import os
from setuptools import setup, find_packages
from codecs import open

here = os.path.abspath(os.path.dirname(__file__))

about = {}
with open(os.path.join(here, 'smc', '__version__.py'), 'r', 'utf-8') as f:
    exec(f.read(), about)
        
if '__version__' not in about:
    raise RuntimeError('Cannot find version information')

with open('README.rst', encoding='utf-8') as f:
    readme = f.read()
    
with open('HISTORY.rst', encoding='utf-8') as f:
    history = f.read()

    
setup(name='smc-python',
      #version='0.6.1',
      version=about['__version__'],
      description=about['__description__'],
      long_description=readme + '\n\n' + history,
      url=about['__url__'],
      author=about['__author__'],
      author_email=about['__author_email__'],
      license=about['__license__'],
      packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
      install_requires=[
        'requests>=2.12.0'
      ],
      include_package_data=True,
      classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License"
        ],
      zip_safe=False)
