from setuptools import setup

from smc import __version__
def readme():
    with open('README.rst') as f:
        return f.read()
    
setup(name='smc-python',
      version=__version__,
      description='Python based API to Stonesoft Security Management Center',
      url='http://github.com/gabstopper/smc-python',
      author='David LePage',
      author_email='dwlepage70@gmail.com',
      license='Apache 2.0',
      packages=['smc', 'smc.actions', 'smc.api', 'smc.elements', 'smc.core', 
                'smc.policy', 'smc.routing', 'smc.administration', 'smc.vpn',
                'smc.base'],
      install_requires=[
          'requests'
      ],
      include_package_data=True,
      classifiers=[
        "Programming Language :: Python :: 2.7",
        ],
      zip_safe=False)