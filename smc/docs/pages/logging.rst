Logging
-------

The smc-python API uses python logging for INFO, ERROR and DEBUG logging levels. If needed, add the
following to your classes:

.. code-block:: python

   import logging
   logging.getLogger()
   logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(levelname)s: %(message)s')
   
.. note:: This is a recommended setting initially as it enables detailed logging of each call as it is
		  processed through the API. It also includes the backend web based calls initiated by the 
		  requests module.

If you simply require stream logging to console for scripts, from your script import the smc module
set_stream_logger, debug level, and optional format string conforming to the logging module:

.. code-block:: python

   from smc import set_stream_logger
   set_stream_logger(level=logging.DEBUG, format_string=None)
   