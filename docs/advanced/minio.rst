Minio Cloud Storage
===================

:class:`.MinioDriver` is a wrapper around `minio-py <https://docs.minio.io/docs/python-client-api-reference>`_.


Connecting
----------

Change region from default `us-east-1` to `us-west-1`:

.. code-block:: python

    from cloudstorage.drivers.minio import MinioDriver

    storage = MinioDriver(endpoint='<minio-server>:<minio-port>
                          key='<my-access-key-id>',
                          secret='<my-secret-key>',
                          region='us-west-1')
    # <Driver: MINIO us-west-1>

Regions supported:

* `us-east-1`
* `us-west-1`
* `us-west-2`
* `eu-west-1`
* `eu-central-1`
* `ap-southeast-1`
* `ap-southeast-2`
* `ap-northeast-1`
* `ap-northeast-2`
* `sa-east-1`
* `cn-north-1`
