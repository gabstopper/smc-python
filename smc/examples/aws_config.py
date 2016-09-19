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

The Stonesoft NGFW will be created with 2 interfaces (limit for t2.micro) and use static interfaces
for both private and public. No IP addresses are required when creating the NGFW. 
The strategy is that the network interface objects will be created first from the boto3 API, if
the interface is for eth0 (management), then the subnet range will be determined and the NGFW will
take an IP address on that subnet, -1 from the broadcast address.
For the 'private' (inside) interface, AWS will auto-assign an IP address which will be statically
assigned to the NGFW during FW creation.

See AWS doc's for reserved addresses in a VPC:
http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Subnets.html

Default NAT is enabled on the engine to allow outbound traffic without a specific NAT rule. 

Once the NGFW is created, a license is automatically bound and the initial_contact for the engine
is created for AMI instance UserData. 

The AWS create_instances() method is called specifying the required information and user data allowing the
NGFW to auto-connect to the SMC without intervention.

The SMC should be prepared with the following:
* Available security engine licenses
* Pre-configured Layer 3 Policy with needed policy

The tested scenario was based on public AWS documentation found at:
http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Scenario2.html

Requirements:
* smc-python
* boto3
* pyyaml

Install smc-python::

    python install git+https://github.com/gabstopper/smc-python.git

Install boto3 and pyyaml via pip::

    pip install boto3
    pip install pyyaml
'''
import re
import time
import ipaddress
import logging
import yaml
import boto3
import botocore
from smc import session
from smc.elements.engines import Layer3Firewall
from smc.elements import collection
from smc.api.exceptions import CreateEngineFailed
from smc.elements.helpers import location_helper
#from smc import set_stream_logger
#set_stream_logger()

smc_public_ip = '73.88.56.153'  #Hack initial_contact file; Locations are not configurable via SMC API
            
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
    
    :ivar vpcid: ID of the VPC
    :ivar vpc: Reference to the VPC object
    :ivar alt_route_table: reference to the alternate route table for private networks
    :ivar elastic_ip: Elastic IP address, will be used for contact address
    :ivar private_subnet: Private subnet used to spin up client instance
    :ivar internet_gateway: AWS internet gateway object reference
    :ivar network_interface: list of dict holding interface index, network
    :ivar availability_zone: AWS AZ for placement
     
    :param vpcid: VPC id
    """ 
    def __init__(self, vpcid=None):
        self.vpcid = vpcid
        self.vpc = None
        self.alt_route_table = None
        self.elastic_ip = None
        self.private_subnet = None
        self.internet_gateway = None
        self.network_interface = []
        self.availability_zone = None
  
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
                    logger.info('State of VPC: {}'.format(self.vpc.state))
                    break
                except botocore.exceptions.ClientError:
                    time.sleep(2)
            
        logger.info("Loaded VPC with id: {} and cidr_block: {}"
                    .format(self.vpc.vpc_id, self.vpc.cidr_block))
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
        logger.info("Created VPC: {}".format(vpc_new.vpc_id))
        
        vpc = VpcConfiguration(vpc_new.vpc_id).load() 
        
        vpc.internet_gateway = ec2.create_internet_gateway()
        logger.info("Created internet gateway: {}"
                    .format(vpc.internet_gateway.id))
        
        #attach igw to vpc
        vpc.internet_gateway.attach_to_vpc(VpcId=vpc.vpc.vpc_id)
        
        vpc.create_default_gw()
        vpc.create_alt_route_table()
        return vpc

    def create_network_interface(self, interface_id, cidr_block,
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
            self.private_subnet = subnet #need this ref for client instance
            logger.info("Associating subnet ID: {} to alternate route table"
                        .format(subnet.subnet_id))
            self.alt_route_table.associate_with_subnet(
                                        SubnetId=subnet.subnet_id)
            logger.info("Setting default route using alternate route table for "
                        "interface {}".format(interface.network_interface_id))
            self.alt_route_table.create_route(
                            DestinationCidrBlock='0.0.0.0/0',
                            NetworkInterfaceId=interface.network_interface_id)
            
        interface.modify_attribute(SourceDestCheck={'Value': False})
        logger.info("Finished creating and configuring network interface: {}, "
                "subnet_id: {}, address: {}"
                .format(interface.network_interface_id, interface.subnet_id,
                       interface.private_ip_address))
    
        self.availability_zone = interface.availability_zone 
        self.associate_network_interface(interface_id, interface.network_interface_id)

    def create_subnet(self, cidr_block):
        """
        Create a subnet
        
        :return: Subnet
        """
        subnet = ec2.create_subnet(VpcId=self.vpc.vpc_id,
                                   CidrBlock=cidr_block)
        logger.info("Created subnet: {}, in availablity zone: {}"
                    .format(subnet.subnet_id, subnet.availability_zone))
        return subnet
    
    def create_default_gw(self):
        """ 
        Create the default route with next hop pointing to IGW 
        """
        rt = self.vpc.route_tables.filter(Filters=[{
                                        'Name': 'association.main',
                                        'Values': ['true']}])
        for default_rt in rt:
            default_rt.create_route(
                    DestinationCidrBlock='0.0.0.0/0',
                    GatewayId=self.internet_gateway.id)
 
    def create_alt_route_table(self):
        """ 
        Create alternate route table for non-public subnets
        """
        self.alt_route_table = self.vpc.create_route_table()
        logger.info("Created alt route table: {}"
                    .format(self.alt_route_table.id))
        
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
                    logger.info("Unassigned Elastic IP found: {}"
                                .format(unassigned.get('AllocationId')))
                    eip = unassigned
                    break
            if not eip: raise
        self.elastic_ip = eip.get('PublicIp')
        return eip.get('AllocationId')
    
    def associate_network_interface(self, interface_id, network_interface_id):
        """
        Associate the network interface to a device index. This is used by the
        launch function to fill the constructor details which require a reference
        to the network interface and it's numeric index (eth0=0, eth1=1, etc)
        
        :raises: InvalidNetworkInterfaceID.NotFound
        """
        interface_itr = ec2.network_interfaces.filter(
                                    NetworkInterfaceIds=[network_interface_id])
        for intf in interface_itr:
            self.network_interface.append({interface_id: intf})
    
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
        logger.info("Modified ingress security group: {}".format(grp.id))
    
    @property
    def ngfw_interfaces(self):
        """ 
        Build the right data structure for NGFW firewall interfaces
        
        :return: list of dict representing NGFW interface
        """
        interfaces = []
        for intf in self.network_interface:
            for idx, obj in intf.iteritems():
                interfaces.append({'interface_id': idx,
                                    'address': obj.private_ip_address,
                                    'network_value': obj.subnet.cidr_block})
        return interfaces
    
    @property
    def ngfw_gateway(self):
        for intf in self.network_interface:
            for idx, obj in intf.iteritems():
                if idx == 0:
                    #default gateway is first IP on network subnet
                    gateway = ipaddress.ip_network(u'{}'.format(obj.subnet.cidr_block))
                    gateway = str(list(gateway)[1])
        return gateway
                                   
    def launch(self, key_pair, userdata=None, 
               imageid=None, 
               instance_type='t2.micro'):
        """
        Launch the instance
        
        :param key_name: keypair required to enable SSH to AMI
        :param userdata: optional, but recommended
        :param imageid: NGFW AMI id
        :param availability_zone: where to launch instance
        :return: instance
        """
        verify_key_pair(key_pair) #exception raised here
        
        logger.info("Launching ngfw as {} instance into availability zone: {}"
                    .format(instance_type, self.availability_zone))
          
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
            logger.info("Terminating instance: {}".format(instance.instance_id))
            instance.terminate()
            for state in waiter(instance, 'terminated'):
                logger.info(state)
     
        for intf in self.vpc.network_interfaces.all():
            logger.info("Deleting interface: {}".format(intf))
            intf.delete()
        for subnet in self.vpc.subnets.all():
            logger.info("Deleting subnet: {}".format(subnet))
            subnet.delete()
        for rt in self.vpc.route_tables.all():
            if not rt.associations_attribute:
                logger.info("Deleting unassociated route table: {}".format(rt))
                rt.delete()
            else:
                for current in rt.associations_attribute:
                    if not current or current.get('Main') is False:
                        logger.info("Deleting non-default route table: {}".format(rt))
                        rt.delete()
        for igw in self.vpc.internet_gateways.all():
            logger.info("Detach and deleting IGW: {}".format(igw))
            igw.detach_from_vpc(VpcId=self.vpc.vpc_id)
            igw.delete()
        
        self.vpc.delete()
        logger.info("Deleted vpc: {}".format(self.vpc.vpc_id))


class NGFWConfiguration(object):
    
    def __init__(self, name='aws-stonesoft', dns=None, default_nat=True, 
                 antivirus=False, gti=False, location=None,
                 firewall_policy=None, vpn_policy=None,
                 vpn_role='central', reverse_connection=False, 
                 **kwargs):
        self.engine = None
        self.name = name
        self.dns = dns if dns else []
        self.default_nat = default_nat
        self.antivirus = antivirus
        self.gti = gti
        self.location = location
        self.vpn_role = vpn_role
        self.vpn_policy = vpn_policy
        self.firewall_policy = firewall_policy
        self.reverse_connection = reverse_connection
    
    def create(self, interfaces, default_gateway):
        """
        Create NGFW
        
        :param list interfaces: dict of interface information
        :return: self
        """
        for interface in interfaces:
            address = interface.get('address')
            interface_id = interface.get('interface_id')
            network_value = interface.get('network_value')
            if interface_id == 0:
                mgmt_ip = address
                mgmt_network = network_value
                engine = Layer3Firewall.create(self.name, 
                                               mgmt_ip, 
                                               mgmt_network,
                                               domain_server_address=self.dns,
                                               reverse_connection=self.reverse_connection, 
                                               default_nat=self.default_nat,
                                               enable_antivirus=self.antivirus,
                                               enable_gti=self.gti)
                engine.add_route(default_gateway, '0.0.0.0/0')
            else:
                engine.physical_interface.add_single_node_interface(interface_id, 
                                                                    address, 
                                                                    network_value)
        self.engine = engine.reload()
        #Enable VPN on external interface if policy provided
        if self.vpn_policy:
            for intf in engine.internal_gateway.internal_endpoint.all():
                if intf.name == mgmt_ip:
                    intf.modify_attribute(enabled=True)
            self.associate_vpn_policy()

        logger.info("Created NGFW...")
        return self

    def queue_policy(self):
        """
        Queue Firewall Policy for firewall. Monitor the upload process from 
        the SMC Administration->Tasks menu
        
        :return: None
        """
        if self.firewall_policy:
            self.engine.upload('{}'.format(self.firewall_policy), 
                               wait_for_finish=False)
            logger.info("Queued firewall policy: {}".format(self.firewall_policy))
        
    def add_contact_address(self, elastic_ip):
        """
        Add the elastic IP public address as a contact address to the 
        management interface (Interface 0)
        
        :return: None
        """
        for interface in self.engine.interface.all():
            if interface.name == 'Interface 0':
                location = location_helper('Default')
                interface.add_contact_address(elastic_ip, location, self.engine.etag)
 
    def initial_contact(self):
        """
        Bind license and return initial contact information
        
        :return: text content for userdata
        """
        for node in self.engine.nodes:
            result = node.bind_license()
            if result.msg:
                logger.error("License bind failed with message: {}. You may have to resolve before"
                             "policy installation is successful"
                             .format(result.msg))
            content = node.initial_contact(enable_ssh=True)
        
        if 'smc_public_ip' in globals():
            return re.sub(r"management-address string (.+)", "management-address string " + \
                          smc_public_ip, content)
        else:
            return content
   
    def associate_vpn_policy(self):
        """
        Associate this engine with an existing VPN Policy
        First create the proper VPN Policy within the SMC. This will add the AWS NGFW as
        a gateway node.
        
        :param str vpn_policy_name: name of existing VPN Policy
        :param str gateway: central|satellite
        :return: None
        """
        if self.vpn_policy: 
            for policy in collection.describe_vpn_policies():
                if policy.name.startswith(self.vpn_policy):
                    vpn = policy.load()
                    vpn.open()
                    if self.vpn_role == 'central':
                        vpn.add_central_gateway(self.engine.internal_gateway.href)
                    else:
                        vpn.add_satellite_gateway(self.engine.internal_gateway.href)
                    vpn.save()
                    vpn.close()
                    break
    
    def monitor_status(self, step=10):
        """
        Monitor NGFW initialization. Status will start as 'Declared' and move to
        'Configured' once initial contact has been made. After policy upload, status
        will move to 'Installed'. Once the FW reports 'Online' status, function returns
        
        :param step: sleep interval
        """
        logger.info("Waiting for NGFW to fully initialize...")
        desired_status = 'Online'
        try:
            while True:
                for node in self.engine.nodes:
                    status = node.status()
                    if status:
                        current_status = status.get('status')
                        if current_status != desired_status:
                            logger.info("Status: {}, Config Status: {}, State: {}"
                                        .format(current_status, 
                                                status.get('configuration_status'), 
                                                status.get('state')))
                        else:
                            logger.info("NGFW Status: {}, Installed Policy: {}, State: {}, "
                                        "Version: {}".format(status.get('status'), 
                                                             status.get('installed_policy'),
                                                             status.get('state'), 
                                                             status.get('version')))
                            return
                time.sleep(step)
        except KeyboardInterrupt:
            pass
        
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, 'name={}'\
                           .format(self.name))
           
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
            yield "Instance in state: {}, waiting..".format(instance.state.get('Name'))
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
   
def spin_up_host(key_pair, vpc, instance_type='t2.micro',
                 aws_client_ami='ami-2d39803a'):
    """
    Create an internal amazon host on private subnet for testing
    Use ubuntu AMI by default
    """
    logger.info("Spinning up client instance on private subnet: {}"
                .format(vpc.private_subnet.id))
    instance = ec2.create_instances(ImageId=aws_client_ami,
                                    MinCount=1,
                                    MaxCount=1,
                                    SubnetId=vpc.private_subnet.id,
                                    InstanceType=instance_type,
                                    KeyName=key_pair,
                                    Placement={'AvailabilityZone': 
                                                vpc.availability_zone})
    instance = instance[0]
    for data in instance.network_interfaces_attribute:
        ntwk = data.get('PrivateIpAddress')
    logger.info("Client instance created: {} with keypair: {} at ipaddress: {}"
                .format(instance.id, instance.key_name, ntwk))

def menu(lst, question):
    """
    Generic menu prompt for region or VPC delete arguments
    """
    while True:
        print question
        for entry in lst:
            print(1 + lst.index(entry)),
            print(") " + entry)
        
        try:
            return lst[input()-1]
        except IndexError:
            print "Invalid choice. Try again."

class AWSConfig(object):
    def __init__(self, aws_keypair, ngfw_ami, aws_client=False, 
                 aws_instance_type='t2.micro', region=None,
                 **kwargs):
        self.aws_keypair = aws_keypair
        self.aws_client = aws_client
        self.ngfw_ami = ngfw_ami
        self.region = region
        self.aws_instance_type = aws_instance_type
        
        for k, v in kwargs.iteritems():
            setattr(self, '_'+k, v)
    
    @property
    def vpc_private(self):
        return self._vpc_private
    
    @property
    def vpc_public(self):
        return self._vpc_public
    
    @property
    def vpc_subnet(self):
        return self._vpc_subnet

    @property
    def aws_access_key_id(self):
        return self._aws_access_key_id
    
    @property
    def aws_secret_access_key(self):
        return self._aws_secret_access_key
    
    @property
    def aws_client_ami(self):
        if self.aws_client and hasattr(self, '_aws_client_ami'):
            return self._aws_client_ami
        else:
            return None
     
    def __getattr__(self, value):
        return None
                            
if __name__ == '__main__':
    
    logger = logging.getLogger('aws_config')
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    import argparse
    parser = argparse.ArgumentParser(description='Stonesoft NGFW AWS Launcher')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-i', '--interactive', action='store_true', help='Use interactive prompt mode')
    group.add_argument('-y', '--yaml', help='Specify yaml configuration file name')
    parser.add_argument('-d', '--delete', action='store_true', help='Delete a VPC using prompt mode')
    parser.add_argument('-l', '--nolog', action='store_true', help='disable logging to console')
    args = parser.parse_args()
    
    if args.nolog:
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.INFO)
    
    smc_url = smc_key = None    
    if args.interactive:
        print "Not Yet Implemented, enter interactive mode"
    elif args.yaml:
        with open(args.yaml, 'r') as stream:
            try:
                data = yaml.safe_load(stream)
                awscfg = AWSConfig(**data.get('AWS'))
                ngfw = NGFWConfiguration(**data.get('NGFW'))
                smc = data.get('SMC')
                if smc:
                    smc_url = smc.get('url')
                    smc_api_key = smc.get('key')
            except yaml.YAMLError as exc:
                print(exc)  

    if smc_url and smc_api_key:
        session.login(url=smc_url, api_key=smc_api_key)
    else: #from ~.smcrc
        session.login()
   
    """
    Strategy to obtain credentials for EC2 operations (in order):
    * Check for region in yaml
    * Check for region in AWS boto3 client locations
    * Prompt for region
    * Use access_key and secret_key configured in YAML
    * Use access_key and secret_key configuration in AWS boto3 client locations
    For more on boto3 credential locations, see:   
    http://boto3.readthedocs.io/en/latest/guide/quickstart.html#configuration
    """
    ec2 = None 
    try:
        ec2 = boto3.resource('ec2', region_name=awscfg.aws_region)
    
    except botocore.exceptions.NoRegionError:
        aws_session = boto3.session.Session()
        awscfg.aws_region = menu(aws_session.get_available_regions('ec2'), 'Enter a region:')
    
    if awscfg.aws_access_key_id and awscfg.aws_secret_access_key: 
        ec2 = boto3.resource('ec2',
                             aws_access_key_id = awscfg.aws_access_key_id,
                             aws_secret_access_key=awscfg.aws_secret_access_key,
                             region_name=awscfg.aws_region)
    else:
        ec2 = boto3.resource('ec2', region_name=awscfg.aws_region)

    if args.delete:
        vpcs = [x.id +' '+ x.cidr_block for x in ec2.vpcs.filter()]
        choice = menu(vpcs, "Enter a VPC to remove: ")
        vpc = VpcConfiguration(choice.split(' ')[0]).load()
        vpc.rollback()
        
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
    vpc = VpcConfiguration.create(vpc_subnet=awscfg.vpc_subnet)
    try:
        vpc.create_network_interface(0, awscfg.vpc_public, description='public-ngfw') 
        vpc.create_network_interface(1, awscfg.vpc_private, description='private-ngfw')
        vpc.authorize_security_group_ingress('0.0.0.0/0', ip_protocol='-1')
        
        userdata = ngfw.create(vpc.ngfw_interfaces, vpc.ngfw_gateway).initial_contact()
        
        
        instance = vpc.launch(key_pair=awscfg.aws_keypair, userdata=userdata, 
                              imageid=awscfg.ngfw_ami,
                              instance_type=awscfg.aws_instance_type)

        ngfw.add_contact_address(vpc.elastic_ip)
        ngfw.engine.rename('{} ({})'.format(instance.id, vpc.availability_zone))
        ngfw.queue_policy()
        
        for message in waiter(instance, 'running'):
            logger.info(message)

        if awscfg.aws_client and awscfg.aws_client_ami:
            spin_up_host(awscfg.aws_keypair, vpc, awscfg.aws_instance_type, 
                         awscfg.aws_client_ami)

        logger.info("Elastic (public) IP address is set to: {}, ngfw instance id: {}"
                    .format(vpc.elastic_ip, instance.id))

        logger.info("To connect to your AWS instance, execute the command: "
                    "ssh -i {}.pem aws@{}".format(instance.key_name, vpc.elastic_ip))

        start_time = time.time()
        ngfw.monitor_status()
        print("--- %s seconds ---" % (time.time() - start_time))
                  
    except (botocore.exceptions.ClientError, CreateEngineFailed) as e:
        logger.error("Caught exception, rolling back: {}".format(e))
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
    session.logout()
    