Microsoft Azure Storage
=======================

Microsoft :class:`.AzureStorageDriver` is a wrapper around
`Azure Storage SDK for Python <http://https://azure-storage.readthedocs.io/>`_.


Connecting
----------

.. code-block:: python

    from cloudstorage.drivers.microsoft import AzureStorageDriver

    storage = AzureStorageDriver(account_name='<my-azure-account-name>',
               key='<my-azure-account-key>')
    # <Driver: AZURE>


Access Control List (ACL)
-------------------------

By default, all containers and blobs default to `private` (public read access).
The following container permissions are supported: `container-public-access`
(full public read access) and `blob-public-access`
(public read access for blobs only).

.. code-block:: python

    container = storage.create_container('container-public',
                                         acl='container-public-access')
    container.cdn_url
    # https://s3.amazonaws.com/container-public

Support ACL values for Azure:

* private
* container-public-access
* blob-public-access

.. WARNING::
    Updating ACL on an existing container is not currently supported.
