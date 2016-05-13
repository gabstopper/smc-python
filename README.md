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

```python
import smc

smc.login('http://1.1.1.1:8082', 'EiGpKD4QxlLJ25dbBEp20001')
....do stuff....
smc.logout()
```

Once a valid session is obtained, it will be re-used for each operation performed. 

###### Creating network objects
```python
smc.create.host('ami', '1.1.1.2')	#host
smc.create.network('goodnetwork', '1.2.0.0/255.255.252.0')	#network 
smc.create.network('networkwithcidr', '1.3.0.0/24', 'created by api tool')	#network with comment
smc.create.router('myrouter', '7.7.7.7')			#router object
smc.create.iprange('myrange', '1.1.1.1-1.2.3.4')	#iprange object
```

###### Create groups and add members
```python
smc.create.group('group_with_no_members')
smc.create.host('ami', '1.1.1.1')
smc.create.host('ami2', '2.2.2.2', comment='this is my comment')	#with optional comment
smc.create.group('anewgroup', ['ami','ami2']) #group with member list
```

###### Removing elements
```python
smc.remove.element('ami')		#remove host named 'ami'
smc.remove.element('agroup')	#remove group
smc.remove.element('myfw')		#remove firewall instance
```

###### Create / remove a single_fw instance
```python
smc.create.single_fw('myfw', '172.18.1.5', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
smc.create.l3interface('myfw', '5.5.5.5', '5.5.0.0/16')
smc.create.l3interface('myfw', '6.6.6.6', '6.6.6.0/255.255.255.0')
smc.create.router('172.18.1.250', '172.18.1.250')
smc.create.l3route('myfw6', '172.18.1.80', 'Any network', 0) 	#add route to myfw6, gateway 172.18.1.80 as default gw
smc.create.l3route('myfw6', '172.18.1.250', '192.168.3.0/24', 0)	#gateway 172.18.1.250 for network 192.168.3.0/24
```

###### Example of using a search filter 
```python
smc.get.element('myobject')  		#Search for element named 'myobject', match on 'name' field (looks at all object types)
smc.get.element('myobject', 'host')	#Search for host element named 'myobject'; match on 'name' field
smc.get.element('myobject', 'host', False)	#Search for host element/s with 'myobject' in all elements
```

###### Full provision of layer 3 fw including multiple interfaces and routes
```python
smc.create.router('172.18.1.250', '172.18.1.250')   	#name, #ip
smc.create.router('172.20.1.250', '172.20.1.250')   	
smc.create.network('192.168.3.0/24', '192.168.3.0/24') 	
    
smc.create.single_fw('myfw', '172.18.1.254', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
smc.create.l3interface('myfw', '10.10.0.1', '10.10.0.0/16', 3)		#name, interface ip, network, interface num
smc.create.l3interface('myfw', '172.20.1.254', '172.20.1.0/255.255.255.0', 6)
smc.create.l3route('myfw', '172.18.1.250', 'Any network', 0) 		#next hop, dest network, interface num
smc.create.l3route('myfw', '172.20.1.250', '192.168.3.0/24', 6)
```