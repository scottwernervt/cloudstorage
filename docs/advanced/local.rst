Local File System Driver
========================

:class:`.LocalDriver` can be used as a full storage backend on backend or for
testing in development.


Connecting
----------

.. code-block:: python

    from cloudstorage.drivers.local import LocalDriver

    storage = LocalDriver(key='/home/webapp/storage',
                          secret='<secret-signed-urls>')
    # <Driver: LOCAL>

Metadata
--------

.. warning:: Metadata and other attributes are saved as extended file
    attributes using the package `xattr <https://github.com/xattr/xattr>`_.
    `Extended attributes <https://en.wikipedia.org/wiki/
    Extended_file_attributes#>`_ are currently only available on Darwin 8.0+
    (Mac OS X 10.4) and Linux 2.6+. Experimental support is included for
    Solaris and FreeBSD.

.. code-block:: python

    container = storage.get_container('container-name')

    meta_data = {
        'owner-id': '1',
        'owner-email': 'user.one@startup.com',
    }

    picture_blob = container.upload_blob('/path/picture.png', meta_data=meta_data)
    picture_blob.meta_data
    # {'owner-id': '1', 'owner-email': 'user.one@startup.com'}

Verify extended attributes on Linux:

.. code-block:: bash

    $ getfattr -d /path/picture.png
    # file: picture.png
    user.content-type="image/png"
    user.metadata.owner-email="user.one@startup.com"
    user.metadata.owner-id="1"


Generate a Download Url
-----------------------

You can optionally share blobs with others by creating a pre-signed URL which
grants time-limited permission to download the blobs. Below will generate a
URL that expires in 2 minutes (120 seconds):

.. code-block:: python

    picture_blob = container.get_blob('picture.png')
    signature = picture_blob.generate_download_url(expires=120)
    # '<generated-signature>'

The signature can then be appended as a url query parameter to your web apps
storage route:

.. code-block:: python

    from urllib.parse import urlencode

    storage_url = 'http://localhost/storage'
    url_params = {
        'signature': signature,
        'filename': 'picture.png',
    }

    download_url = storage_url + '?' + urlencode(url_params)
    # 'http://localhost/storage?signature=<generated-signature>&filename=picture.png'


The user clicks the download URL link and the backend validates the signature:

.. code-block:: python

    from urllib.parse import urlparse, parse_qs

    o = urlparse(download_url)
    query = parse_qs(o.query)
    # {'signature': ['<generated-signature>'], 'filename': ['picture.png']}

    signature = query['signature'][0]
    payload = storage.validate_signature(signature)
    # {
    #   'max_age': 120,
    #  	'expires': 1492583288,
    #  	'blob_name': 'picture.png',
    #  	'container': 'container-name',
    #  	'method': 'GET',
    #  	'content_disposition': None
    # }

    container_request = storage.get_container(payload['container'])
    blob_request = container_request.get_blob(payload['blob_name'])
    blob_request.path
    # 'container-name/picture.png'

If the signature has expired, :meth:`.LocalDriver.validate_signature` will raise
:exc:`.SignatureExpiredError`. Finally, the web app would serve the static file
over Apache or Nginx (or other web server) using request header like
`X-SendFile` or by stream the file contents.


Generate an Upload FormPost
---------------------------

Generates a signed URL to upload a file to a container that expires in 120
seconds (2 minutes):

.. code-block:: python

    container = storage.get_container('container-name')

    options = {
        'expires': 120,
        'content_disposition': 'inline; filename=avatar-user-1.png',
        'meta_data': {
            'owner-id': '1',
            'owner-email': 'user.one@startup.com',
        },
    }
    form_post = container.generate_upload_url('avatar-user-1.png', **options)
    # {
    #   'url': '',
    #   'fields': {
    #     'blob_name': 'avatar-user-1.png',
    #     'container': 'container-name',
    #     'expires': 1492629357,
    #     'signature': '<generated-signature>'
    #   }
    # }

Generate a form with `method="POST"` and `enctype="multipart/form-data"` with
the fields above:

.. code-block:: python

    post_url = 'http://localhost/storage'
    fields = [
        '<input type="hidden" name="{name}" value="{value}" />'.format(
            name=name, value=value)
        for name, value in form_post['fields'].items()
    ]

    upload_form = [
        '<form action="{url}" method="post" '
        'enctype="multipart/form-data">'.format(
            url=post_url),
        *fields,
        '<input name="file" type="file" />',
        '<input type="submit" value="Upload" />',
        '</form>',
    ]

    print('\n'.join(upload_form))


.. code-block:: html

    <form action="http://localhost/storage" method="post" enctype="multipart/form-data">
        <input type="hidden" name="blob_name" value="avatar-user-1.png" />
        <input type="hidden" name="container" value="container-name" />
        <input type="hidden" name="expires" value="1492630156" />
        <input type="hidden" name="signature" value="<generated-signature>" />
        <input name="file" type="file" />
        <input type="submit" value="Upload" />
    </form>

The user uploads a file to your route `http://localhost/storage` with method
`POST` and the signature can be validated with:

.. code-block:: python

    signature = request.form['signature']
    payload = storage.validate_signature(signature)
    # {
    #   'acl': None,
    #   'meta_data': {
    #     'owner-id': '1',
    #     'owner-email': 'user.one@startup.com'
    #   },
    #   'content_disposition': 'inline; filename=avatar-user-1.png',
    #   'content_length': None,
    #   'content_type': None,
    #   'max_age': 3600,
    #   'blob_name': 'avatar-user-1.png',
    #   'container': 'container-name',
    #   'expires': 1492631817
    # }

    container = storage.get_container(payload['container'])

    blob = container.upload_blob(filename=request.files['file'],
                                 blob_name=payload['blob_name'],
                                 acl=payload.get('acl'),
                                 meta_data=payload.get('meta_data'),
                                 content_type=payload.get('content_type'),
                                 content_disposition=payload.get('content_disposition'))
    # <Blob avatar-user-1.png container-name LOCAL>
