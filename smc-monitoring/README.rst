|Documentation Status| |PyPI version|

Monitoring API for Stonesoft Security Management Center
=======================================================

smc-python-monitoring is made of up two core capabilities:

- Monitor, Query or view live events from the SMC
- Pub/Sub (Subscribe) to SMC element events by supported API type

The smc-python-monitoring API makes it possible to obtain real time monitoring information from the SMC with respects to:

* Logs
* Connections
* Blacklist
* Routing
* Users
* SSL VPN Users
* VPNs
* Alerts

This correlates to the area of the SMC under "Monitoring".

Every query can be refined by using filters that allow a variety of boolean operations to control the results.

The smc-python-monitoring API also provides the ability to subscribe to element event changes in the SMC.
Any element type that is exposed as an SMC API `entry point` can be used as a subscriber target. Event type
examples that would fire events would be created, updated, or deleted (for example - although not an exhaustive
list). 

Compatibility
=============

Requires Security Management Center version 6.2 or newer.

This package has been tested with Python 2.7, 3.4 and 3.5.

Requirements
============

smc-python >= v0.5.6

websocket-client

Install
=======

``pip install smc-python-monitoring``

Usage
=====

In order to leverage monitoring or subscriber features, you must first obtain a valid smc session as 
normal:

.. code:: python

	from smc import session
	session.login()
	...

Once a valid session is obtained, the session information is re-used for the web socket connection,
including SSL related data such as validating SSL through the client side SSL certificate before
establishing the connection.

Monitoring and Queries
++++++++++++++++++++++

Making queries is uniform across all query types.
There are small exceptions to this rule with respects to LogQuery which provides more options on how to control
the batched query size, custom time ranges for the query, etc. See documentation on LogQuery for more details.

A return data format for queries can be configured when calling fetch on the query. Results can be obtained
in a variety of formatted outputs such as CSV, Table format or as a raw dict. You can also provide your own
formatter to the query. See ``smc_monitoring.models.formatter`` for more info.

By default each query type has a pre-defined set of ``field_ids`` that define a basic set of fields for
the query type. This specifies which fields are returned in the query. You can customize these fields on the
query by using the ``query.format.field_names`` or ``query.format.field_ids`` methods. See the documentation for
more info.

All queries can be made as each 'batch' queries or 'live' style queries. The type used depends on the method
called on the query instance. All queries done via smc-python-monitoring follow the same rules as implemented in
the SMC UI. 

For example, 'Monitoring' queries (i.e. Connections, Blacklist, Users, etc) do not allow time/date
ranges on the query, however filtering by fields work. The same field filtering works in the same way with Log
style queries.

Example of making a basic log query in real time. Note the default return format is Table for a cleaner output,
assuming this is being run from a command window:

.. code:: python

	query = LogQuery()
	for log in query.fetch_live():
	    print(log)

Making a simple LogQuery with a fetch size of 50 and returning in a raw dict format:

.. code:: python

	query = LogQuery(fetch_size=50)
	for log in query.fetch_raw():
    	    print(log)

Making a more sophisticated query that uses a timezone, then adds an "AND" filter that
will match if the entry has an alert severity of "HIGH" and only if the ACTION and APPLICATION
fields have values:

.. code:: python

	query = LogQuery(fetch_size=50)
	query.format.timezone('CST')
	
	query.add_and_filter(
            [InFilter(FieldValue(LogField.ALERTSEVERITY), [ConstantValue(Alerts.HIGH)]),
             DefinedFilter(FieldValue(LogField.ACTION)),
	     DefinedFilter(FieldValue(LogField.IPSAPPID))])
    
	for log in query.fetch_batch(TableFormat):
	    print(log)


Query for the last 10 records if the source IP is 192.168.4.84 and return only fields
timestamp, source, destination and service:

.. code:: python

	query = LogQuery(fetch_size=10)
	query.format.timezone('CST')
   
	query.format.field_ids([LogField.TIMESTAMP, LogField.SRC, LogField.DST, LogField.IPSAPPID])
    
	query.add_and_filter(
	    [InFilter(FieldValue(LogField.SRC), [IPValue('192.168.4.84')]),
	     DefinedFilter(FieldValue(LogField.IPSAPPID))])
    
	for log in query.fetch_batch(TableFormat):
	    ...


Examples of other monitoring type queries:

Obtain all current connections on a given engine. Output in CSV:

.. code:: python
	
	query = ConnectionQuery('sg_vm')
	for record in query.fetch_batch(CSVFormat):
	    print(record)

Obtain all authenticated users on a given engine, output as 'User' object instances:

.. code:: python

	query = UserQuery('sg_vm')
	for record in query.fetch_as_element():
	    print(record)

Obtain all VPN SA's on given engine, output at 'VPNSecurityAssoc' object instances:

.. code:: python

	query = VPNSAQuery('sg_vm')
	for record in query.fetch_as_element():
	    print(record)

Obtain all current routes for a given engine, output as a list of raw dict items:

.. code:: python

	query = RoutingQuery('sg_vm')
	for record in query.fetch_batch(RawDictFormat):
	    print(record)
		
Obtain all SSL VPN connections for a given engine, output in table format:

.. code:: python

	query = SSLVPNQuery('sg_vm')
	for record in query.fetch_batch(TableFormat):
	    print(record)

Obtain all active alerts from the Shared Domain:

.. code:: python

	query = ActiveAlertQuery('Shared Domain', timezone='America/Chicago')
	for record in query.fetch_batch():
        print(record)
 	
	    
Subscribing to Events
+++++++++++++++++++++

Using smc-python-monitoring you can also subscribe to events published by the SMC API
when changes are made. As long as the entry point exists for the element type, you can
set up a "channel" to receive real-time updates when the element type is modified.

To listen for events you must first obtain an SMC session as usual.

Then obtain an instance of `Notification`, specifying the events of interest.

Subscribe to a single element event (SMC api entry point):

.. code:: python

	notification = Notification('network')

Subscribe to multiple element events on a single channel (subscription_id):

.. code:: python

	notification = Notification('network,host,iprange')

Subscribe to multiple element events, each with it’s own channel (subscription_id):

.. code:: python

	notification = Notification('network')
	notification.subscribe('host')
	notification.subscribe('layer2_policy')

Return the events as instance of “Event” (optional). Otherwise raw json returned.

.. code:: python

	for event in notification.notify(as_type=Event):
   		print(event)

	Event(subscription_id=151,action=delete,element=https://xxxx/elements/host/1087)
	Event(subscription_id=152,action=delete,element=https://xxxx/elements/layer2_policy/27)

.. |Documentation Status| image:: https://readthedocs.org/projects/smc-python/badge/?version=latest
   :target: http://smc-python.readthedocs.io/en/latest/?badge=latest
.. |PyPI version| image:: https://badge.fury.io/py/smc-python-monitoring.svg
   :target: https://badge.fury.io/py/smc-python-monitoring
