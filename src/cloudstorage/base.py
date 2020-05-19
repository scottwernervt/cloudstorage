import abc
import logging
from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union  # noqa: F401

from cloudstorage import messages
from cloudstorage.exceptions import NotFoundError
from cloudstorage.structures import CaseInsensitiveDict
from cloudstorage.typed import (
    Acl,
    ContentLength,
    ExtraOptions,
    FileLike,
    FormPost,
    MetaData,
)

__all__ = ["Blob", "Container", "Driver"]

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        name: str,
        checksum: str,
        etag: str,
        size: int,
        container: "Container",
        driver: "Driver",
        acl: Acl = None,
        meta_data: MetaData = None,
        content_disposition: str = None,
        content_type: str = None,
        cache_control: str = None,
        created_at: datetime = None,
        modified_at: datetime = None,
        expires_at: datetime = None,
    ) -> None:
        if meta_data is None:
            meta_data = CaseInsensitiveDict()
        else:
            meta_data = CaseInsensitiveDict(meta_data)

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
        self.cache_control = cache_control
        self.created_at = created_at
        self.modified_at = modified_at
        self.expires_at = expires_at

        self._attr = CaseInsensitiveDict()  # type: CaseInsensitiveDict
        self._meta_data = CaseInsensitiveDict()  # type: CaseInsensitiveDict
        self._acl = None

        # Track attributes for blob update (PUT request)
        track_params = CaseInsensitiveDict(
            {
                "name": name,
                "meta_data": meta_data,
                "acl": acl,
                "content_disposition": content_disposition,
                "content_type": content_type,
                "cache_control": cache_control,
                "expires_at": expires_at,
            }
        )
        for key, value in track_params.items():
            if key == "meta_data":
                self._meta_data = value
            elif key == "acl":
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
        return "%s/%s" % (self.container.name, self.name)

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
        if isinstance(destination, Path):
            destination = str(destination)
        self.driver.download_blob(self, destination)

    def generate_download_url(
        self,
        expires: int = 3600,
        method: str = "GET",
        content_disposition: str = None,
        extra: ExtraOptions = None,
    ) -> str:
        """Generates a signed URL for this blob.

        If you have a blob that you want to allow access to for a set amount of
        time, you can use this method to generate a URL that is only valid
        within a certain time period. This is particularly useful if you don’t
        want publicly accessible blobs, but don’t want to require users to
        explicitly log in. [#f1]_

        .. [#f1] `Blobs / Objects — google-cloud 0.24.0 documentation
         <https://googleapis.github.io/google-cloud-python/latest/storage/blobs.html>`_

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
          <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/
          services/s3.html#S3.Client.generate_presigned_url>`_
        * `Google Cloud Storage: generate_signed_url
          <https://googleapis.github.io/google-cloud-python/latest/storage/blobs.html>`_
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
            extra=extra,
        )

    def patch(self) -> None:
        """Saves all changed attributes for this blob.

        .. warning:: Not supported by all drivers yet.

        :return: NoneType
        :rtype: None

        :raises NotFoundError: If the blob object doesn't exist.
        """
        self.driver.patch_blob(blob=self)

    def __repr__(self):
        return "<Blob %s %s %s>" % (self.name, self.container.name, self.driver.name)


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

    def __init__(
        self,
        name: str,
        driver: "Driver",
        acl: str = None,
        meta_data: MetaData = None,
        created_at: datetime = None,
    ) -> None:
        if meta_data is None:
            meta_data = CaseInsensitiveDict()
        else:
            meta_data = CaseInsensitiveDict(meta_data)

        self.name = name
        self.driver = driver

        # TODO: FEATURE: Support normalized ACL view.
        self.acl = acl
        self.meta_data = meta_data
        self.created_at = created_at

        self._attr = CaseInsensitiveDict()
        self._acl = acl  # type: Optional[str]
        self._meta_data = CaseInsensitiveDict()

        # Track attributes for container update (PUT request)
        track_params = CaseInsensitiveDict(
            {"name": name, "meta_data": meta_data, "acl": acl}
        )
        for key, value in track_params.items():
            if key == "meta_data":
                self._meta_data = value
            elif key == "acl":
                self._acl = value
            else:
                self._attr[key] = value

    def __contains__(self, blob: Union[Blob, str]) -> bool:
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
        if isinstance(blob, Blob):
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
            return (
                self.name == other.name and self.driver.name == other.driver.name
            )  # noqa: E126
        return implemented

    def __hash__(self) -> int:
        """Override the default hash behavior.

        :return: Hash.
        :rtype: hash
        """
        return hash(self.name) ^ hash(self.driver.name)

    def __iter__(self) -> Iterable[Blob]:
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

    def upload_blob(
        self,
        filename: FileLike,
        blob_name: str = None,
        acl: str = None,
        meta_data: MetaData = None,
        content_type: str = None,
        content_disposition: str = None,
        cache_control: str = None,
        chunk_size: int = 1024,
        extra: ExtraOptions = None,
    ) -> Blob:
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
          <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/
          services/s3.html#S3.Client.put_object>`_
        * `Google Cloud Storage: upload_from_file / upload_from_filename
          <https://googleapis.github.io/google-cloud-python/latest/storage/blobs.html>`_
        * `Rackspace Cloud Files: Create or update object
          <https://developer.rackspace.com/docs/cloud-files/v1/
          storage-api-reference/object-services-operations/
          #create-or-update-object>`_

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

        :param cache_control: (optional) Specify directives for caching
         mechanisms for the blob.
        :type cache_control: str or None

        :param chunk_size: (optional) Optional chunk size for streaming a
          transfer.
        :type chunk_size: int

        :param extra: (optional) Extra parameters for the request.
        :type extra: Dict[str, str] or None

        :return: The uploaded blob.
        :rtype: Blob
        """
        if isinstance(filename, Path):
            filename = str(filename)
        return self.driver.upload_blob(
            container=self,
            filename=filename,
            blob_name=blob_name,
            acl=acl,
            meta_data=meta_data,
            content_type=content_type,
            content_disposition=content_disposition,
            cache_control=cache_control,
            chunk_size=chunk_size,
            extra=extra,
        )

    def get_blob(self, blob_name: str) -> Blob:
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

    def generate_upload_url(
        self,
        blob_name: str,
        expires: int = 3600,
        acl: str = None,
        meta_data: MetaData = None,
        content_disposition: str = None,
        content_length: ContentLength = None,
        content_type: str = None,
        cache_control: str = None,
        extra: ExtraOptions = None,
    ) -> FormPost:
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
          <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/
          services/s3.html#S3.Client.generate_presigned_post>`_
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

        :param content_length: Specifies that uploaded files can only be
          between a certain size range in bytes: `(<min>, <max>)`.
        :type content_length: tuple[int, int] or None

        :param content_type: (optional) A standard MIME type describing the
          format of the object data.
        :type content_type: str or None

        :param cache_control: (optional) Specify directives for caching
         mechanisms for the blob.
        :type cache_control: str or None

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
            expires=expires,
            acl=acl,
            meta_data=meta_data,
            content_disposition=content_disposition,
            content_length=content_length,
            content_type=content_type,
            cache_control=cache_control,
            extra=extra,
        )

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
        return "<Container %s %s>" % (self.name, self.driver.name)


class Driver(metaclass=abc.ABCMeta):
    """Abstract Base Driver Class (:class:`abc.ABCMeta`) to derive from.

    .. todo::

        * Create driver abstract method to get total number of containers.
        * Create driver abstract method to get total number of blobs
          in a container.
        * Support for ACL permission grants.
        * Support for CORS.
        * Support for container / blob expiration (delete_at).

    :param key: (optional) API key, username, credentials file, or local
     directory.
    :type key: str or None

    :param secret: (optional) API secret key.
    :type secret: str

    :param region: (optional) Region to connect to.
    :type region: str

    :param kwargs: (optional) Extra options for the driver.
    :type kwargs: dict
    """

    #: Unique `str` driver name.
    name = None  # type: str

    #: :mod:`hashlib` function `str` name used by driver.
    hash_type = "md5"  # type: str

    #: Unique `str` driver URL.
    url = None  # type: Optional[str]

    def __init__(
        self, key: str = None, secret: str = None, region: str = None, **kwargs: Dict
    ) -> None:
        self.key = key
        self.secret = secret
        self.region = region

    def __contains__(self, container) -> bool:
        """Determines whether or not the container exists.

        .. code: python

            container = storage.get_container('container-name')

            container in storage
            # True

            'container-name' in storage
            # True

        :param container: Container or container name.
        :type container: cloudstorage.Container or str

        :return: True if the container exists.
        :rtype: bool
        """
        if hasattr(container, "name"):
            container_name = container.name
        else:
            container_name = container

        try:
            self.get_container(container_name=container_name)
            return True
        except NotFoundError:
            return False

    @abstractmethod
    def __iter__(self) -> Iterable["Container"]:
        """Get all containers associated to the driver.

        .. code-block:: python

            for container in storage:
                print(container.name)

        :yield: Iterator of all containers belonging to this driver.
        :yield type: Iterable[:class:`.Container`]
        """
        pass

    @abstractmethod
    def __len__(self) -> int:
        """The total number of containers in the driver.

        :return: Number of containers belonging to this driver.
        :rtype: int
        """
        pass

    @staticmethod
    @abstractmethod
    def _normalize_parameters(
        params: Dict[str, str], normalizers: Dict[str, str]
    ) -> Dict[str, str]:
        """Transform parameter key names to match syntax required by the driver.

        :param params: Dictionary of parameters for method.
        :type params: dict

        :param normalizers: Dictionary mapping of key names.
        :type normalizers: dict

        :return: Dictionary of transformed key names.

            ::

                {
                    '<key-name>': `<Mapped-Name>`
                    'meta_data': 'Metadata',
                    'content_disposition': 'ContentDisposition'
                }

        :rtype: Dict[str, str]
        """
        pass

    @abstractmethod
    def validate_credentials(self) -> None:
        """Validate driver credentials (key and secret).

        :return: None
        :rtype: None
        :raises CredentialsError: If driver authentication fails.
        """
        pass

    @property
    @abstractmethod
    def regions(self) -> List[str]:
        """List of supported regions for this driver.

        :return: List of region strings.
        :rtype: list[str]
        """
        pass

    @abstractmethod
    def create_container(
        self, container_name: str, acl: str = None, meta_data: MetaData = None
    ) -> "Container":
        """Create a new container.

        For example:

        .. code-block:: python

            container = storage.create_container('container-name')
            # <Container container-name driver-name>

        :param container_name: The container name to create.
        :type container_name: str

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
                    * container-public-access (Microsoft Azure Storage)
                    * blob-public-access (Microsoft Azure Storage)
        :type acl: str or None

        :param meta_data: (optional) A map of metadata to store with the
          container.
        :type meta_data: Dict[str, str] or None

        :return: The newly created or existing container.
        :rtype: :class:`.Container`

        :raises CloudStorageError: If the container name contains invalid
          characters.
        """
        pass

    @abstractmethod
    def get_container(self, container_name: str) -> "Container":
        """Get a container by name.

        For example:

        .. code-block:: python

            container = storage.get_container('container-name')
            # <Container container-name driver-name>

        :param container_name: The name of the container to retrieve.
        :type container_name: str

        :return: The container if it exists.
        :rtype: :class:`.Container`

        :raise NotFoundError: If the container doesn't exist.
        """
        pass

    @abstractmethod
    def patch_container(self, container: "Container") -> None:
        """Saves all changed attributes for the container.

        .. important:: This class method is called by :meth:`.Container.save`.

        :param container: A container instance.
        :type container: :class:`.Container`

        :return: NoneType
        :rtype: None

        :raises NotFoundError: If the container doesn't exist.
        """
        pass

    @abstractmethod
    def delete_container(self, container: "Container") -> None:
        """Delete this container.

        .. important:: This class method is called by :meth:`.Container.delete`.

        :param container: A container instance.
        :type container: :class:`.Container`

        :return: NoneType
        :rtype: None

        :raises IsNotEmptyError: If the container is not empty.
        :raises NotFoundError: If the container doesn't exist.
        """
        pass

    @abstractmethod
    def container_cdn_url(self, container: "Container") -> str:
        """The Content Delivery Network URL for this container.

        .. important:: This class method is called by
          :attr:`.Container.cdn_url`.

        :return: The CDN URL for this container.
        :rtype: str
        """
        pass

    @abstractmethod
    def enable_container_cdn(self, container: "Container") -> bool:
        """(Optional) Enable Content Delivery Network (CDN) for the container.

        .. important:: This class method is called by
          :meth:`.Container.enable_cdn`.

        :param container: A container instance.
        :type container: :class:`.Container`

        :return: True if successful or false if not supported.
        :rtype: bool
        """
        logger.warning(messages.FEATURE_NOT_SUPPORTED, "enable_container_cdn")
        return False

    @abstractmethod
    def disable_container_cdn(self, container: "Container") -> bool:
        """(Optional) Disable Content Delivery Network (CDN) on the container.

        .. important:: This class method is called by
          :meth:`.Container.disable_cdn`.

        :param container: A container instance.
        :type container: :class:`.Container`

        :return: True if successful or false if not supported.
        :rtype: bool
        """
        logger.warning(messages.FEATURE_NOT_SUPPORTED, "disable_container_cdn")
        return False

    @abstractmethod
    def upload_blob(
        self,
        container: "Container",
        filename: FileLike,
        blob_name: str = None,
        acl: str = None,
        meta_data: MetaData = None,
        content_type: str = None,
        content_disposition: str = None,
        cache_control: str = None,
        chunk_size=1024,
        extra: ExtraOptions = None,
    ) -> "Blob":
        """Upload a filename or file like object to a container.

        .. important:: This class method is called by
          :meth:`.Container.upload_blob`.

        :param container: The container to upload the blob to.
        :type container: :class:`.Container`

        :param filename: A file handle open for reading or the path to the file.
        :type filename: file or str

        :param acl: (optional) Blob canned Access Control List (ACL).
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

        :param cache_control: (optional) Specify directives for caching
         mechanisms for the blob.
        :type cache_control: str or None

        :param chunk_size: (optional) Optional chunk size for streaming a
          transfer.
        :type chunk_size: int

        :param extra: (optional) Extra parameters for the request.
        :type extra: Dict[str, str] or None

        :return: The uploaded blob.
        :rtype: Blob
        """
        pass

    @abstractmethod
    def get_blob(self, container: "Container", blob_name: str) -> "Blob":
        """Get a blob object by name.

        .. important:: This class method is called by :meth:`.Blob.get_blob`.

        :param container: The container that holds the blob.
        :type container: :class:`.Container`

        :param blob_name: The name of the blob to retrieve.
        :type blob_name: str

        :return: The blob object if it exists.
        :rtype: Blob

        :raise NotFoundError: If the blob object doesn't exist.
        """
        pass

    @abstractmethod
    def get_blobs(self, container: "Container") -> Iterable["Blob"]:
        """Get all blobs associated to the container.

        .. important:: This class method is called by :meth:`.Blob.__iter__`.

        :param container: A container instance.
        :type container: :class:`.Container`

        :return: Iterable of all blobs belonging to this container.
        :rtype: Iterable{Blob]
        """
        pass

    @abstractmethod
    def download_blob(self, blob: "Blob", destination: FileLike) -> None:
        """Download the contents of this blob into a file-like object or into
        a named file.

        .. important:: This class method is called by :meth:`.Blob.download`.

        :param blob: The blob object to download.
        :type blob: Blob

        :param destination: A file handle to which to write the blob’s data or
          a filename to be passed to `open`.
        :type destination: file or str

        :return: NoneType
        :rtype: None

        :raises NotFoundError: If the blob object doesn't exist.
        """
        pass

    @abstractmethod
    def patch_blob(self, blob: "Blob") -> None:
        """Saves all changed attributes for this blob.

        .. important:: This class method is called by :meth:`.Blob.update`.

        :return: NoneType
        :rtype: None

        :raises NotFoundError: If the blob object doesn't exist.
        """
        pass

    @abstractmethod
    def delete_blob(self, blob: "Blob") -> None:
        """Deletes a blob from storage.

        .. important:: This class method is called by :meth:`.Blob.delete`.

        :param blob: The blob to delete.
        :type blob: Blob

        :return: NoneType
        :rtype: None

        :raise NotFoundError: If the blob object doesn't exist.
        """
        pass

    @abstractmethod
    def blob_cdn_url(self, blob: "Blob") -> str:
        """The Content Delivery Network URL for the blob.

        .. important:: This class method is called by :attr:`.Blob.cdn_url`.

        :param blob: The public blob object.
        :type blob: Blob

        :return: The CDN URL for the blob.
        :rtype: str
        """
        pass

    @abstractmethod
    def generate_container_upload_url(
        self,
        container: "Container",
        blob_name: str,
        expires: int = 3600,
        acl: str = None,
        meta_data: MetaData = None,
        content_disposition: str = None,
        content_length: ContentLength = None,
        content_type: str = None,
        cache_control: str = None,
        extra: ExtraOptions = None,
    ) -> FormPost:
        """Generate a signature and policy for uploading objects to the
        container.

        .. important:: This class method is called by
          :meth:`.Container.generate_upload_url`.

        :param container: A container to upload the blob object to.
        :type container: :class:`.Container`

        :param blob_name: The blob's name, prefix, or `''` if a user is
          providing a file name. Note, Rackspace Cloud Files only supports
          prefixes.
        :type blob_name: str or None

        :param expires: (optional) Expiration in seconds.
        :type expires: int

        :param acl: (optional) Container canned Access Control List (ACL).
        :type acl: str or None

        :param meta_data: (optional) A map of metadata to store with the blob.
        :type meta_data: Dict[Any, Any] or None

        :param content_disposition: (optional) Specifies presentational
          information for the blob.
        :type content_disposition: str or None

        :param content_type: (optional) A standard MIME type describing the
          format of the object data.
        :type content_type: str or None

        :param content_length: Specifies that uploaded files can only be
          between a certain size range in bytes.
        :type content_length: tuple[int, int] or None

        :param cache_control: (optional) Specify directives for caching
         mechanisms for the blob.
        :type cache_control: str or None

        :param extra: (optional) Extra parameters for the request.
        :type extra: Dict[Any, Any] or None

        :return: Dictionary with URL and form fields (includes signature or
          policy) or header fields.
        :rtype: Dict[Any, Any]
        """
        pass

    @abstractmethod
    def generate_blob_download_url(
        self,
        blob: "Blob",
        expires: int = 3600,
        method: str = "GET",
        content_disposition: str = None,
        extra: ExtraOptions = None,
    ) -> str:
        """Generates a signed URL for this blob.

        .. important:: This class method is called by
          :meth:`.Blob.generate_download_url`.

        :param blob: The blob to download with a signed URL.
        :type blob: Blob

        :param expires: (optional) Expiration in seconds.
        :type expires: int

        :param method: (optional) HTTP request method. Defaults to `GET`.
        :type method: str

        :param content_disposition: (optional) Sets the Content-Disposition
          header of the response.
        :type content_disposition: str or None

        :param extra: (optional) Extra parameters for the request.
        :type extra: Dict[Any, Any] or None

        :return: Pre-signed URL for downloading a blob.
        :rtype: str
        """
        pass

    def __repr__(self):
        if self.region:
            return "<Driver: %s %s>" % (self.name, self.region)

        return "<Driver: %s>" % self.name

    _POST_OBJECT_KEYS = CaseInsensitiveDict()  # type: CaseInsensitiveDict
    _GET_OBJECT_KEYS = CaseInsensitiveDict()  # type: CaseInsensitiveDict
    _PUT_OBJECT_KEYS = CaseInsensitiveDict()  # type: CaseInsensitiveDict
    _DELETE_OBJECT_KEYS = CaseInsensitiveDict()  # type: CaseInsensitiveDict

    _POST_CONTAINER_KEYS = CaseInsensitiveDict()  # type: CaseInsensitiveDict
    _GET_CONTAINER_KEYS = CaseInsensitiveDict()  # type: CaseInsensitiveDict
    _PUT_CONTAINER_KEYS = CaseInsensitiveDict()  # type: CaseInsensitiveDict
    _DELETE_CONTAINER_KEYS = CaseInsensitiveDict()  # type: CaseInsensitiveDict
