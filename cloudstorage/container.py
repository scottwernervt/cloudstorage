from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Union  # noqa: F401

from cloudstorage.exceptions import NotFoundError
from cloudstorage.typed import (
    ContentLength,
    ExtraOptions,
    FileLike,
    FormPost,
    MetaData,
)


class Container:
    """Represents a container (bucket or folder) which contains blobs.

    .. code-block:: python

        container = storage.get_container('container-name')
        container.name
        # container-name
        container.created_at
        # 2017-04-11 08:58:12-04:00
        len(container)
        # 20

    .. todo:: Add option to delete blobs before deleting the container.
    .. todo:: Support extra headers like Content-Encoding.

    :param name: Container name (must be unique).
    :type name: str

    :param driver: Reference to this container's driver.
    :type driver: Driver

    :param acl: (optional) Container's canned Access Control List (ACL).
                If `None`, defaults to storage backend default.

                * private
                * public-read
                * public-read-write
                * authenticated-read
                * bucket-owner-read
                * bucket-owner-full-control
                * aws-exec-read (Amazon S3)
                * project-private (Google Cloud Storage)
    :type acl: str or None

    :param meta_data: (optional) Metadata stored with this container.
    :type meta_data: Dict[str, str] or None

    :param created_at: Creation time of this container.
    :type created_at: datetime.datetime or None
    """

    def __init__(self, name: str, driver: 'Driver', acl: str = None,
                 meta_data: MetaData = None,
                 created_at: datetime = None) -> None:
        meta_data = meta_data if meta_data is not None else {}

        self.name = name
        self.driver = driver

        # TODO: FEATURE: Support normalized ACL view.
        self.acl = acl
        self.meta_data = meta_data
        self.created_at = created_at

        self._attr = {}  # type: Dict[Any, Any]
        self._acl = acl  # type: Optional[str]
        self._meta_data = {}  # type: Dict[Any, Any]

        # Track attributes for object PUT
        for key, value in locals().items():
            if key == 'meta_data':
                self._meta_data = value
            elif key == 'acl':
                self._acl = value
            else:
                self._attr[key] = value

    def __contains__(self, blob: Union['Blob', str]) -> bool:
        """Determines whether or not the blob exists in this container.

        .. code-block:: python

            container = storage.get_container('container-name')
            picture_blob = container.get_blob('picture.png')
            picture_blob in container
            # True
            'picture.png' in container
            # True

        :param blob: Blob or Blob name.
        :type blob: str or Blob

        :return: True if the blob exists.
        :rtype: bool
        """
        if hasattr(blob, 'name'):
            blob_name = blob.name
        else:
            blob_name = blob

        try:
            self.driver.get_blob(container=self, blob_name=blob_name)
            return True
        except NotFoundError:
            return False

    def __eq__(self, other: object, implemented=NotImplemented) -> bool:
        """Override the default equals behavior.

        :param other: The other container.
        :type other: Container

        :return: True if the containers are the same.
        :rtype: bool
        """
        if isinstance(other, self.__class__):
            return self.name == other.name and \
                   self.driver.name == other.driver.name  # noqa: E126
        return implemented

    def __hash__(self) -> int:
        """Override the default hash behavior.

        :return: Hash.
        :rtype: hash
        """
        return hash(self.name) ^ hash(self.driver.name)

    def __iter__(self) -> Iterable['Blob']:
        """Get all blobs associated to the container.

        .. code-block:: python

            container = storage.get_container('container-name')
            for blob in container:
                blob.name
                # blob-1.ext, blob-2.ext

        :return: Iterable of all blobs belonging to this container.
        :rtype: Iterable{Blob]
        """
        return self.driver.get_blobs(container=self)

    def __len__(self) -> int:
        """Total number of blobs in this container.

        :return: Blob count in this container.
        :rtype: int
        """
        blobs = self.driver.get_blobs(container=self)
        return len(list(blobs))

    def __ne__(self, other: object) -> bool:
        """Override the default not equals behavior.

        :param other: The other container.
        :type other: Container

        :return: True if the containers are not the same.
        :rtype: bool
        """
        return not self.__eq__(other)

    @property
    def cdn_url(self) -> str:
        """The Content Delivery Network URL for this container.

        `https://container-name.storage.com/`

        :return: The CDN URL for this container.
        :rtype: str
        """
        return self.driver.container_cdn_url(container=self)

    def patch(self) -> None:
        """Saves all changed attributes for this container.

        .. warning:: Not supported by all drivers yet.

        :return: NoneType
        :rtype: None

        :raises NotFoundError: If the container doesn't exist.
        """
        self.driver.patch_container(container=self)

    def delete(self) -> None:
        """Delete this container.

        .. important:: All blob objects in the container must be deleted before
          the container itself can be deleted.

        .. code-block:: python

            container = storage.get_container('container-name')
            container.delete()
            container in storage
            # False

        :return: NoneType
        :rtype: None

        :raises IsNotEmptyError: If the container is not empty.
        :raises NotFoundError: If the container doesn't exist.
        """
        self.driver.delete_container(container=self)

    def upload_blob(self, filename: FileLike, blob_name: str = None,
                    acl: str = None, meta_data: MetaData = None,
                    content_type: str = None, content_disposition: str = None,
                    chunk_size: int = 1024,
                    extra: ExtraOptions = None) -> 'Blob':
        """Upload a filename or file like object to a container.

        If `content_type` is `None`, Cloud Storage will attempt to guess the
        standard MIME type using the packages: `python-magic` or `mimetypes`. If
        that fails, Cloud Storage will leave it up to the storage backend to
        guess it.

        .. warning:: The effect of uploading to an existing blob depends on the
          “versioning” and “lifecycle” policies defined on the blob’s
          container. In the absence of those policies, upload will overwrite
          any existing contents.

        Basic example:

        .. code-block:: python

            container = storage.get_container('container-name')
            picture_blob = container.upload_blob('/path/picture.png')
            # <Blob picture.png container-name S3>

        Set Content-Type example:

        .. code-block:: python

            container = storage.get_container('container-name')
            with open('/path/resume.doc', 'rb') as resume_file:
                resume_blob = container.upload_blob(resume_file,
                    content_type='application/msword')
                resume_blob.content_type
                # 'application/msword'

        Set Metadata and ACL:

        .. code-block:: python

            picture_file = open('/path/picture.png', 'rb)
                'acl': 'public-read',
            meta_data = {
                'owner-email': 'user.one@startup.com',
                'owner-id': '1'
            }

            container = storage.get_container('container-name')
            picture_blob = container.upload_blob(picture_file,
                acl='public-read', meta_data=meta_data)
            picture_blob.meta_data
            # {owner-id': '1', 'owner-email': 'user.one@startup.com'}

        References:

        * `Boto 3: PUT Object
          <http://boto3.readthedocs.io/en/latest/reference/services/s3.html#
          S3.Client.put_object>`_
        * `Google Cloud Storage: upload_from_file / upload_from_filename
          <https://googlecloudplatform.github.io/google-cloud-python/stable/
          storage-blobs.html>`_
        * `Rackspace Cloud Files: Create or update object
          <https://developer.rackspace.com/docs/cloud-files/v1/
          storage-api-reference/object-services-operations/
          #create-or-update-object>`_

        :param chunk_size:
        :type chunk_size:
        :param filename: A file handle open for reading or the path to the file.
        :type filename: file or str

        :param acl: (optional) Blob canned Access Control List (ACL).
                    If `None`, defaults to storage backend default.

                    * private
                    * public-read
                    * public-read-write
                    * authenticated-read
                    * bucket-owner-read
                    * bucket-owner-full-control
                    * aws-exec-read (Amazon S3)
                    * project-private (Google Cloud Storage)
        :type acl: str or None

        :param blob_name: (optional) Override the blob's name. If not set, will
          default to the filename from path or filename of iterator object.
        :type blob_name: str or None

        :param meta_data: (optional) A map of metadata to store with the blob.
        :type meta_data: Dict[str, str] or None

        :param content_type: (optional) A standard MIME type describing the
          format of the object data.
        :type content_type: str or None

        :param content_disposition: (optional) Specifies presentational
          information for the blob.
        :type content_disposition: str or None

        :param chunk_size: (optional) Optional chunk size for streaming a
          transfer.
        :type chunk_size: int

        :param extra: (optional) Extra parameters for the request.
        :type extra: Dict[str, str] or None

        :return: The uploaded blob.
        :rtype: Blob
        """
        return self.driver.upload_blob(container=self, filename=filename,
                                       blob_name=blob_name, acl=acl,
                                       meta_data=meta_data,
                                       content_type=content_type,
                                       content_disposition=content_disposition,
                                       chunk_size=chunk_size,
                                       extra=extra)

    def get_blob(self, blob_name: str) -> 'Blob':
        """Get a blob object by name.

        .. code-block:: python

            container = storage.get_container('container-name')
            picture_blob = container.get_blob('picture.png')
            # <Blob picture.png container-name S3>

        :param blob_name: The name of the blob to retrieve.
        :type blob_name: str

        :return: The blob object if it exists.
        :rtype: Blob

        :raise NotFoundError: If the blob object doesn't exist.
        """
        return self.driver.get_blob(container=self, blob_name=blob_name)

    def generate_upload_url(self, blob_name: str, expires: int = 3600,
                            acl: str = None, meta_data: MetaData = None,
                            content_disposition: str = None,
                            content_length: ContentLength = None,
                            content_type: str = None,
                            extra: ExtraOptions = None) -> FormPost:
        """Generate a signature and policy for uploading objects to this
        container.

        This method gives your website a way to upload objects to a container
        through a web form without giving the user direct write access.

        Basic example:

        .. code-block:: python

            import requests

            picture_file = open('/path/picture.png', 'rb')

            container = storage.get_container('container-name')
            form_post = container.generate_upload_url('avatar-user-1.png')

            url = form_post['url']
            fields = form_post['fields']
            multipart_form_data = {
                'file': ('avatar.png', picture_file, 'image/png'),
            }

            resp = requests.post(url, data=fields, files=multipart_form_data)
            # <Response [201]> or <Response [204]>

            avatar_blob = container.get_blob('avatar-user-1.png')
            # <Blob avatar-user-1.png container-name S3>

        Form example:

        .. code-block:: python

            container = storage.get_container('container-name')
            form_post = container.generate_upload_url('avatar-user-1.png')

            # Generate an upload form using the form fields and url
            fields = [
                '<input type="hidden" name="{name}" value="{value}" />'.format(
                    name=name, value=value)
                for name, value in form_post['fields'].items()
            ]

            upload_form = [
                '<form action="{url}" method="post" '
                'enctype="multipart/form-data">'.format(
                    url=form_post['url']),
                *fields,
                '<input name="file" type="file" />',
                '<input type="submit" value="Upload" />',
                '</form>',
            ]

            print('\\n'.join(upload_form))

        .. code-block:: html

            <!--Google Cloud Storage Generated Form-->
            <form action="https://container-name.storage.googleapis.com"
                  method="post" enctype="multipart/form-data">
            <input type="hidden" name="key" value="avatar-user-1.png" />
            <input type="hidden" name="bucket" value="container-name" />
            <input type="hidden" name="GoogleAccessId" value="<my-access-id>" />
            <input type="hidden" name="policy" value="<generated-policy>" />
            <input type="hidden" name="signature" value="<generated-sig>" />
            <input name="file" type="file" />
            <input type="submit" value="Upload" />
            </form>

        Content-Disposition and Metadata example:

        .. code-block:: python

            import requests

            params = {
                'blob_name': 'avatar-user-1.png',
                'meta_data': {
                    'owner-id': '1',
                    'owner-email': 'user.one@startup.com'
                },
                'content_type': 'image/png',
                'content_disposition': 'attachment; filename=attachment.png'
            }
            form_post = container.generate_upload_url(**params)

            url = form_post['url']
            fields = form_post['fields']
            multipart_form_data = {
                'file': open('/path/picture.png', 'rb'),
            }

            resp = requests.post(url, data=fields, files=multipart_form_data)
            # <Response [201]> or <Response [204]>

            avatar_blob = container.get_blob('avatar-user-1.png')
            avatar_blob.content_disposition
            # 'attachment; filename=attachment.png'

        References:

        * `Boto 3: S3.Client.generate_presigned_post
          <http://boto3.readthedocs.io/en/latest/reference/services/s3.html#
          S3.Client.generate_presigned_post>`_
        * `Google Cloud Storage: POST Object
          <https://cloud.google.com/storage/docs/xml-api/post-object>`_
        * `Rackspace Cloud Files: FormPost
          <https://developer.rackspace.com/docs/cloud-files/v1/use-cases/
          public-access-to-your-cloud-files-account/#formpost>`_

        :param blob_name: The blob's name, prefix, or `''` if a user is
          providing a file name. Note, Rackspace Cloud Files only supports
          prefixes.
        :type blob_name: str or None

        :param expires: (optional) Expiration in seconds.
        :type expires: int

        :param acl: (optional) Container canned Access Control List (ACL).
                    If `None`, defaults to storage backend default.

                    * private
                    * public-read
                    * public-read-write
                    * authenticated-read
                    * bucket-owner-read
                    * bucket-owner-full-control
                    * aws-exec-read (Amazon S3)
                    * project-private (Google Cloud Storage)
        :type acl: str or None

        :param meta_data: (optional) A map of metadata to store with the blob.
        :type meta_data: Dict[str, str] or None

        :param content_disposition: (optional) Specifies presentational
          information for the blob.
        :type content_disposition: str or None

        :param content_type: (optional) A standard MIME type describing the
          format of the object data.
        :type content_type: str or None

        :param content_length: Specifies that uploaded files can only be
          between a certain size range in bytes: `(<min>, <max>)`.
        :type content_length: tuple[int, int] or None

        :param extra: (optional) Extra parameters for the request.

                      * **success_action_redirect** *(str) --* A URL that users
                        are redirected to when an upload is successful. If you
                        do not provide a URL, Cloud Storage responds with the
                        status code that you specified in
                        `success_action_status`.
                      * **success_action_status** *(str) --* The status code
                        that you  want Cloud Storage to respond with when an
                        upload is successful. The default is `204`.
        :type extra: Dict[str, str] or None

        :return: Dictionary with URL and form fields (includes signature or
          policy).
        :rtype: Dict[Any, Any]
        """
        return self.driver.generate_container_upload_url(
            container=self,
            blob_name=blob_name,
            expires=expires, acl=acl,
            meta_data=meta_data,
            content_disposition=content_disposition,
            content_length=content_length,
            content_type=content_type,
            extra=extra)

    def enable_cdn(self) -> bool:
        """Enable Content Delivery Network (CDN) for this container.

        :return: True if successful or false if not supported.
        :rtype: bool
        """
        return self.driver.enable_container_cdn(container=self)

    def disable_cdn(self) -> bool:
        """Disable Content Delivery Network (CDN) for this container.

        :return: True if successful or false if not supported.
        :rtype: bool
        """
        return self.driver.disable_container_cdn(container=self)

    def __repr__(self):
        return '<Container %s %s>' % (self.name, self.driver.name)
