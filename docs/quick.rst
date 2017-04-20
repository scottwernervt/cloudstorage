***********
Quick Start
***********


Basic Terminology
=================

* Blobs are objects, keys, or files.
* Containers (buckets) manage blobs.
* Storage Driver initiates a connection to the storage backend and manage
  containers.


Connecting to Storage
=====================

Let's start with creating a Local File System storage driver (replace `key`
argument with a folder path of your choosing):

.. code-block:: python

    from cloudstorage.drivers.local import LocalDriver

    storage = LocalDriver(key='/home/webapp/storage', secret='<my-secret>')
    # <Driver: LOCAL>

Alternatively, the driver can be initialized with its name. This is useful if
you have different configurations for testing vs production. For example, a
Flask app might use the `LOCAL` driver for testing and `S3` for production.

.. code-block:: python

    from cloudstorage import get_driver_by_name

    driver_cls = get_driver_by_name('LOCAL')
    storage = driver_cls(key='/home/webapp/storage', secret='<my-secret>')
    # <Driver: LOCAL>

Creating a Container
====================

Creating a container:

.. code-block:: python

    container = storage.create_container('container-name')
    # <Container container-name LOCAL>


Accessing a Container
=====================

Getting a container:

.. code-block:: python

    container = storage.get_container('container-name')
    # <Container container-name LOCAL>


Deleting a Container
====================

All of the blob objects in a container must be deleted before the container
itself can be deleted:

.. code-block:: python

    container = storage.get_container('container-name')

    for blob in container:
        blob.delete()

    container.delete()


Uploading a Blob
================

Storing data from a file, stream, or string:

.. code-block:: python

    picture_path = '/path/picture.png'
    picture_blob = container.upload_blob(picture_path)
    # <Blob picture.png container-name LOCAL>

.. code-block:: python

    with open('/path/picture.png', 'rb') as picture_file:
        picture_blob = container.upload_blob(picture_file, blob_name='picture.png')
        # <Blob picture.png container-name LOCAL>

Cloud Storage will attempt to guess the uploaded file's `Content-Type` using
:mod:`mimetypes` and `python-magic <https://github.com/ahupp/python-magic>`_.
The `Content-Type` can be overridden with the `content_type` argument:

.. code-block:: python

    with open('/path/picture.png', 'rb') as picture_file:
        picture_blob = container.upload_blob(filename=picture_file,
                                             content_type='application/octet-stream')
        # <Blob picture.png container-name LOCAL>
        picture_blob.content_type
        # 'application/octet-stream'

.. important:: Always use read binary mode `rb` when uploading a file like
               object.

.. warning:: The effect of uploading to an existing blob depends on
    the “versioning” and “lifecycle” policies defined on the blob’s
    container. In the absence of those policies, upload will overwrite
    any existing contents. As of now, Cloud Storage does not supporting
    versioning/generation.


Accessing a Blob
================

To get a blob from a container and its attributes:

.. code-block:: python

    container = storage.get_container('container-name')
    picture_blob = container.get_blob('picture.png')
    picture_blob.name
    # 'picture.png'
    picture_blob.size
    # 50301
    picture_blob.checksum
    # '2f907a59924ad96b7478074ed96b05f0'
    picture_blob.etag
    # 'bf506fc6ffbc3c4a2756eac85a0b4d2f3f227fee'
    picture_blob.content_type
    # 'image/png'
    picture_blob.created_at
    # datetime.datetime(2017, 4, 19, 18, 38, 26, 335373)


Downloading a Blob
==================

Downloading a blob data to a file path:

.. code-block:: python

    picture_blob = container.get_blob('picture.png')
    picture_blob.download('/path/picture-copy.png')

Or to a file like object:

.. code-block:: python

    picture_blob = container.get_blob('picture.png')
    with open('/path/picture-copy.png', 'wb') as picture_file:
        picture_blob.download(picture_file)

.. IMPORTANT::
    Always use write binary mode `wb` when downloading a blob to a file like
    object.


Deleting a Blob
===============

Deleting a blob:

.. code-block:: python

    picture_blob = container.get_blob('picture.png')
    picture_blob.delete()


Generate a Download Url
=======================

Generates a signed URL to download a blob:

.. code-block:: python

    from urllib.parse import urlencode

    import requests

    storage_url = 'http://localhost/storage'

    picture_blob = container.get_blob('picture.png')
    signature = picture_blob.generate_download_url(expires=120)

    url_params = {
        'signature': signature,
        'filename': 'picture.png',
    }
    download_url = storage_url + '?' + urlencode(url_params)
    # 'http://localhost/storage?signature=<generated-signature>&filename=picture.png'

    response = requests.get(download_url)
    # <Response [200]>

    with open('/path/picture-download.png', 'wb') as picture_file:
        for chunk in response.iter_content(chunk_size=128):
            picture_file.write(chunk)


Generate an Upload FormPost
===========================

Generate a signature and policy for uploading objects to a container:

.. code-block:: python

    import requests

    container = storage.get_container('container-name')
    form_post = container.generate_upload_url('avatar.png', expires=120)

    url = form_post['url']
    fields = form_post['fields']
    multipart_form_data = {
        'file': open('/path/picture.png', 'rb'),
    }

    response = requests.post(url, data=fields, files=multipart_form_data)
    # <Response [204]>


Iteration of Containers and Blobs
=================================

Storage and containers are both iterable:

.. code-block:: python

    for container in storage:
        container.name
        # 'container-a', 'container-b', ...

        for blob in container:
            blob.name
            # 'blob-1', 'blob-2', ...

Check if a container or container name exists in storage:

.. code-block:: python

    container = storage.get_container('container-name')
    container in storage
    # True
    'container-name' in storage
    # True

Check if a blob or blob name exists in a container:

.. code-block:: python

    container = storage.get_container('container-name')
    picture_blob = container.get_blob('picture.png')
    picture_blob in container
    # True
    'picture.png' in container
    # True


Metadata and Extra Arguments
============================

If supported by the driver, extra arguments can be included with operations
on containers and blobs. For example, `meta_data` can be saved to a blob
object or `Content-Disposition` set to inline or attachment.

.. code-block:: python

    options = {
        'acl': 'public-read',
        'content_disposition': 'attachment; filename="user-1-avatar.png"',
        'content_type': 'image/png',
        'meta_data': {
            'owner-id': '1',
            'owner-email': 'user.one@startup.com',
        }
    }

    picture_path = '/path/picture.png'
    picture_blob = container.upload_blob(picture_path, **options)
    picture_blob.content_disposition
    # 'attachment; filename="user-1-avatar.png"'
    picture_blob.meta_data
    # {'owner-id': '1', 'owner-email': 'user.one@startup.com'}

.. tip::
    It is recommended to save to meta data keys with dashes, `owner-id`,
    instead of with underscores, `owner_id`. Some drivers will allow
    underscores but other drivers will automatically convert them to dashes.

Proceed to the :ref:`Advanced section <advanced>` for individual driver
documentation and advanced usages like generating presigned upload and download
URLs.
