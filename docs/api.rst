*************
API Reference
*************


Base
====

.. toctree::
   :maxdepth: 1

   api/blob
   api/container
   api/driver


Drivers
=======

.. toctree::
   :maxdepth: 1

   api/rackspace
   api/google
   api/local
   api/amazon


Helper Functions
================

.. automodule:: cloudstorage.helpers
    :members:


Utility Functions
=================

.. automodule:: cloudstorage.utils
    :members:


Exceptions
==========

.. automodule:: cloudstorage.exceptions
    :members:
    :member-order: bysource


Logging
=======
By default, Cloud Storage logs to :class:`logging.NullHandler`. To attach a log
handler:

.. code-block:: python

    import logging

    logger = logging.getLogger('cloudstorage')
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s.%(funcName)s - %(levelname)s - %(message)s')

    ch.setFormatter(formatter)
    logger.addHandler(ch)
