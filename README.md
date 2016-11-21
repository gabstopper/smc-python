[![Documentation Status](https://readthedocs.org/projects/smc-python/badge/?version=latest)](http://smc-python.readthedocs.io/en/latest/?badge=latest) [![GitHub release](https://img.shields.io/badge/version-0.3.8-brightgreen.svg)](https://github.com/gabstopper/smc-python/blob/master/smc/CHANGELOG)
#### smc-python

Python based library to provide the ability to interact with the Stonesoft Management Center API.
Provides automation capabilities for any environment that interact with the SMC and remotely.

Some of the functionality you get with the SMC Python API:

* Create any engine types; single firewall, cluster firewalls, ips engines, layer 2 firewalls, master engine and virtual engines.
* Engine operations such as enabling/disabling AV, GTI, default NAT, Contact Addresses, etc
* Add / remove interfaces
* Add / remove routes
* Engine level commands such as rebooting, going offline, policy push, enable/disable SSH, etc.
* Create and modify all network element objects such as Host, Network, Address Ranges, Domain Names, etc.
* Policy control (create rules, delete rules) for layer 3 firewall policies
* VPN Policy control and creation
* Management / Log Server settings configuration
* Admin User creation and modification
* System level control (update system packages, update engines, global blacklisting, etc
* Search operations for any object type by name, href and by filter
* Collections interface to view all objects by type


##### Requirements

Python 2.6, 2.7
Requests module
Security Management Center version 5.10, 6.0+

##### Getting Started

Installing package

use pip

`pip install git+https://github.com/gabstopper/smc-python.git`

download the latest tarball: [smc-python](https://github.com/gabstopper/smc-python/archive/master.zip), unzip and run

`python setup.py install`

##### Testing

Included are a variety of test example scripts that leverage the API to do various tasks in /examples

##### Basics

Before any commands are run, you must obtain a login session. Once commands are complete, call smc.logout() to remove the active session.

```python
from smc import session

session.login('http://1.1.1.1:8082', 'EiGpKD4QxlLJ25dbBEp20001')
....do stuff....
session.logout()
```

Once a valid session is obtained, it will be re-used for each operation performed.

 
Please see the read-the-docs documentation above for a full explanation and technical reference on available API classes.

[View Documentation on Read The Docs](http://smc-python.readthedocs.io/en/latest/?badge=latest)