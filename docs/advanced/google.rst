Google Cloud Storage
====================

:class:`.GoogleStorageDriver` is a wrapper around `google-cloud-storage <https://googlecloudplatform.github.io/google-cloud-python/stable/storage-client.html>`_.


Connecting
----------

The driver will check for `GOOGLE_APPLICATION_CREDENTIALS` environment variable
before connecting. If not found, the driver will use service worker credentials
json file path passed to `key` argument.

.. code-block:: python

    from cloudstorage.drivers.google import GoogleStorageDriver

    credentials_json_file = '/path/cloud-storage-service-account.json'
    storage = GoogleStorageDriver(key=credentials_json_file)
    # <Driver: GOOGLESTORAGE>


Access Control List (ACL)
-------------------------

By default, all containers and blobs default to `project-private`. To change
the access control when creating a container or blob, include the `acl`
argument:

.. code-block:: python

    container = storage.create_container('container-public', acl='public-read')
    container.cdn_url
    # https://storage.googleapis.com/container-public

.. code-block:: python

    container = storage.get_container('container-public')
    picture_blob = container.upload_blob('/path/picture.png', acl='public-read')
    picture_blob.cdn_url
    # https://storage.googleapis.com/container-public/picture.png

Support ACL values for Google Cloud Storage:

* private
* public-read
* public-read-write
* authenticated-read
* bucket-owner-read
* bucket-owner-full-control
* project-private

.. WARNING::
    Updating ACL on an existing container or blob is not currently supported.


Content Delivery Network (CDN)
------------------------------

Calling :meth:`container.enable_cdn` will make the container public
(shared publicly). More information available at `Making Data Public
<https://cloud.google.com/storage/docs/access-control/making-data-public>`_.
