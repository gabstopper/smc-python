#### smc-python

Python based library to provide basic functions to interact with the Stonesoft Management Center API.

Currently it provides basic functionality to manipulate object data stored on the SMC. It is working towards having a command line
front end to ease interaction from automated tools such as Chef/Puppet or do automated deployments into virtual and cloud environments.

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

###### Create / remove a single fw L3 instance
```python
smc.create.single_fw('myfw', '172.18.1.5', '172.18.1.0/24', dns='5.5.5.5', fw_license=True)
smc.create.l3interface('myfw', '5.5.5.5', '5.5.0.0/16', 3)	#name, ip, network, interface
smc.create.l3interface('myfw', '6.6.6.6', '6.6.6.0/255.255.255.0', 6)
smc.create.router('172.18.1.250', '172.18.1.250')
smc.create.l3route('myfw6', '172.18.1.80', 'Any network', 0) 	#add route to myfw6, gateway 172.18.1.80 as default gw
smc.create.l3route('myfw6', '172.18.1.250', '192.168.3.0/24', 0)	#gateway 172.18.1.250 for network 192.168.3.0/24
```

###### Create / remove a single L2 instance with management port on interface 0, inline interfaces on 2-3, and DNS of 5.5.5.5
```python
smc.create.single_layer2('mylayer2', '172.18.1.254', '172.18.1.0/24', mgmt_interface='0', inline_interface='2-3', dns='5.5.5.5', fw_license=True)
smc.create.l2interface('mylayer2', interface_id='8,9')	#add additional inline interfaces on 8,9
smc.create.router('mynexthop', '172.18.1.50')			#create next hop router element
smc.create.l3route('mylayer2', 'mynexthop', '192.168.3.0/24', 0)	#create route using router element for net 192.168.3.0/24
```

###### Create / remove a single IPS instance with management port and inline interfaces
```python
smc.create.single_ips('myips', '172.18.1.254', '172.18.1.0/24', mgmt_interface='0', dns='5.5.5.5', fw_license=True)
smc.create.l2interface('myips', interface_id='8,9')
smc.create.router('mynexthop', '172.18.1.50')
smc.create.l3route('myips', 'mynexthop', '192.168.3.0/24', 0)
```

###### Example of using a search filter 
```python
smc.search.element('ami')
smc.search.element_as_json('myobject')  #Search for element named 'myobject'
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