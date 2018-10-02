import abc
import logging
from abc import abstractmethod
from typing import Dict, Iterable, List, Optional  # noqa: F401

from cloudstorage.blob import Blob
from cloudstorage.container import Container
from cloudstorage.exceptions import NotFoundError
from cloudstorage.messages import FEATURE_NOT_SUPPORTED
from cloudstorage.typed import (
    ContentLength,
    ExtraOptions,
    FileLike,
    FormPost,
    MetaData,
)

logger = logging.getLogger(__name__)


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
    hash_type = 'md5'  # type: str

    #: Unique `str` driver URL.
    url = None  # type: Optional[str]

    def __init__(self, key: str = None, secret: str = None, region: str = None,
                 **kwargs: Dict) -> None:
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
        if hasattr(container, 'name'):
            container_name = container.name
        else:
            container_name = container

        try:
            self.get_container(container_name=container_name)
            return True
        except NotFoundError:
            return False

    @abstractmethod
    def __iter__(self) -> Iterable[Container]:
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
    def _normalize_parameters(params: Dict[str, str],
                              normalizers: Dict[str, str]) -> Dict[str, str]:
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

    @property
    @abstractmethod
    def regions(self) -> List[str]:
        """List of supported regions for this driver.

        :return: List of region strings.
        :rtype: list[str]
        """
        pass

    @abstractmethod
    def create_container(self, container_name: str, acl: str = None,
                         meta_data: MetaData = None) -> Container:
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
    def get_container(self, container_name: str) -> Container:
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
    def patch_container(self, container: Container) -> None:
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
    def delete_container(self, container: Container) -> None:
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
    def container_cdn_url(self, container: Container) -> str:
        """The Content Delivery Network URL for this container.

        .. important:: This class method is called by
          :attr:`.Container.cdn_url`.

        :return: The CDN URL for this container.
        :rtype: str
        """
        pass

    @abstractmethod
    def enable_container_cdn(self, container: Container) -> bool:
        """(Optional) Enable Content Delivery Network (CDN) for the container.

        .. important:: This class method is called by
          :meth:`.Container.enable_cdn`.

        :param container: A container instance.
        :type container: :class:`.Container`

        :return: True if successful or false if not supported.
        :rtype: bool
        """
        logger.warning(FEATURE_NOT_SUPPORTED, 'enable_container_cdn')
        return False

    @abstractmethod
    def disable_container_cdn(self, container: Container) -> bool:
        """(Optional) Disable Content Delivery Network (CDN) on the container.

        .. important:: This class method is called by
          :meth:`.Container.disable_cdn`.

        :param container: A container instance.
        :type container: :class:`.Container`

        :return: True if successful or false if not supported.
        :rtype: bool
        """
        logger.warning(FEATURE_NOT_SUPPORTED, 'disable_container_cdn')
        return False

    @abstractmethod
    def upload_blob(self, container: Container, filename: FileLike,
                    blob_name: str = None, acl: str = None,
                    meta_data: MetaData = None, content_type: str = None,
                    content_disposition: str = None, chunk_size=1024,
                    extra: ExtraOptions = None) -> Blob:
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
    def get_blob(self, container: Container, blob_name: str) -> Blob:
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
    def get_blobs(self, container: Container) -> Iterable[Blob]:
        """Get all blobs associated to the container.

        .. important:: This class method is called by :meth:`.Blob.__iter__`.

        :param container: A container instance.
        :type container: :class:`.Container`

        :return: Iterable of all blobs belonging to this container.
        :rtype: Iterable{Blob]
        """
        pass

    @abstractmethod
    def download_blob(self, blob: Blob,
                      destination: FileLike) -> None:
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
    def patch_blob(self, blob: Blob) -> None:
        """Saves all changed attributes for this blob.

        .. important:: This class method is called by :meth:`.Blob.update`.

        :return: NoneType
        :rtype: None

        :raises NotFoundError: If the blob object doesn't exist.
        """
        pass

    @abstractmethod
    def delete_blob(self, blob: Blob) -> None:
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
    def blob_cdn_url(self, blob: Blob) -> str:
        """The Content Delivery Network URL for the blob.

        .. important:: This class method is called by :attr:`.Blob.cdn_url`.

        :param blob: The public blob object.
        :type blob: Blob

        :return: The CDN URL for the blob.
        :rtype: str
        """
        pass

    @abstractmethod
    def generate_container_upload_url(self, container: Container,
                                      blob_name: str,
                                      expires: int = 3600, acl: str = None,
                                      meta_data: MetaData = None,
                                      content_disposition: str = None,
                                      content_length: ContentLength = None,
                                      content_type: str = None,
                                      extra: ExtraOptions = None) -> FormPost:
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

        :param extra: (optional) Extra parameters for the request.
        :type extra: Dict[Any, Any] or None

        :return: Dictionary with URL and form fields (includes signature or
          policy) or header fields.
        :rtype: Dict[Any, Any]
        """
        pass

    @abstractmethod
    def generate_blob_download_url(self, blob: Blob, expires: int = 3600,
                                   method: str = 'GET',
                                   content_disposition: str = None,
                                   extra: ExtraOptions = None) -> str:
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
            return '<Driver: %s %s>' % (self.name, self.region)

        return '<Driver: %s>' % self.name

    _POST_OBJECT_KEYS = {}  # type: Dict
    _GET_OBJECT_KEYS = {}  # type: Dict
    _PUT_OBJECT_KEYS = {}  # type: Dict
    _DELETE_OBJECT_KEYS = {}  # type: Dict

    _POST_CONTAINER_KEYS = {}  # type: Dict
    _GET_CONTAINER_KEYS = {}  # type: Dict
    _PUT_CONTAINER_KEYS = {}  # type: Dict
    _DELETE_CONTAINER_KEYS = {}  # type: Dict
