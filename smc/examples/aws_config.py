'''
Stonesoft NGFW configurator for AWS instance deployment with auto-engine creation.
There are two example use cases that can be leveraged to generate NGFW automation into AWS:

Use Case 1: 
    * Fully create a VPC and subnets and auto provision NGFW as gateway
    
Use Case 2: 
    * Fully provision NGFW into existing VPC

In both cases the NGFW will connect to Stonesoft Management Center over an encrypted connection 
across the internet.
It is also possible to host SMC in AWS where contact could be made through AWS routing

.. note:: This also assumes the NGFW AMI is available in "My AMI's" within the AWS Console 

The Stonesoft NGFW will be created with 2 interfaces (limit for t2.micro) and use a DHCP interface 
for the management interface. No IP addresses are required when creating the NGFW. 
The strategy is that the network interface objects will be created first from the boto3 API 
allowing retrieval of the dynamically assigned ip addresses and subnet cidr blocks.
Those are then used by smc-python when creating the engine based on what AWS delegates. 
Default NAT is enabled on the engine to allow outbound traffic without a specific NAT rule. 

Once the NGFW is created, a license is automatically bound and the initial_contact for the engine
is created for AMI instance UserData. 

The AWS create_instances() method is called specifying the required information and user data allowing the
NGFW to auto-connect to the SMC without intervention.

The SMC should be prepared with the following:
* Available security engine licenses
* Pre-configured Layer 3 Policy with required policy

There is a current limitation on the NGFW side where Locations can not be added through the SMC API
therefore auto-policy queueing cannot be done without manually configuring the Location on the engine. When 
the policy is pushed, the engine will lose the public IP of the SMC management and log server. 
This should not be an issue if the SMC is on the same network or routable from inside (thru VPN, etc).

The tested scenario was based on public AWS documentation found at:
http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Scenario2.html

Requirements:
smc-python
boto3

Install smc-python::

    python install git+https://github.com/gabstopper/smc-python.git
    
'''

from pprint import pprint
import re
import time
import ipaddress
import boto3
import botocore
from smc.api.session import session
from smc.elements.engines import Layer3Firewall
from smc.elements import collections as collections
from smc.api.exceptions import CreateEngineFailed

smc_public_ip = '73.88.56.153'  #Hack initial_contact file; Locations are not configurable via SMC API
instance_type='t2.micro'
ngfw_6_0_2 = 'ami-b50f60a2' #east
            
class VpcConfiguration(object):
    """ 
    VpcConfiguration models the data to correlate certain aspects of an 
    AWS VPC such as VPC ID, associated subnets, and network interfaces and uses the boto3
    services model api.
    
    If the class is instantiated without a VPC id, the default VPC will be used. If a
    VPC is specified, it is loaded along with any relevant settings needed to configure
    and spin up a NGFW instance.
    
    Note that operations performed against AWS are not idempotent, so if there is a 
    failure, changes made would need to be undone.
    
    Instance attributes:
    
    :ivar availability_zone: AWS AZ for placement
    :ivar internet_gateway: AWS internet gateway object reference
    :ivar vpc: vpc object reference
     
    :param vpcid: VPC id
    """ 
    def __init__(self, vpcid=None):
        self.vpcid = vpcid
        self.vpc = None #: Reference to VPC
        self.alt_route_table = None
        self.network_interface = [] #: interface idx, network ref
  
    def load(self):
        if not self.vpcid:
            default_vpc = ec2.vpcs.filter(Filters=[{
                                        'Name': 'isDefault',
                                        'Values': ['true']}])
            for v in default_vpc:
                self.vpc = v
        else:
            for _ in range(5):
                try:
                    self.vpc = ec2.Vpc(self.vpcid)
                    print 'State of VPC: {}'.format(self.vpc.state)
                    break
                except botocore.exceptions.ClientError:
                    time.sleep(2)
            
        print "Loaded VPC with id: {} and cidr_block: {}".\
            format(self.vpc.vpc_id, self.vpc.cidr_block)
        return self
   
    @classmethod
    def create(cls, vpc_subnet, instance_tenancy='default'):
        """ Create new VPC with internet gateway and default route
        * Create the VPC
        * Create internet gateway
        * Attach internet gateway to VPC
        * Create route in main route table for all outbound to igw
        
        :param vpc_subnet: VPC cidr for encapsulated subnets
        :param instance_tenancy: 'default|dedicated|host'
        :returns: self
        """
        vpc_new = ec2.create_vpc(CidrBlock=vpc_subnet,
                                 InstanceTenancy=instance_tenancy)
        print "Created VPC: {}".format(vpc_new.vpc_id)
        
        vpc = VpcConfiguration(vpc_new.vpc_id).load() 
        
        vpc.internet_gateway = ec2.create_internet_gateway()
        print "Created internet gateway: {}".format(vpc.internet_gateway.id)
        
        #attach igw to vpc
        vpc.internet_gateway.attach_to_vpc(VpcId=vpc.vpc.vpc_id)
        
        vpc.create_default_gw()
        vpc.create_alt_route_table()
        return vpc

    def create_network_interface(self, interface_id, cidr_block,
                                 availability_zone=None,
                                 description=''):
        """
        Create a network interface to be used for the NGFW AMI
        This involves several steps: 
        * Create the subnet
        * Create the network interface for subnet
        * Disable SourceDestCheck on the network interface
        * Create elastic IP and bind (only to interface eth0)
        
        NGFW will act as a gateway to the private networks and will have 
        default NAT enabled.
        Interface 0 will be attached to the AWS interface eth0 which will
        be bound to the AWS Internet GW for inbound / outbound routing. The
        static IP address for eth0 will be calculated based on the network address
        broadcast -1.
        See AWS doc's for reserved addresses in a VPC:
        http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Subnets.html
        
        :param int interface_id: id to assign interface
        :param cidr_block: cidr of subnet
        :param availability_zone: optional
        :param description: description on interface
        :raises: botocore.exception.ClientError
        """
        subnet = self.create_subnet(cidr_block)
        wait_for_resource(subnet, self.vpc.subnets.all())
       
        #Assign static address and elastic to eth0
        if interface_id == 0:
            external = ipaddress.ip_network(u'{}'.format(cidr_block))
            external = str(list(external)[-2]) #broadcast address -1
            interface = subnet.create_network_interface(PrivateIpAddress=external,
                                                        Description=description)
            
            wait_for_resource(interface, self.vpc.network_interfaces.all()) 
            allocation_id = self.allocate_elastic_ip()
            address = ec2.VpcAddress(allocation_id)
            address.associate(NetworkInterfaceId=interface.network_interface_id)
        else:
            interface = subnet.create_network_interface(Description=description)
            wait_for_resource(interface, self.vpc.network_interfaces.all())
            
        interface.modify_attribute(SourceDestCheck={'Value': False})
        print "Created network interface: {}, subnet_id: {}, private address: {}".\
                format(interface.network_interface_id, interface.subnet_id,
                       interface.private_ip_address)
    
        self.availability_zone = interface.availability_zone 
        self.associate_network_interface(interface_id, interface.network_interface_id)

    def create_subnet(self, cidr_block):
        """
        Create a subnet
        :return: Subnet
        """
        subnet = ec2.create_subnet(VpcId=self.vpc.vpc_id,
                                   CidrBlock=cidr_block)
        print "Created subnet: {}, in availablity zone: {}".\
                    format(subnet.subnet_id, subnet.availability_zone)
        return subnet
    
    def create_default_gw(self):
        """ 
        Create the default GW pointing to IGW 
        """
        def_route = self.default_route_table()
        
        def_route.create_route(
                    DestinationCidrBlock='0.0.0.0/0',
                    GatewayId=self.internet_gateway.id)
 
    def create_alt_route_table(self):
        """ 
        Create alternate route table for non-public subnets
        """
        self.alt_route_table = self.vpc.create_route_table()
        print "Created alt route table: {}".format(\
                        self.alt_route_table.id)
    
    def alt_route_to_ngfw(self):
        """ 
        Create a route to non-local networks using eth1 (ngfw)
        as the route gateway
        """
        for intf in self.network_interface:
            for idx, network in intf.iteritems():
                if idx != 0:
                    self.alt_route_table.create_route(
                            DestinationCidrBlock='0.0.0.0/0',
                            NetworkInterfaceId=network.network_interface_id)
                    print "Added route for NGFW.."

    def allocate_elastic_ip(self):
        """ 
        Create elastic IP address for network interface. An elastic IP is
        used for the public facing interface for the NGFW AMI
        :return: AllocationId (elastic IP reference)
        """
        eip = None
        try:
            eip = ec2.meta.client.allocate_address(Domain='vpc')
        except botocore.exceptions.ClientError:
            #Caught AddressLimitExceeded. Find unassigned or re-raise
            addresses = ec2.meta.client.describe_addresses().get('Addresses')
            for unassigned in addresses:
                if not unassigned.get('NetworkInterfaceId'):
                    print "Unassigned Elastic IP found: {}".\
                                        format(unassigned.get('AllocationId'))
                    eip = unassigned
                    break
            if not eip: raise
        return eip.get('AllocationId')
    
    @property
    def availability_zone(self):
        """
        :return: availability_zone
        """
        if not hasattr(self, '_availability_zone'):
            return None
        return self._availability_zone
    
    @availability_zone.setter
    def availability_zone(self, value):
        self._availability_zone = value
    
    @property    
    def internet_gateway(self):
        """ 
        :return: InternetGateway
        """
        if not hasattr(self, '_internet_gateway'):
            return None
        return self._internet_gateway
    
    @internet_gateway.setter
    def internet_gateway(self, value):
        self._internet_gateway = value
                
    def default_route_table(self):
        """ 
        Get the default route table
        :return: RouteTable
        """
        rt = self.vpc.route_tables.filter(Filters=[{
                                        'Name': 'association.main',
                                        'Values': ['true']}])
        for default_rt in rt:
            return default_rt
    
    def associate_network_interface(self, interface_id, network_interface_id):
        """
        Associate the network interface to a device index.
        :raises: InvalidNetworkInterfaceID.NotFound
        """
        interface_itr = ec2.network_interfaces.filter(
                                    NetworkInterfaceIds=[network_interface_id])
        for intf in interface_itr:
            self.network_interface.append({interface_id: intf})
        
    def associate_alt_route_to_subnets(self):
        """
        Associate alternate route to non-public subnets
        Interface 0 will be assigned to the 'public' or management side
        network and other network subnets will be considered private. Note that
        a network interface will always have a subnet reference.
        """
        for networks in self.network_interface:
            for idx, ntwk in networks.iteritems():
                if idx != 0: #0 is considered public
                    self.alt_route_table.associate_with_subnet(
                                        SubnetId=ntwk.subnet_id)
        self.alt_route_to_ngfw()        
        
    def authorize_security_group_ingress(self, from_cidr_block, 
                                         ip_protocol='-1'):
        """ 
        Creates an inbound rule to allow access from public that will
        be redirected to the virtual FW
        For protocols, AWS references:
        http://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml
        
        :param cidr_block: network (src 0.0.0.0/0 from internet)
        :param protocol: protocol to allow (-1 for all)
        """
        for grp in self.vpc.security_groups.all():
            grp.authorize_ingress(CidrIp=from_cidr_block,
                                  IpProtocol=ip_protocol)
        print "Modified ingress security group: {}".format(grp.id)
    
    def build_ngfw_interfaces(self):
        """ 
        Build the right data structure for NGFW firewall interfaces
        :return: list of dictionarys representing NGFW interface
        """
        interfaces = []
        for intf in self.network_interface:
            for idx, obj in intf.iteritems():
                interfaces.append({'interface_id': idx,
                                    'address': obj.private_ip_address,
                                    'network_value': obj.subnet.cidr_block})
        return interfaces
                       
    def launch(self, key_pair, userdata=None, 
               imageid=ngfw_6_0_2, 
               availability_zone='us-west-2b'):
        """
        Launch the instance
        
        :param key_name: keypair required to enable SSH to AMI
        :param userdata: optional, but recommended
        :param imageid: NGFW AMI id
        :param availability_zone: where to launch instance
        :return: instance
        """
        verify_key_pair(key_pair) #exception raised here
        
        print "Launching instance into availability zone: {}".format(\
                                                self.availability_zone)
          
        interfaces = []
        for interface in self.network_interface:
            for idx, network in interface.iteritems():
                interfaces.append({'NetworkInterfaceId': network.network_interface_id,
                                   'DeviceIndex': idx})

        #create run instance
        instance = ec2.create_instances(ImageId=imageid,
                                        MinCount=1,
                                        MaxCount=1,
                                        InstanceType=instance_type,
                                        KeyName=key_pair,
                                        Placement={'AvailabilityZone': 
                                                   self.availability_zone},
                                        NetworkInterfaces=interfaces,
                                        UserData=userdata)
        return instance[0]
    
    def rollback(self):
        """ 
        In case of failure, convenience to wrap in try/except and remove
        the VPC. If there is a running EC2 instance, this will terminate
        that instnace, remove all other dependencies and delete the VPC.
        Typically this is best run when attempting to create the entire
        VPC. It is not advisable if loading an existing VPC as it will remove
        the entire configuration.
        """
        for instance in self.vpc.instances.filter(Filters=[{
                                    'Name': 'instance-state-name',
                                    'Values': ['running', 'pending']}]):
            print "Terminating instance: {}".format(instance.instance_id)
            instance.terminate()
            for state in waiter(instance, 'terminated'):
                print state
     
        for intf in self.vpc.network_interfaces.all():
            print "Deleting interface: {}".format(intf)
            intf.delete()
        for subnet in self.vpc.subnets.all():
            print "Deleting subnet: {}".format(subnet)
            subnet.delete()
        for rt in self.vpc.route_tables.all():
            if not rt.associations_attribute:
                print "Deleting unassociated route table: {}".format(rt)
                rt.delete()
            else:
                for current in rt.associations_attribute:
                    if not current or current.get('Main') == False:
                        print "Deleting non-default route table: {}".format(rt)
                        rt.delete()
        for igw in self.vpc.internet_gateways.all():
            print "Detach and deleting IGW: {}".format(igw)
            igw.detach_from_vpc(VpcId=self.vpc.vpc_id)
            igw.delete()
        
        self.vpc.delete()
        print "Deleted vpc: {}".format(self.vpc.vpc_id)
            
def verify_key_pair(key_pair):
    """ 
    Verifies key pair before launching AMI
    :raises: botocore.exception.ClientError 
    """
    ec2.meta.client.describe_key_pairs(KeyNames=[key_pair])

def waiter(instance, status):
    """ 
    Generator to monitor the startup of the launched AMI 
    Call this in loop to get status
    :param instance: instance to monitor 
    :param status: status to check for:
           'pending|running|shutting-down|terminated|stopping|stopped'
    :return: generator message updates 
    """
    while True:
        if instance.state.get('Name') != status:
            print "Instance in state: {}, waiting..".format(instance.state.get('Name'))
            time.sleep(5)
            instance.reload()
        else:
            yield "Image in desired state: {}!".format(status)
            break

def wait_for_resource(resource, iterable):
    """
    Wait for the resource to become available. If the AWS
    component isn't available right away and a reference call is
    made the AWS client throw an exception. This checks the iterable 
    for the component id before continuing. Insert this where you 
    might need to introduce a short delay.
    
    :param resource: subnet, interface, etc
    :param iterable: iterable function
    :return: None
    """
    for _ in range(5):
        for _id in iterable:
            if resource.id == _id.id:
                return
            time.sleep(2)
            
def create_ngfw_in_smc(name, interfaces, 
                       domain_server_address=None,
                       default_nat=True,
                       reverse_connection=True):
    """ 
    Create NGFW instance in SMC, bind the license and return the 
    initial_contact info which will be fed to the AWS launcher as 
    UserData.
    The NGFW will be configured to enable Default NAT for outbound.
    
    :param str name: name of ngfw in smc
    :param list interfaces: list of interfaces from VpcConfiguration
    :param list domain_server_address: (optional) dns address for engine
    :param boolean default_nat: (optional: default True) whether to enable default NAT
    :param boolean reverse_connection: (optional: default True) use when behind NAT
    
    See :py:class:`smc.elements.engines.Layer3Firewall` for more info
    """
    global engine
    print "Creating NGFW...."
    
    for interface in interfaces:
        address = interface.get('address')
        interface_id = interface.get('interface_id')
        network_value = interface.get('network_value')
        if interface_id == 0:
            mgmt_ip = address
            mgmt_network = network_value
            engine = Layer3Firewall.create(name, 
                                           mgmt_ip, 
                                           mgmt_network,
                                           domain_server_address=domain_server_address,
                                           reverse_connection=reverse_connection, 
                                           default_nat=default_nat)
            #default gateway is first IP on network subnet
            gateway = ipaddress.ip_network(u'{}'.format(mgmt_network))
            gateway = str(list(gateway)[1])
            engine.add_route(gateway, '0.0.0.0/0')
        else:
            engine.physical_interface.add_single_node_interface(interface_id, 
                                                                address, 
                                                                network_value)
        #Enable VPN on external interface
        for intf in engine.internal_gateway.internal_endpoint.all():
            if intf.name == mgmt_ip:
                intf.modify_attribute(enabled=True)
    
    print "Created NGFW..."
    for node in engine.nodes:
        node.bind_license()
        content = node.initial_contact(enable_ssh=True)
    
    #reload engine to update engine settings
    engine = engine.load()
    
    #engine.upload(policy='Layer 3 Virtual Firewall Policy') #queue policy
    return re.sub(r"management-address string (.+)", "management-address string " + \
                  smc_public_ip, content)

def change_ngfw_name(instance_id, az):
    """ Change the engine name to match the InstanceId on Amazon
         
    :param instance_id: instance ID obtained from AWS run_instances
    :param az: availability zone
    """
    engine.modify_attribute(name='{} ({})'.format(instance_id, az))
    engine.internal_gateway.modify_attribute(name='{} ({}) Primary'.format(\
                                        instance_id, az))
    for node in engine.nodes:
        node.modify_attribute(name='{} node {}'.format(instance_id, node.nodeid))

def associate_vpn_policy(vpn_policy_name, gateway='central'):
    """
    Associate this engine with an existing VPN Policy
    First create the proper VPN Policy within the SMC. This will add the AWS NGFW as
    a gateway node.
    
    :param str vpn_policy_name: name of existing VPN Policy
    :param str gateway: |central|satellite
    :return: None
    """ 
    for policy in collections.describe_vpn_policies():
        if policy.name == vpn_policy_name:
            vpn = policy.load()
            vpn.open()
            if gateway == 'central':
                vpn.add_central_gateway(engine.internal_gateway.href)
            else:
                vpn.add_satellite_gateway(engine.internal_gateway.href)
            vpn.save()
            vpn.close()
        break
        
def monitor_ngfw_status(step=10):
    """
    Monitor NGFW initialization. Status will start as 'Declared' and move to
    'Configured' once initial contact has been made. After policy upload, status
    will move to 'Installed'.
    
    :param step: sleep interval
    """
    print "Waiting for NGFW to fully initialize..."
    desired_status = 'Online'
    while True:
        for node in engine.nodes:
            status = node.status()
            if status.get('status') != desired_status:
                print "Status: {}, Config Status: {}, State: {}".format(\
                        status.get('status'), status.get('configuration_status'), 
                        status.get('state'))
            else:
                print 'NGFW Status: {}, Installed Policy: {}, State: {}, Version: {}'.\
                format(status.get('status'), status.get('installed_policy'),
                       status.get('state'), status.get('version'))
                return
        time.sleep(step)
        

        
if __name__ == '__main__':
    
    session.login(url='http://172.18.1.150:8082', api_key='EiGpKD4QxlLJ25dbBEp20001')
    
    import smc.actions.remove
    smc.actions.remove.element('aws-02', 'single_fw')

    ec2 = boto3.resource('ec2', 
                         #region_name='us-west-2',
                         region_name='us-east-1'
                         )
    '''
    Use Case 1: Create entire VPC and deploy NGFW
    ---------------------------------------------
    This will fully create a VPC and associated requirements. 
    The following will occur:
    * A new VPC will be created in the AZ based on boto3 client region
    * Two network subnets are created in the VPC, one public and one private
    * Two network interfaces are created and assigned to the subnets
      eth0 = public, eth1 = private
    * An elastic IP is created and attached to the public network interface
    * An internet gateway is created and attached to the public network interface
    * A route is created in the default route table for the public interface to
      route 0.0.0.0/0 to the IGW
    * The default security group is modified to allow inbound access from 0.0.0.0/0
      to to the NGFW network interface
      :py:func:`VpcConfiguration.authorize_security_group_ingress`
    * A secondary route table is created with a default route to 0.0.0.0/0 with a next
      hop assigned to interface eth1 (NGFW). This is attached to the private subnet.
    * The NGFW is automatically created and UserData is obtained for AMI instance launch
    * AMI is launched using UserData to allow auto-connection to NGFW SMC Management
    * NGFW receives queued policy and becomes active
    
    .. note: The AZ used during instance spin up is based on the AZ that is auto-generated
             by AWS when the interface is created. If you require a different AZ, set the 
             attribute :py:class:`VpcConfiguration.availability_zone` before called launch. 
    '''
    #Uncomment and put your VPC name in here to delete the whole thing
    vpc = VpcConfiguration('vpc-da3a74bd').load()
    vpc.rollback()
    
    
    vpc = VpcConfiguration.create(vpc_subnet='192.168.3.0/24')
    try:
        vpc.create_network_interface(0, '192.168.3.240/28', description='public-ngfw') 
        vpc.create_network_interface(1, '192.168.3.0/25', description='private-ngfw')
        vpc.associate_alt_route_to_subnets()
        vpc.authorize_security_group_ingress('0.0.0.0/0', ip_protocol='-1')
        
        userdata = create_ngfw_in_smc(name='aws-02', 
                                      interfaces=vpc.build_ngfw_interfaces(),
                                      domain_server_address=['8.8.8.8', '8.8.4.4'])
        
        instance = vpc.launch(key_pair='dlepage', userdata=userdata)
        
        #change ngfw name to 'instanceid-availability_zone
        change_ngfw_name(instance.id, vpc.availability_zone)
        associate_vpn_policy('myVPN')
        
        for message in waiter(instance, 'running'):
            print message
        
        start_time = time.time()
        monitor_ngfw_status()
        print("--- %s seconds ---" % (time.time() - start_time))
    
    except (botocore.exceptions.ClientError, CreateEngineFailed) as e:
        print "Caught exception, rolling back: {}".format(e)
        vpc.rollback()

    '''
    Use Case 2: Deploy NGFW into existing VPC
    -----------------------------------------
    This assumes the following:
    * You have an existing VPC, with a public subnet and private subnet/s
    * You have created 2 network interfaces, one assigned to the public subnet
    * Disable SourceDestCheck on the network interfaces
    * The public network interface is assigned an elastic IP
    * An internet gateway is attached to the VPC
    * A route table exists for the VPC (default is ok) and allows outbound traffic 
      to the internet gateway.
    
    When associating the network interface, interface eth0 should be the network
    interface associated with the elastic (public) facing interface id.
    After creating the instance, manually add a new route table, and 
    route table entry that directs destination 0.0.0.0/0 to the NGFW 
    interface id for eth1 (not the instance). Then attach the new route table 
    to the private subnet.
    '''
    '''    
    vpc = VpcConfiguration('vpc-f1735e95').load()
    vpc.associate_network_interface(0, 'eni-49ab2635')
    vpc.associate_network_interface(1, 'eni-0b931e77')
    vpc.authorize_security_group_ingress('0.0.0.0/0', ip_protocol='-1')
    vpc.availability_zone.add('us-west-2a')
    
    userdata = create_ngfw_in_smc(name='aws-02', 
                                  interfaces=vpc.build_ngfw_interfaces(),
                                  domain_server_address=['8.8.8.8', '8.8.4.4'])
    
    instance = vpc.launch(key_pair='aws-ngfw', userdata=userdata)
    for message in wait_for_ready(instance):
        print message
    '''
    '''
    addr = ec2.meta.client.describe_addresses().get('Addresses')
    for available in addr:
        if not available.get('NetworkInterfaceId'):
            print "Available Elastic IP: {}".format(available.get('AllocationId'))
    '''
    
    #http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Subnets.html
    session.logout()
    