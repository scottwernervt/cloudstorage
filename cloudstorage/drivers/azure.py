"""Microsoft Azure Storage Driver."""

import logging

try:
    from http import HTTPStatus
except ImportError:
    # noinspection PyUnresolvedReferences
    from httpstatus import HTTPStatus
from typing import Dict, Iterable, List, Union

from azure.storage.blob import BlockBlobService
from azure.storage.blob.models import Blob as AzureBlob
from azure.storage.blob.models import Container as AzureContainer

from inflection import underscore

from cloudstorage.base import (
    Blob, Container, ContentLength, Driver,
    ExtraOptions, FileLike, FormPost, MetaData,
)

logger = logging.getLogger(__name__)


class AzureStorageDriver(Driver):
    """Driver for interacting with Microsoft Azure Storage.
    """

    name = 'AZURE'
    hash_type = 'md5'
    url = 'https://azure.microsoft.com/en-us/services/storage/'

    def __init__(self, account_name: str = None, key: str = None,
                 **kwargs: Dict) -> None:
        super().__init__(key=key)
        self._service = BlockBlobService(account_name=account_name,
                                         account_key=key, **kwargs)

    def __iter__(self) -> Iterable[Container]:
        pass

    def __len__(self) -> int:
        pass

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

    def _get_blob(self, container_name: str, blob_name: str) -> AzureBlob:
        pass

    def _get_container(self, container_name: str) -> AzureContainer:
        pass

    def _make_container(self, container: AzureContainer) -> Container:
        pass

    def _make_blob(self, container: Container, blob: AzureBlob) -> Blob:
        pass

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
        pass

    def get_container(self, container_name: str) -> Container:
        pass

    def patch_container(self, container: Container) -> None:
        pass

    def delete_container(self, container: Container) -> None:
        pass

    def container_cdn_url(self, container: Container) -> str:
        pass

    def enable_container_cdn(self, container: Container) -> bool:
        pass

    def disable_container_cdn(self, container: Container) -> bool:
        pass

    def upload_blob(self, container: Container, filename: Union[str, FileLike],
                    blob_name: str = None, acl: str = None,
                    meta_data: MetaData = None, content_type: str = None,
                    content_disposition: str = None, chunk_size: int = 1024,
                    extra: ExtraOptions = None) -> Blob:
        pass

    def get_blob(self, container: Container, blob_name: str) -> Blob:
        pass

    def get_blobs(self, container: Container) -> Iterable[Blob]:
        pass

    def download_blob(self, blob: Blob,
                      destination: Union[str, FileLike]) -> None:
        pass

    def patch_blob(self, blob: Blob) -> None:
        pass

    def delete_blob(self, blob: Blob) -> None:
        pass

    def blob_cdn_url(self, blob: Blob) -> str:
        pass

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
