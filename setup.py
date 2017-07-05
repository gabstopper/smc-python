from setuptools import setup, find_packages

def readme():
    with open('README.rst') as f:
        return f.read()
    
setup(name='smc-python',
      version='0.5.5',
      description='Python based API to Stonesoft Security Management Center',
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
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5"
        ],
      zip_safe=False)
