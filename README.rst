Cloud Storage
=============

.. image:: https://img.shields.io/pypi/v/cloudstorage.svg
    :target: https://pypi.python.org/pypi/cloudstorage

.. image:: https://img.shields.io/pypi/l/cloudstorage.svg
    :target: https://pypi.python.org/pypi/cloudstorage

.. image:: https://img.shields.io/pypi/pyversions/cloudstorage.svg
    :target: https://pypi.python.org/pypi/requests

.. image:: https://travis-ci.org/scottwernervt/cloudstorage.svg?branch=master
    :target: https://travis-ci.org/scottwernervt/cloudstorage

`Cloud Storage`_ is a Python +3.4 package which creates a unified API for the
cloud storage services: Amazon Simple Storage Service (S3), Rackspace Cloud
Files, Google Cloud Storage, and the Local File System.

Cloud Storage is inspired by `Apache Libcloud <https://libcloud.apache.org/>`_.
Advantages to Apache Libcloud Storage are:

* Full Python 3 support.
* Generate temporary signed URLs for downloading and uploading files.
* Support for request and response headers like Content-Disposition.
* Pythonic! Iterate through all blobs in containers and all containers in
  storage using respective objects.

Usage
-----

.. code-block:: python

    >>> from cloudstorage.drivers.amazon import S3Driver
    >>> storage = S3Driver(key='<my-aws-access-key-id>', secret='<my-aws-secret-access-key>')

    >>> container = storage.create_container('avatars')
    >>> container.cdn_url
    'https://avatars.s3.amazonaws.com/'

    >>> avatar_blob = container.upload_blob('/path/my-avatar.png')
    >>> avatar_blob.cdn_url
    'https://s3.amazonaws.com/avatars/my-avatar.png'

    >>> avatar_blob.generate_download_url(expires=3600)
    'https://avatars.s3.amazonaws.com/my-avatar.png?'
    'AWSAccessKeyId=<my-aws-access-key-id>'
    '&Signature=<generated-signature>'
    '&Expires=1491849102'

    >>> container.generate_upload_url('user-1-avatar.png', expires=3600)
    {
        'url': 'https://avatars.s3.amazonaws.com/',
        'fields': {
            'key': 'user-1-avatar.png',
            'AWSAccessKeyId': '<my-aws-access-key-id>',
            'policy': '<generated-policy>',
            'signature': '<generated-signature>'
        }
    }

Supported Services
------------------

* `Amazon S3`_
* `Google Cloud Storage`_
* Local File System
* `Rackspace CloudFiles`_


Installation
------------

To install Cloud Storage:

.. code-block:: bash

    pip install cloudstorage

.. _`Amazon S3`: http://aws.amazon.com/s3/
.. _`Blackblaze B2 Cloud Storage`: https://www.backblaze.com/b2/Cloud-Storage.html
.. _`Google Cloud Storage`: https://cloud.google.com/storage/
.. _`Microsoft Azure Storage`: https://azure.microsoft.com/services/storage/
.. _`Rackspace CloudFiles`: https://www.rackspace.com/cloud/files
.. _`Cloud Storage`: https://github.com/scottwernervt/cloudstorage
