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