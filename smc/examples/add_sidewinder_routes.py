"""
Migration Sidewinder routes into SMC

Dependencies:

* Python 2.7.x (Windows or *nix)
* smc-python: https://github.com/gabstopper/smc-python.git
* requests python library (will be automatically installed if python host has internet access)
* ipaddress 

Prequisities:

* Create the NGFW in SMC
* Create the network interfaces, matching Sidewinder configuration

The script is very simple, it requires an input file which represents the output from 
'cf static query' and is also generated by the NGFW migration tool.

To run:
 
* Configure the 'filename' value to reference the file where this route information is kept.
* Modify the 'firewall' value to specify the name of the NGFW engine within SMC.
* Set the session.login(...) url and api_key for your SMC

For the session.login parameters, the api_key value is specific to creating an "API Client" within
the SMC under Configuration->Administrators->API Client. 

This script can be run on the SMC 

.. code-block:: python
   
   session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001')

The script will 'load' the NGFW configuration to obtain references to the entry points associated
with the engine. Then it will loop through the routes file and call Engine.add_route(gateway, network)
and obtain the result. The result is printed whether it succeeds or fails. Upon failure, a reason will
be provided. In most cases, it may fail if the relevant interfaces are not created.

Here is an example of the static route input file:

route add route=10.10.10.0/255.255.255.0 gateway=10.2.11.7 distance=1 description=''
route add route=10.12.1.240/255.255.255.252 gateway=10.12.127.33 distance=1 description='iwan route'
route add route=10.0.0.0/255.0.0.0 gateway=10.12.127.33 distance=1 description=''
route add route=10.12.1.236/255.255.255.252 gateway=10.12.127.33 distance=1 description=''
route add route=10.6.4.0/255.255.255.0 gateway=10.12.127.33 distance=1 description=''

"""
import re
import ipaddress
import logging
from smc import session
from smc.core.engine import Engine 
logging.getLogger()
#logging.basicConfig(level=logging.DEBUG)

filename = '/Users/davidlepage/statis routes.txt'
firewall = 'mcafee2'

if __name__ == '__main__':

    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001')
    
    #Load the engine configuration; raises LoadEngineFailed for not found engine
    engine = Engine(firewall).load()
    
    with open(filename) as f:
        for line in f:
            for match in re.finditer('route=(.*) gateway=(.*) distance.*?', line, re.S):
                #make unicode (python 2.x)
                network = ipaddress.ip_network(u'{}'.format(match.group(1)))
                gateway = match.group(2)
                print "Adding route to network: {}, via gateway: {}".format(\
                                            network, gateway)
                
                result = engine.add_route(gateway, str(network))
                if not result.href:
                    print "Failed adding network: {} with gateway: {}, reason: {}".format(\
                                                network, gateway, result.msg)
                else:
                    print "Success adding route to network: {} via gateway: {}".format(\
                                                network, gateway)
    session.logout()