from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('HISTORY.rst') as f:
    history = f.read()

    
setup(name='smc-python',
      version='0.5.8b',
      description='Python based API to Stonesoft Security Management Center',
      long_description=readme + '\n\n' + history,
      url='http://github.com/gabstopper/smc-python',
      author='David LePage',
      author_email='dwlepage70@gmail.com',
      license='Apache 2.0',
      packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
      install_requires=[
        'requests>=2.12.0',
	    'ipaddress'
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
