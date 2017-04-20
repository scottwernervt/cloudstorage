Rackspace Cloud Files
=====================

Rackspace :class:`.CloudFilesDriver` extends `rackspacesdk
<https://pypi.python.org/pypi/rackspacesdk>`_ which is a wrapper around
`OpenStack SDK <https://pypi.python.org/pypi/openstacksdk>`_.


Connecting
----------

Change region from default Northern Virginia (`IAD`) to Dallas-Fort Worth
(`DFW`):

.. code-block:: python

    from cloudstorage.drivers.rackspace import CloudFilesDriver

    storage = CloudFilesDriver(key='<my-rackspace-username>',
                               secret='<my-rackspace-secret-key>',
                               region='DFW')
    # <Driver: CLOUDFILES IAD>

Regions supported:

* Dallas-Fort Worth (`DFW`)
* Chicago (`ORD`)
* Northern Virginia (`IAD`)
* London (`LON`)
* Sydney (`SYD`)
* Hong Kong (`HKG`)


Access Control List (ACL)
-------------------------

.. warning:: Cloud Storage does not currently support canned Access Control
             List (ACL) for Containers and Blobs.


Content Delivery Network (CDN)
------------------------------

You must enable CDN on the container before accessing a blob's CDN URL.

.. code-block:: python

    container = storage.create_container('container-public')
    container.enable_cdn()
    # True
    container.cdn_url
    # https://XXXXXX-XXXXXXXXXXXX.ssl.cf5.rackcdn.com

    picture_blob = container.upload_blob('/path/picture.png')
    picture_blob.cdn_url
    # https://XXXXXX-XXXXXXXXXXXX.ssl.cf5.rackcdn.com/picture.png
