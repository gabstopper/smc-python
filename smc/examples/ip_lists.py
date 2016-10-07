"""
Example script to create an empty IP List, create an IPList with contents provided as
a python list, download an IP List in a specified format (txt, json or zip), 
and upload an IP List. 

IP Lists are a new network element supported in SMC API and engines at version 6.1 or newer. 
These allow for individual IP addresses or network addresses, one per line, and can be used 
in the source/destination fields of an engine policy.

IPList operations are done by downloading the existing IPList (after creation), modifying
the list contents and uploading back to SMC. 

.. note:: Contents of the uploaded IPList will replace the existing contents of the IPList
          with the same name on the SMC. 
          
For upload, a content-type of 
multipart/form-data is required with the exception of modifying an IPList as json. The 
header type setting is handled by smc-python automatically.

File format for the IPList is::

    1.1.1.0/24
    2.2.2.2
    3.3.3.3
    4.4.4.4
    5.5.5.5
    6.6.6.1-6.6.6.254
    aaaa:bbbb::cccc
    aaaa:bbbb::/32
    aaaa:bbbb::
    ...

Requirements:
* smc-python >= 0.3.3
* Stonesoft Management Center >= 6.1

"""
from smc import session
from smc.elements.element import IPList
from smc.elements.collection import describe_ip_lists

def upload_as_zip(name, filename):
    """
    Upload an IPList as a zip file. Useful when IPList is very large.
    This is the default upload format for IPLists.
    
    :param str name: name of IPList
    :param str filename: name of zip file to upload, full path
    :return: :py:class:`smc.api.web.SMCResult`
    """
    location = describe_ip_lists(name=[name])
    if location:
        iplist = location[0]
        result = iplist.upload(filename=filename)
        return result

def upload_as_text(name, filename):
    """ 
    Upload the IPList as text from a file.
    
    :param str name: name of IPList
    :param str filename: name of text file to upload
    :return: :py:class:`smc.api.web.SMCResult`
    """
    location = describe_ip_lists(name=[name])
    if location:
        iplist = location[0]
        result = iplist.upload(filename=filename, as_type='txt')
        return result

def upload_as_json(name, mylist):
    """
    Upload the IPList as json payload. 
    
    :param str name: name of IPList
    :param list: list of IPList entries
    :return: :py:class:`smc.api.web.SMCResult`
    """
    location = describe_ip_lists(name=[name])
    if location:
        iplist = location[0]
        result = iplist.upload(json=mylist, as_type='json')
        return result

def download_as_zip(name, filename):
    """
    Download IPList with zip compression. Recommended for IPLists
    of larger sizes. This is the default format for downloading
    IPLists.
    
    :param str name: name of IPList
    :param str filename: name of filename for IPList
    """
    location = describe_ip_lists(name=[name])
    if location:
        iplist = location[0]
        result = iplist.download(filename=filename)
        return result

def download_as_text(name, filename):
    """
    Download IPList as text to specified filename.
    
    :param str name: name of IPList
    :param str filename: name of file for IPList download
    """
    location = describe_ip_lists(name=[name])
    if location:
        iplist = location[0]
        result = iplist.download(filename=filename, as_type='txt')
        return result

def download_as_json(name):
    """
    Download IPList as json. This would allow for easily 
    manipulation of the IPList, but generally recommended only for
    smaller lists
    
    :param str name: name of IPList
    :return: :py:class:`smc.api.web.SMCResult`
    """
    location = describe_ip_lists(name=[name])
    if location:
        iplist = location[0]
        result = iplist.download(as_type='json')
        return result.json
                
def create_iplist(name):
    """
    Create an empty IPList as name
    
    :param str name: name of IPList
    :return: :py:class:`smc.api.web.SMCResult`
    """
    iplist = IPList(name=name).create()
    return iplist

def create_iplist_with_data(name, iplist):
    """
    Create an IPList with initial list contents.
    
    :param str name: name of IPList
    :param list iplist: list of IPList IP's, networks, etc
    :return: :py:class:`smc.api.web.SMCResult`
    """
    iplist = IPList(name=name, iplist=iplist).create()
    return iplist
                   
if __name__ == '__main__':

    session.login(url='http://172.18.1.25:8082', api_key='gxJ8WugtuNB5ztvl7HUz0001', timeout=120)
    
    
    #print upload_as_text('mylist', '/Users/davidlepage/git/smc-python/src/smc/examples/ip_addresses')
    
    #print upload_as_json('mylist', {'ip': ['1.1.1.1', '2.2.2.2', '3.3.3.3']})
    
    #print upload_as_zip('mylist', '/Users/davidlepage/git/smc-python/src/smc/examples/iplist.zip')
    
    #print create_iplist(name='newlist')
    
    #print create_iplist_with_data(name='abrandnewlist', iplist=['123.123.123.123','23.23.23.23'])
    
    #print download_as_text('mylist', filename='/Users/davidlepage/iplist.txt')
    
    #print download_as_zip('mylist', filename='/Users/davidlepage/iplist.zip')

    #print download_as_json('mylist')
    
    session.logout()
    
    