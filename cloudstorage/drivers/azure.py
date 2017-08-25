"""Microsoft Azure Storage Driver."""

import logging

import base64
import codecs

try:
    from http import HTTPStatus
except ImportError:
    # noinspection PyUnresolvedReferences
    from httpstatus import HTTPStatus
from typing import Dict, Iterable, List, Union

from azure.common import AzureMissingResourceHttpError
from azure.common import AzureHttpError
from azure.common import AzureConflictHttpError
from azure.storage.blob import PublicAccess
from azure.storage.blob import BlockBlobService
from azure.storage.blob.models import Blob as AzureBlob
from azure.storage.blob.models import Container as AzureContainer
from azure.storage.blob.models import Include
from azure.storage.blob.models import ContentSettings

from inflection import underscore

from cloudstorage.helpers import validate_file_or_path
from cloudstorage.exceptions import NotFoundError
from cloudstorage.exceptions import CloudStorageError
from cloudstorage.exceptions import IsNotEmptyError
from cloudstorage.base import Blob
from cloudstorage.base import Container
from cloudstorage.base import ContentLength
from cloudstorage.base import Driver
from cloudstorage.base import ExtraOptions
from cloudstorage.base import FileLike
from cloudstorage.base import FormPost
from cloudstorage.base import MetaData
from cloudstorage.messages import CONTAINER_NOT_FOUND
from cloudstorage.messages import CONTAINER_EXISTS
from cloudstorage.messages import CONTAINER_NOT_EMPTY
from cloudstorage.messages import BLOB_NOT_FOUND
from cloudstorage.helpers import file_checksum

logger = logging.getLogger(__name__)


class AzureStorageDriver(Driver):
    """Driver for interacting with Microsoft Azure Storage.
    """

    # TODO: QUESTION: Do we want to just call service functions instead of check
    # if container or blob exists? We would need to handle exceptions for each
    # case.

    name = 'AZURE'
    hash_type = 'md5'
    url = 'https://azure.microsoft.com/en-us/services/storage/'

    def __init__(self, account_name: str = None, key: str = None,
                 **kwargs: Dict) -> None:
        super().__init__(key=key)
        self._service = BlockBlobService(account_name=account_name,
                                         account_key=key, **kwargs)

    def __iter__(self) -> Iterable[Container]:
        azure_containers = self.service.list_containers(include_metadata=True)
        for azure_container in azure_containers:
            yield self._wrap_azure_container(azure_container)

    def __len__(self) -> int:
        azure_containers = self.service.list_containers()
        return len(azure_containers)

    @staticmethod
    def _normalize_parameters(params: Dict[str, str],
                              normalizers: Dict[str, str]) -> Dict[str, str]:
        normalized = params.copy()

        for key, value in params.items():
            normalized.pop(key)
            if not value:
                continue

            key_inflected = underscore(key).lower()

            # Only include parameters found in normalizers
            key_overrider = normalizers.get(key_inflected)
            if key_overrider:
                normalized[key_overrider] = value

        return normalized

    def _get_azure_blob(self, container_name: str, blob_name: str) -> AzureBlob:
        try:
            azure_blob = self.service.get_blob_properties(container_name,
                                                          blob_name)
        except AzureMissingResourceHttpError as err:
            logger.debug(err)
            raise NotFoundError(BLOB_NOT_FOUND % (blob_name, container_name))

        return azure_blob

    def _wrap_azure_blob(self, container: Container,
                         azure_blob: AzureBlob) -> Blob:
        content_settings = azure_blob.properties.content_settings

        # TODO: CODE: Move to helper since google uses it too.
        md5_bytes = base64.b64decode(content_settings.content_md5)

        try:
            checksum = md5_bytes.hex()
        except AttributeError:
            # Python 3.4: 'bytes' object has no attribute 'hex'
            checksum = codecs.encode(md5_bytes, 'hex_codec').decode('ascii')

        return Blob(name=azure_blob.name,
                    size=azure_blob.properties.content_length,
                    checksum=checksum,
                    etag=azure_blob.properties.etag,
                    container=container,
                    driver=self,
                    acl=None,
                    meta_data=azure_blob.metadata,
                    content_disposition=content_settings.content_disposition,
                    content_type=content_settings.content_type,
                    created_at=None,
                    modified_at=azure_blob.properties.last_modified,
                    expires_at=None)

    def _get_azure_container(self, container_name: str) -> AzureContainer:
        try:
            azure_container = self.service.get_container_properties(
                container_name)
        except AzureMissingResourceHttpError as err:
            logger.debug(err)
            raise NotFoundError(CONTAINER_NOT_FOUND % container_name)

        return azure_container

    def _wrap_azure_container(self,
                              azure_container: AzureContainer) -> Container:
        return Container(name=azure_container.name,
                         driver=self,
                         acl=azure_container.properties.public_access,
                         meta_data=azure_container.metadata,
                         created_at=azure_container.properties.last_modified)

    @property
    def service(self) -> BlockBlobService:
        """The block blob service bound to this driver.

        :return: Service for interacting with the Microsoft Azure Storage API.
        :rtype: :class:`azure.storage.blob.blockblobservice.BlockBlobService`
        """
        return self._service

    @property
    def regions(self) -> List[str]:
        logger.warning('Regions not supported.')
        return []

    def create_container(self, container_name: str, acl: str = None,
                         meta_data: MetaData = None) -> Container:
        meta_data = meta_data if meta_data is not None else {}

        if acl == 'public-read':
            public_access = PublicAccess.Container
        else:
            public_access = None

        try:
            self.service.create_container(container_name,
                                          metadata=meta_data,
                                          public_access=public_access,
                                          fail_on_exist=False)
        except AzureConflictHttpError:
            logger.debug(CONTAINER_EXISTS, container_name)
        except AzureHttpError as err:
            logger.debug(err)
            raise CloudStorageError(str(err))

        azure_container = self._get_azure_container(container_name)
        return self._wrap_azure_container(azure_container)

    def get_container(self, container_name: str) -> Container:
        azure_container = self._get_azure_container(container_name)
        return self._wrap_azure_container(azure_container)

    def patch_container(self, container: Container) -> None:
        raise NotImplementedError

    def delete_container(self, container: Container) -> None:
        azure_container = self._get_azure_container(container.name)
        azure_blobs = self.service.list_blobs(azure_container.name,
                                              num_results=1)
        if len(azure_blobs.items) > 0:
            raise IsNotEmptyError(CONTAINER_NOT_EMPTY % azure_container.name)

        self.service.delete_container(azure_container.name,
                                      fail_not_exist=False)

    def container_cdn_url(self, container: Container) -> str:
        azure_container = self._get_azure_container(container.name)
        url = '{}://{}/{}'.format(
            self.service.protocol,
            self.service.primary_endpoint,
            azure_container.name,
        )
        return url

    def enable_container_cdn(self, container: Container) -> bool:
        azure_container = self._get_azure_container(container.name)
        self.service.set_container_acl(azure_container.name,
                                       public_access=PublicAccess.Container)
        return True

    def disable_container_cdn(self, container: Container) -> bool:
        azure_container = self._get_azure_container(container.name)
        self.service.set_container_acl(azure_container.name, public_access=None)
        return True

    def upload_blob(self, container: Container, filename: Union[str, FileLike],
                    blob_name: str = None, acl: str = None,
                    meta_data: MetaData = None, content_type: str = None,
                    content_disposition: str = None, chunk_size: int = 1024,
                    extra: ExtraOptions = None) -> Blob:
        meta_data = {} if meta_data is None else meta_data
        extra = extra if extra is not None else {}

        extra_args = self._normalize_parameters(extra, self._PUT_OBJECT_KEYS)
        extra_args.setdefault('content_type', content_type)
        extra_args.setdefault('content_disposition', content_disposition)

        azure_container = self._get_azure_container(container.name)
        blob_name = blob_name or validate_file_or_path(filename)

        # azure does not set content_md5 on backend
        file_hash = file_checksum(filename, hash_type=self.hash_type)
        file_digest = file_hash.digest()
        checksum = base64.b64encode(file_digest).decode('utf-8').strip()
        extra_args.setdefault('content_md5', checksum)

        content_settings = ContentSettings(**extra_args)

        if isinstance(filename, str):
            self.service.create_blob_from_path(
                container_name=azure_container.name,
                blob_name=blob_name,
                file_path=filename,
                content_settings=content_settings,
                metadata=meta_data,
                validate_content=True,
            )
        else:
            self.service.create_blob_from_stream(
                container_name=azure_container.name,
                blob_name=blob_name,
                stream=filename,
                content_settings=content_settings,
                metadata=meta_data,
                validate_content=True,
            )

        azure_blob = self._get_azure_blob(azure_container.name, blob_name)
        return self._wrap_azure_blob(container, azure_blob)

    def get_blob(self, container: Container, blob_name: str) -> Blob:
        azure_container = self._get_azure_container(container.name)
        azure_blob = self._get_azure_blob(azure_container.name, blob_name)
        return self._wrap_azure_blob(container, azure_blob)

    def get_blobs(self, container: Container) -> Iterable[Blob]:
        azure_container = self._get_azure_container(container.name)

        azure_blobs = self.service.list_blobs(azure_container.name,
                                              include=Include(metadata=True))
        for azure_blob in azure_blobs:
            yield self._wrap_azure_blob(container, azure_blob)

    def download_blob(self, blob: Blob,
                      destination: Union[str, FileLike]) -> None:
        pass

    def patch_blob(self, blob: Blob) -> None:
        pass

    def delete_blob(self, blob: Blob) -> None:
        azure_blob = self._get_azure_blob(blob.container.name, blob.name)
        self.service.delete_blob(blob.container.name, azure_blob.name)

    def blob_cdn_url(self, blob: Blob) -> str:
        azure_blob = self._get_azure_blob(blob.container.name, blob.name)
        url = self.service.make_blob_url(blob.container.name, azure_blob.name)
        return url

    def generate_container_upload_url(self, container: Container,
                                      blob_name: str,
                                      expires: int = 3600, acl: str = None,
                                      meta_data: MetaData = None,
                                      content_disposition: str = None,
                                      content_length: ContentLength = None,
                                      content_type: str = None,
                                      extra: ExtraOptions = None) -> FormPost:
        pass

    def generate_blob_download_url(self, blob: Blob, expires: int = 3600,
                                   method: str = 'GET',
                                   content_disposition: str = None,
                                   extra: ExtraOptions = None) -> str:
        pass

    _OBJECT_META_PREFIX = 'x-ms-meta-'

    #: `insert-object
    #: <>`
    _PUT_OBJECT_KEYS = {
    }

    #: `post-object
    #: <>`_
    _POST_OBJECT_KEYS = {
    }

    #: `get-object
    #: <>`_
    _GET_OBJECT_KEYS = {
    }
