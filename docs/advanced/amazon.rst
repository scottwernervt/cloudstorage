Amazon Simple Storage Service (S3)
==================================

Amazon :class:`.S3Driver` is a wrapper around `Boto 3 <http://boto3.readthedocs.io>`_.


Connecting
----------

Change region from default `us-east-1` to `us-west-`:

.. code-block:: python

    from cloudstorage.drivers.amazon import S3Driver

    storage = S3Driver(key='<my-aws-access-key-id>',
                       secret='<my-aws-secret-access-key>',
                       region='us-west-1')
    # <Driver: S3 us-west-1>

Regions supported:

* `ap-northeast-1`
* `ap-northeast-2`
* `ap-south-1`
* `ap-southeast-1`
* `ap-southeast-2`
* `ca-central-1`
* `eu-central-1`
* `eu-west-1`
* `eu-west-2`
* `sa-east-1`
* `us-east-1`
* `us-east-2`
* `us-west-1`
* `us-west-2`


Access Control List (ACL)
-------------------------

By default, all containers and blobs default to `private`. To change the access
control when creating a container or blob, include the `acl` argument option:

.. code-block:: python

    container = storage.create_container('container-public', acl='public-read')
    container.cdn_url
    # https://s3.amazonaws.com/container-public

.. code-block:: python

    container = storage.get_container('container-public')
    picture_blob = container.upload_blob('/path/picture.png', acl='public-read')
    picture_blob.cdn_url
    # https://s3.amazonaws.com/container-public/picture.png

Support ACL values for S3:

* private
* public-read
* public-read-write
* authenticated-read
* bucket-owner-read
* bucket-owner-full-control
* aws-exec-read

.. WARNING::
    Updating ACL on an existing container or blob is not currently supported.
