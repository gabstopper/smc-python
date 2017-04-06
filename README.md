[![Documentation Status](https://readthedocs.org/projects/smc-python/badge/?version=latest)](http://smc-python.readthedocs.io/en/latest/?badge=latest) [![GitHub version](https://badge.fury.io/gh/gabstopper%2Fsmc-python.svg)](https://badge.fury.io/gh/gabstopper%2Fsmc-python)

### smc-python

Python based library to provide the ability to interact with the Stonesoft Management Center API.
Provides automation capabilities for any environment that interact with the SMC remotely.

Some of the functionality you get with the SMC Python API:

* Create any engine types; single firewall, cluster firewalls, ips engines, layer 2 firewalls, master engine and virtual engines.
* Engine operations such as enabling/disabling AV, GTI, default NAT, Contact Addresses, etc
* Interface configurations
* Routing configurations (OSPF, Static)
* Engine level commands such as rebooting, going offline, policy push, enable/disable SSH, etc.
* Create and modify all network element objects such as Host, Network, Address Ranges, Domain Names, etc.
* Policy control (create rules, delete rules) for layer 3 firewall policies
* VPN Policy control and creation
* Management / Log Server settings configuration
* Admin User creation and modification
* System level controls; update system packages, update engines, global blacklisting, etc
* Tasks
* Search operations for any object type by name, href and by filter
* Collections interface to view all objects by type


##### Requirements

Python 2.7

Python 3.4, 3.5 (version >- 0.4)

Requests 

Security Management Center version 5.10, 6.0, 6.1, 6.1.1, 6.1.2, 6.2

##### Getting Started

Installing package

Use pip:

`pip install git+https://github.com/gabstopper/smc-python.git`

Specific version:

`pip install -e git://github.com/gabstopper/smc-python.git@v0.4.2#egg=smc-python-0.4.2`

Download the latest tarball: [smc-python](https://github.com/gabstopper/smc-python/archive/master.zip), unzip and run:

`python setup.py install`

##### Testing

Included are a variety of test example scripts that leverage the API to do various tasks in /examples

##### Basics

Before any commands are run, you must obtain a login session. Once commands are complete, call smc.logout() to remove the active session. To obtain the api_key, log in to the Stonesoft Management Center and create an API client with the proper privileges.

```python
from smc import session

session.login(url='http://1.1.1.1:8082', api_key='xxxxxxxxxxxxx')
....do stuff....
session.logout()
```

Once a valid session is obtained, it will be re-used for each operation for the duration of the sessions validity, or until the program is exited.

 
Please see the read-the-docs documentation above for a full explanation and technical reference on available API classes.

[View Documentation on Read The Docs](http://smc-python.readthedocs.io/en/latest/?badge=latest)