#### smc-python

Python based library to provide basic functions to interact with the Stonesoft Management Center API.

Currently it provides basic functionality to manipulate object data stored on the SMC. It is working towards having a command line
front end to ease interaction from automated tools such as Chef/Puppet or do automated deployments into virtual and cloud environments.

##### Getting Started

Installing package

use pip

`pip git+https://github.com/gabstopper/smc-python.git`

download the latest tarball: [smc-python](https://github.com/gabstopper/smc-python/archive/master.zip), unzip and run

`python setup.py install`

##### Testing

Included is a test.py script that has several examples for manipulating data using the SMC api.

##### Basics

Before any commands are run, you must obtain a login session. Once commands are complete, call smc.logout() to remove the active session.

```ruby
import smc

smc.login('http://1.1.1.1:8082', 'EiGpKD4QxlLJ25dbBEp20001')
....do stuff....
smc.logout()
```

Once a valid session is obtained, it will be re-used for each operation performed. 

###### Creating/removing a host record. Validation is done based on IP address.
```ruby
smc.create_host('ami', '1.1.1.2')
smc.remove_host('ami')
```

###### Create group and add members
```ruby
smc.create_group('group_with_no_members')
smc.create_host('ami', '1.1.1.1')
smc.create_host('ami2', '2.2.2.2')
smc.create_group('anewgroup', ['ami','ami2']) #group with member list
```

###### Create / remove a single_fw instance
```ruby
smc.create_single_fw('myfw', '172.18.1.5', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
time.sleep(5)
smc.remove_single_fw('myfw')
```

###### Example of using a search filter 
```ruby
mygroup = smc.filter_by_type('group', 'Skype Servers')  #Search for group named (Skype Servers)
myfw = smc.filter_by_type('single_fw', 'vmware-fw') #Search for single fw named 'vmware-fw'
myobject = smc.filter_by_element('myelement') #Search for object by name ignoring object type
```

