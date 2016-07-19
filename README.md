[![Documentation Status](https://readthedocs.org/projects/smc-python/badge/?version=latest)](http://smc-python.readthedocs.io/en/latest/?badge=latest)
#### smc-python

Python based library to provide basic functions to interact with the Stonesoft Management Center API.

Currently it provides functionality to fully create engine instances, elements, blacklists, etc. 
There is also a CLI based front-end with command completion for performing operations remotely (brokered by the SMC).

##### Getting Started

Installing package

use pip

`pip install git+https://github.com/gabstopper/smc-python.git`

download the latest tarball: [smc-python](https://github.com/gabstopper/smc-python/archive/master.zip), unzip and run

`python setup.py install`

##### Testing

Included is a test.py script that has several examples for manipulating data using the SMC api.

##### Basics

Before any commands are run, you must obtain a login session. Once commands are complete, call smc.logout() to remove the active session.

```python
import smc.api.web

smc.api.web.login('http://1.1.1.1:8082', 'EiGpKD4QxlLJ25dbBEp20001')
....do stuff....
smc.api.web.logout()
```

Once a valid session is obtained, it will be re-used for each operation performed. 

Please see the read-the-docs documentation above for a full explanation and technical reference on available API classes.


###### Policy creation, loading and add/remove rules
```python
policy = FirewallPolicy.create('pythonapi', 
                                   smc.search.fw_template_policies(
                                                    policy='Firewall Inspection Template'))
policy = FirewallPolicy('pythonapi').load()   
policy.open()
policy.ipv4_rule.create('api1', 'kiley-test', 'smi', 'any', 'allow')
policy.ipv4_rule.create('api2', 'kiley-test', 'kiley-test', 'any', 'discard')
policy.ipv4_rule.create('api3', 'ami', 'any', 'any', 'refuse')
policy.save()
policy.ipv4_rule.delete('api3')
```