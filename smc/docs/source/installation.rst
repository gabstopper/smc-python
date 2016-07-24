Installation
===========

Install the package by using a package manager such as pip.

.. code-block:: python

   pip install git+https://github.com/gabstopper/smc-python.git

Or optionally download the latest tarball (windows): smc-python_, unzip and run:

.. _smc-python: https://github.com/gabstopper/smc-python/archive/master.zip

`python setup.py install`

Dependencies on this library are:

* requests
* ipaddress
* prompt-toolkit (only if using CLI)
* pygments (only if using CLI)

If installation is required on a non-internet facing machine, you will have to download
the smc-python tarball and dependencies manually and install by running python setup install.

Once the smc-python package has been installed, you can import the
main packages into a python script:

.. code-block:: python

   import smc.api.web
   import smc.elements.element
   import smc.elements.engine
   import smc.elements.policy
   import smc.elements.system
   
To remove the package, simply run:

`pip uninstall smc-python`

For more information on next steps, please see Getting Started.   


