'''
Created on Aug 11, 2016

@author: davidlepage

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
 
'''

from pprint import pprint
import re
import time
import boto3
from smc.api.session import session
from smc.elements.engines import AWSLayer3Firewall

smc_public_ip = '73.88.56.153'  #Hack initial_contact file; Locations are not configurable via SMC API
instance_type='t2.micro'
ngfw_6_0_2 = 'ami-34a26b54'
            
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
     
    :param vpcid: VPC id
    """ 
    def __init__(self, vpcid=None):
        self.vpcid = vpcid
        self.vpc = None #: Reference to VPC
        self.alt_route_table = None
        self.network_interface = [] #: interface idx, network ref
        self.availability_zone = set()
  
    def load(self):
        if not self.vpcid:
            default_vpc = ec2.vpcs.filter(Filters=[{
                                        'Name': 'isDefault',
                                        'Values': ['true']}])
            for v in default_vpc:
                self.vpc = v
        else:
            self.vpc = ec2.Vpc(self.vpcid)
 
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
        :param instance_tenancy: 'default'|'dedicated'|'host'
        :returns: self
        """
        vpc_new = ec2.create_vpc(CidrBlock=vpc_subnet,
                                 InstanceTenancy=instance_tenancy)
        print "Created VPC: {}".format(vpc_new.vpc_id)
        
        vpc = VpcConfiguration(vpc_new.vpc_id).load() 
        
        igw = ec2.create_internet_gateway()
        print "Created internet gateway: {}".format(igw.id)
        
        igw.attach_to_vpc(VpcId=vpc.vpc.vpc_id)
        
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
        be bound to the AWS Internet GW for inbound / outbound routing.
        
        :param interface_id: id to assign interface
        :type interface_id: int
        :param cidr_block: cidr of subnet
        :param availability_zone: optional
        :param description: description on interface
        :raises: botocore.exception.ClientError
        """
        subnet = self.create_subnet(cidr_block)
        interface = subnet.create_network_interface(Description=description)
        
        #Disable source / dest check
        interface.modify_attribute(SourceDestCheck={'Value': False})
        
        #Assign elastic to eth0
        if interface_id == 0:
            allocation_id = self.allocate_elastic_ip()
            address = ec2.VpcAddress(allocation_id)
            address.associate(NetworkInterfaceId=interface.network_interface_id)
        #else:
        #    self.private_subnets.append(subnet) #track private subnets
            
        print "Created network interface: {}, subnet_id: {}, private address: {}".\
                format(interface.network_interface_id, interface.subnet_id,
                       interface.private_ip_address)
    
        self.availability_zone.add(interface.availability_zone) 
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
        igw = self.internet_gateway().id
    
        def_route.create_route(
                    DestinationCidrBlock='0.0.0.0/0',
                    GatewayId=igw)
 
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
        eip = ec2.meta.client.allocate_address(Domain='vpc')
        return eip.get('AllocationId')
    
    def internet_gateway(self):
        """ 
        Get the internet gateway
        :return: InternetGateway
        """
        for igw in self.vpc.internet_gateways.all():
            return igw
            
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
        if not self.alt_route_table: 
            print "Route table doesn't exist!"
            #No alt route found, check for non-default route tables to use, or
            #that may already be used, or create a new one
            for rt in vpc.vpc.route_tables.filter(Filters=[{
                                        'Name': 'association.main',
                                        'Values': ['false']}]):
                print "non_default: %s" % rt
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
        
        #TODO: Could more than 1 security group be applied? 
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
        :returns: list of dictionarys representing NGFW interface
        """
        interfaces = []
        for intf in self.network_interface:
            for idx, obj in intf.iteritems():
                interfaces.append({'interface_id': idx,
                                    'address': obj.private_ip_address,
                                    'network_value': obj.subnet.cidr_block})
        return interfaces
                  
    def rollback(self):
        """ 
        In case of failure, convenience to wrap in try/except and remove
        the VPC. If there is a running EC2 instance, you must delete that
        first.
        """
        self.vpc.delete()
                       
    def launch(self, key_pair, userdata=None, 
               imageid=ngfw_6_0_2, 
               availability_zone='us-west-2b'):
        """
        Launch the instance
        
        :param key_name: keypair required to enable SSH to AMI
        :param userdata: optional, but recommended
        :param imageid: NGFW AMI id
        :param availability_zone: where to launch instance
        :return: instance id
        """
        verify_key_pair(key_pair) #exception raised here
        az = next(iter(self.availability_zone))
        print "Launching instance into availability zone: {}".format(az)
          
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
                                        Placement={'AvailabilityZone': az},
                                        NetworkInterfaces=interfaces,
                                        UserData=userdata
                                        )
        
        for aws_ngfw in instance:
            print "Instance name: %s" % aws_ngfw.instance_id
            return aws_ngfw.instance_id
        
def verify_key_pair(key_pair):
    """ 
    Verifies key pair before launching AMI
    :raises: botocore.exception.ClientError 
    """
    ec2.meta.client.describe_key_pairs(KeyNames=[key_pair])
        
def wait_for_ready(instance):
    """ Generator to monitor the startup of the launched AMI 
    :param instance: instance ID to monitor during startup
    :returns: generator message updates waiting for state 'running'
    """
    while True:
        status = ec2.meta.client.describe_instance_status(\
                                    InstanceIds=[instance],
                                    Filters=[{'Name': 'instance-state-name',
                                              'Values': ['running']}])
        if not status.get('InstanceStatuses'):
            yield "Waiting for image to become ready...."
            time.sleep(5)
        else:
            yield "Image in running state!"
            break

def create_ngfw_in_smc(name, interfaces, 
                       domain_server_address=None,
                       default_nat=True):
    """ 
    Create NGFW instance in SMC, bind the license and return the 
    initial_contact info which will be fed to the AWS launcher as 
    UserData.
    The NGFW will be configured to enable Default NAT for outbound.
    
    :param name: name of ngfw in smc
    :param interfaces: list of interfaces from VpcConfiguration
    :param domain_server_address: (optional) dns address for engine
    :type domain_server_address: list
    :param default_nat: (optional: default True) whether to enable default NAT
    
    See :py:class:`smc.elements.engines.AWSLayer3Firewall` for more info
    """
    global engine
    engine = AWSLayer3Firewall.create(name, 
                                      interfaces,  
                                      domain_server_address=domain_server_address,
                                      default_nat = True)
    print "Created NGFW..."
    engine.bind_license() 
    #engine.upload(policy='Layer 3 Virtual Firewall Policy') #queue policy
    content = engine.initial_contact(enable_ssh=True)
    return re.sub(r"management-address string (.+)", "management-address string " + \
                  smc_public_ip, content)

def change_ngfw_name(instance_id):
    """ Change the engine name to match the InstanceId on Amazon
         
    :param instance_id: instance ID obtained from AWS run_instances 
    """
    engine.change_name(instance_id)
        
if __name__ == '__main__':
    
    session.login(url='http://172.18.1.150:8082', api_key='xxxxxxxxxxxxxxxxxxxxxx')
    
    import smc.actions.remove
    smc.actions.remove.element('aws-02', 'single_fw')

    ec2 = boto3.resource('ec2', 
                         region_name='us-west-2')
    '''
    Use Case 1: Create entire VPC and deploy NGFW
    ---------------------------------------------
    This will fully create a VPC and associated requirements. 
    The following will occur:
    * A new VPC will be created in the AZ based on boto3 client connection
    * Two network subnets are created in the VPC, one public and one private
    * Two network interfaces are created and assigned to the subnets
    * An elastic IP is created and attached to the public network interface
    * A route is created in the default route table for the public interface to
      route 0.0.0.0/0 to the IGW
    * The default security group is modified to allow inbound access from 0.0.0.0/0
      to to the NGFW network interface
      :py:func:`VpcConfiguration.authorize_security_group_ingress`
    * A secondary route table is created with a default route to 0.0.0.0/0 with a next
      hop of the private network interface assigned to NGFW
    * The NGFW is automatically created and UserData is obtained for AMI instance launch
    * AMI is launched using UserData to allow auto-connection to NGFW SMC Management
    * NGFW receives queued policy and becomes active
    
    .. note: The AZ used during instance spin up is based on the AZ that is auto-generated
             by AWS when the interface is created. If you require a different AZ, set the 
             attribute :py:class:`VpcConfiguration.availability_zone` before called launch. 
    '''
    '''
    vpc = VpcConfiguration.create(vpc_subnet='192.168.3.0/24')
    vpc.create_network_interface(0, '192.168.3.240/28', description='public-ngfw') 
    vpc.create_network_interface(1, '192.168.3.0/25', description='private-ngfw')
    vpc.associate_alt_route_to_subnets()
    vpc.authorize_security_group_ingress('0.0.0.0/0', ip_protocol='-1')
    
    userdata = create_ngfw_in_smc(name='aws-02', 
                                  interfaces=vpc.build_ngfw_interfaces(),
                                  domain_server_address=['8.8.8.8', '8.8.4.4'])
    
    instance = vpc.launch(key_pair='aws-ngfw', userdata=userdata)
    for message in wait_for_ready(instance):
        print message
    '''
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
    
    pprint(vars(vpc))
    
    session.logout()
    