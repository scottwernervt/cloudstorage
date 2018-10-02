from datetime import datetime
from typing import Dict

from cloudstorage.typed import Acl, ExtraOptions, FileLike, MetaData


class Blob:
    """Represents an object blob.

    .. code-block:: python

        picture_blob = container.get_blob('picture.png')
        picture_blob.size
        # 50301
        picture_blob.checksum
        # '2f907a59924ad96b7478074ed96b05f0'
        picture_blob.content_type
        # 'image/png'
        picture_blob.content_disposition
        # 'attachment; filename=picture-attachment.png'

    :param name: Blob name (must be unique in container).
    :type name: str

    :param checksum: Checksum of this blob.
    :type checksum: str

    :param etag: Blob etag which can also be the checksum. The etag for
      `LocalDriver` is a SHA1 hexdigest of the blob's full path.
    :type etag: str

    :param size: Blob size in bytes.
    :type size: int

    :param container: Reference to the blob's container.
    :type container: Container

    :param driver: Reference to the blob's container's driver.
    :type driver: Driver

    :param meta_data: (optional) Metadata stored with the blob.
    :type meta_data: Dict[str, str] or None

    :param acl: (optional) Access control list (ACL) for this blob.
    :type acl: dict or None

    :param content_disposition: (optional) Specifies presentational
                                information for this blob.
    :type content_disposition: str or None

    :param content_type: (optional) A standard MIME type describing the format
                         of the object data.
    :type content_type: str or None

    :param created_at: (optional) Creation time of this blob.
    :type created_at: datetime.datetime or None

    :param modified_at: (optional) Last modified time of this blob.
    :type modified_at: datetime.datetime or None

    :param expires_at: (optional) Deletion or expiration time for this blob.
    :type expires_at: datetime.datetime or None
    """

    def __init__(self, name: str, checksum: str, etag: str, size: int,
                 container: 'Container', driver: 'Driver', acl: Acl = None,
                 meta_data: MetaData = None, content_disposition: str = None,
                 content_type: str = None, created_at: datetime = None,
                 modified_at: datetime = None,
                 expires_at: datetime = None) -> None:
        acl = acl if acl is not None else {}
        meta_data = meta_data if meta_data is not None else {}

        self.name = name
        self.size = size
        self.checksum = checksum
        self.etag = etag
        self.container = container
        self.driver = driver

        self.acl = acl
        self.meta_data = meta_data
        self.content_disposition = content_disposition
        self.content_type = content_type
        self.created_at = created_at
        self.modified_at = modified_at
        self.expires_at = expires_at

        self._attr = {}  # type: Dict
        self._acl = {}  # type: Dict
        self._meta_data = {}  # type: Dict

        # Track attributes for object PUT
        for key, value in locals().items():
            if key == 'meta_data':
                self._meta_data = value
            elif key == 'acl':
                self._acl = value
            else:
                self._attr[key] = value

    def __eq__(self, other: object) -> bool:
        """Override the default equals behavior.

        :param other: The other Blob.
        :type other: Blob

        :return: True if the Blobs are the same.
        :rtype: bool
        """
        if isinstance(other, self.__class__):
            return self.checksum == other.checksum
        return NotImplemented

    def __hash__(self) -> int:
        """Override the default hash behavior.

        :return: Hash.
        :rtype: hash
        """
        # TODO: QUESTION: Include extra attributes like self.name?
        return hash(self.checksum)

    def __len__(self) -> int:
        """The blob size in bytes.

        :return: bytes
        :rtype: int
        """
        return self.size

    def __ne__(self, other: object) -> bool:
        """Override the default not equals behavior.

        :param other: The other blob.
        :type other: Blob

        :return: True if the containers are not the same.
        :rtype: bool
        """
        return not self.__eq__(other)

    @property
    def cdn_url(self) -> str:
        """The Content Delivery Network URL for this blob.

        `https://container-name.storage.com/picture.png`

        :return: The CDN URL for this blob.
        :rtype: str
        """
        return self.driver.blob_cdn_url(blob=self)

    @property
    def path(self) -> str:
        """Relative URL path for this blob.

        `container-name/picture.png`

        :return: The relative URL path to this blob.
        :rtype: str
        """
        return '%s/%s' % (self.container.name, self.name)

    def delete(self) -> None:
        """Delete this blob from the container.

        .. code-block:: python

            picture_blob = container.get_blob('picture.png')
            picture_blob.delete()
            picture_blob in container
            # False

        :return: NoneType
        :rtype: None

        :raises NotFoundError: If the blob object doesn't exist.
        """
        self.driver.delete_blob(blob=self)

    def download(self, destination: FileLike) -> None:
        """Download the contents of this blob into a file-like object or into
        a named file.

        Filename:

        .. code-block:: python

            picture_blob = container.get_blob('picture.png')
            picture_blob.download('/path/picture-copy.png')

        File object:

        .. IMPORTANT:: Always use write binary mode `wb` when downloading a
            blob to a file object.

        .. code-block:: python

            picture_blob = container.get_blob('picture.png')
            with open('/path/picture-copy.png', 'wb') as picture_file:
                picture_blob.download(picture_file)

        :param destination: A file handle to which to write the blob’s data or
          a filename to be passed to `open`.
        :type destination: file or str

        :return: NoneType
        :rtype: None

        :raises NotFoundError: If the blob object doesn't exist.
        """
        self.driver.download_blob(self, destination)

    def generate_download_url(self, expires: int = 3600, method: str = 'GET',
                              content_disposition: str = None,
                              extra: ExtraOptions = None) -> str:
        """Generates a signed URL for this blob.

        If you have a blob that you want to allow access to for a set amount of
        time, you can use this method to generate a URL that is only valid
        within a certain time period. This is particularly useful if you don’t
        want publicly accessible blobs, but don’t want to require users to
        explicitly log in. [#f1]_

        .. [#f1] `Blobs / Objects — google-cloud 0.24.0 documentation
         <https://googlecloudplatform.github.io/google-cloud-python/
         stable/storage-blobs.html>`_

        Basic example:

        .. code-block:: python

            import requests

            picture_blob = container.get_blob('picture.png')
            download_url = picture_blob.download_url(expires=3600)

            response = requests.get(download_url)
            # <Response [200]>

            with open('/path/picture-download.png', 'wb') as picture_file:
                for chunk in response.iter_content(chunk_size=128):
                    picture_file.write(chunk)

        Response Content-Disposition example:

        .. code-block:: python

            picture_blob = container.get_blob('picture.png')

            params = {
                'expires': 3600,
                'content_disposition': 'attachment; filename=attachment.png'
            }
            download_url = picture_blob.download_url(**params)

            response = requests.get(download_url)
            # <Response [200]>
            response.headers['content-disposition']
            # attachment; filename=attachment.png

        References:

        * `Boto 3: S3.Client.generate_presigned_url
          <http://boto3.readthedocs.io/en/latest/reference/services/s3.html#
          S3.Client.generate_presigned_url>`_
        * `Google Cloud Storage: generate_signed_url
          <https://googlecloudplatform.github.io/google-cloud-python/stable/
          storage-blobs.html>`_
        * `Rackspace: TempURL
          <https://developer.rackspace.com/docs/cloud-files/v1/use-cases/
          public-access-to-your-cloud-files-account/#tempurl>`_

        :param expires: (optional) Expiration in seconds.
        :type expires: int

        :param method: (optional) HTTP request method. Defaults to `GET`.
        :type method: str

        :param content_disposition: (optional) Sets the Content-Disposition
          header of the response.
        :type content_disposition: str or None

        :param extra: (optional) Extra parameters for the request.

                      * All

                        * **content_type** *(str) --* Sets the Content-Type
                          header of the response.

                      * Google Cloud Storage

                        * **version** *(str) --* A value that indicates which
                          generation of the resource to fetch.

                      * Amazon S3

                        * **version_id** *(str) --* Version of the object.
        :type extra: Dict[str, str] or None

        :return: Pre-signed URL for downloading a blob. :class:`.LocalDriver`
          returns urlsafe signature.
        :rtype: str
        """
        return self.driver.generate_blob_download_url(
            blob=self,
            expires=expires,
            method=method,
            content_disposition=content_disposition,
            extra=extra)

    def patch(self) -> None:
        """Saves all changed attributes for this blob.

        .. warning:: Not supported by all drivers yet.

        :return: NoneType
        :rtype: None

        :raises NotFoundError: If the blob object doesn't exist.
        """
        self.driver.patch_blob(blob=self)

    def __repr__(self):
        return '<Blob %s %s %s>' % (
            self.name, self.container.name, self.driver.name)
