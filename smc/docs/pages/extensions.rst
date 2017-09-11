Extensions
==========

smc-python provides additional extensions to extend the base library.
Extensions are installed as separate packages and will have the dependency on the base
smc-python library.

Available extensions:

- smc-python-monitoring


smc-python-monitoring
---------------------

smc-python-monitoring API provides a monitoring interface to the SMC to perform queries for
dynamic engine components such as blacklists, connections, routes, vpn's, users and logs.

Capabilities in the API implement the functionality found in the SMC Log Viewer and engine
level monitoring.

Query
+++++

.. automodule:: smc_monitoring.models.query
	:members:

Models
++++++

.. automodule:: smc_monitoring.models

Filters
*******

.. automodule:: smc_monitoring.models.filters
	:members:
	:show-inheritance:

Values
******

.. automodule:: smc_monitoring.models.values
	:members:
	:show-inheritance:

Formats
*******

.. automodule:: smc_monitoring.models.formats
	:members:
	:show-inheritance:

Constants
*********

.. automodule:: smc_monitoring.models.constants
	:members:
	:show-inheritance:
	
Formatters
**********

.. automodule:: smc_monitoring.models.formatters
	:members:
	:show-inheritance:

TimeRanges
**********

.. automodule:: smc_monitoring.models.calendar
	:members:
	:show-inheritance:

Monitors
++++++++

.. automodule:: smc_monitoring.monitors

Blacklist
*********

.. automodule:: smc_monitoring.monitors.blacklist
	:members:
	:show-inheritance:

Connections
***********

.. automodule:: smc_monitoring.monitors.connections
	:members:
	:show-inheritance:
	:inherited-members:

Logs
****

.. automodule:: smc_monitoring.monitors.logs
	:members:
	:show-inheritance:

Routes
******

.. automodule:: smc_monitoring.monitors.routes
	:members:
	:show-inheritance:
	
SSLVPN
******

.. automodule:: smc_monitoring.monitors.sslvpn
	:members:
	:show-inheritance:

Users
*****

.. automodule:: smc_monitoring.monitors.users
	:members:
	:show-inheritance:

VPNs
****

.. automodule:: smc_monitoring.monitors.vpns
	:members:
	:show-inheritance:



