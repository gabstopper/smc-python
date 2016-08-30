from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()
    
setup(name='smc-python',
      version='0.2',
      description='Python based API to Stonesoft Security Management Center',
      url='http://github.com/gabstopper/smc-python',
      author='David LePage',
      author_email='dwlepage70@gmail.com',
      license='None',
      packages=['smc', 'smc.actions', 'smc.api', 'smc.elements'],
      install_requires=[
          'requests'
      ],
      include_package_data=True,
      zip_safe=False)
