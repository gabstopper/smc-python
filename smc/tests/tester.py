#!/usr/bin/python

import smc
import logging
from pprint import pprint


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

smc.login('http://172.18.1.150:8082', 'EiGpKD4QxlLJ25dbBEp20001')

#Test blacklist
blacklist = smc.web_api.get_all_entry_points()
print blacklist

for bl in blacklist:
    if bl['rel'] == 'blacklist':
        print "Blacklist to HREF: %s" % bl

#Find BL
fw = smc.search.filter_by_type('fw_cluster', 'sg_vm')
d = smc.search.get_element_by_href(fw['href'])
pprint(d)
for e in d['link']:
    if e['rel'] == 'blacklist':
        print "Blacklist entry: %s" % e
        #f = smc.search.get_element_by_href(e['href'])
  
#pprint(d)
smc.logout()
