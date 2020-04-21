"""Microsoft Azure Storage Driver."""
import base64
import codecs
import logging
from datetime import datetime, timedelta
from typing import Dict, Iterable, List

from azure.common import (
    AzureConflictHttpError,
    AzureHttpError,
    AzureMissingResourceHttpError,
)
from azure.storage.blob import BlockBlobService, PublicAccess
from azure.storage.blob.models import (
    Blob as AzureBlob,
    BlobPermissions,
    Container as AzureContainer,
    ContentSettings,
    Include,
)
from inflection import underscore

from cloudstorage import Blob, Container, Driver, messages
from cloudstorage.exceptions import (
    CloudStorageError,
    CredentialsError,
    IsNotEmptyError,
    NotFoundError,
)
from cloudstorage.helpers import file_checksum, validate_file_or_path
from cloudstorage.typed import (
    ContentLength,
    ExtraOptions,
    FileLike,
    FormPost,
    MetaData,
)

__all__ = ["AzureStorageDriver"]

logger = logging.getLogger(__name__)


class AzureStorageDriver(Driver):
    """Driver for interacting with Microsoft Azure Storage.

    .. code-block:: python

        from cloudstorage.drivers.microsoft import AzureStorageDriver

        storage = AzureStorageDriver(account_name='<my-azure-account-name>',
                   key='<my-azure-account-key>')
        # <Driver: AZURE>

    .. todo: Support for container or blob encryption key.

    References:

    * `Blob Service REST API <https://docs.microsoft.com/en-us/rest/api/
      storageservices/blob-service-rest-api>`_
    * `Azure/azure-storage-python
      <https://github.com/Azure/azure-storage-python>`_
    * `Uploading files to Azure Storage using SAS
      <https://blogs.msdn.microsoft.com/azureossds/2015/03/30/
      uploading-files-to-azure-storage-using-sasshared-access-signature/>`_

    :param account_name: Azure storage account name.
    :type account_name: str

    :param key: Azure storage account key.
    :type key: str

    :param kwargs: (optional) Extra driver options.
    :type kwargs: dict
    """

    name = "AZURE"
    hash_type = "md5"
    url = "https://azure.microsoft.com/en-us/services/storage/"

    def __init__(self, account_name: str, key: str, **kwargs: Dict) -> None:
        super().__init__(key=key, **kwargs)
        self._service = BlockBlobService(
            account_name=account_name, account_key=key, **kwargs
        )

    def __iter__(self) -> Iterable[Container]:
        azure_containers = self.service.list_containers(include_metadata=True)
        for azure_container in azure_containers:
            yield self._convert_azure_container(azure_container)

    def __len__(self) -> int:
        azure_containers = self.service.list_containers()
        return len(azure_containers)

    @staticmethod
    def _normalize_parameters(
        params: Dict[str, str], normalizers: Dict[str, str]
    ) -> Dict[str, str]:
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
        """Get Azure Storage blob by container and blob name.

        :param container_name: The name of the container that containers the
          blob.
        :type container_name: str

        :param blob_name: The name of the blob to get.
        :type blob_name: str

        :return: The blob object if it exists.
        :rtype: :class:`azure.storage.blob.models.Blob`
        """
        try:
            azure_blob = self.service.get_blob_properties(container_name, blob_name)
        except AzureMissingResourceHttpError as err:
            logger.debug(err)
            raise NotFoundError(messages.BLOB_NOT_FOUND % (blob_name, container_name))

        return azure_blob

    def _convert_azure_blob(self, container: Container, azure_blob: AzureBlob) -> Blob:
        """Convert Azure Storage Blob to a Cloud Storage Blob.

        :param container: Container instance.
        :type container: :class:`.Container`

        :param azure_blob: Azure Storage blob.
        :type azure_blob: :class:`azure.storage.blob.models.Blob`

        :return: Blob instance.
        :rtype: :class:`.Blob`
        """
        content_settings = azure_blob.properties.content_settings

        if content_settings.content_md5:
            # TODO: CODE: Move to helper since google uses it too.
            md5_bytes = base64.b64decode(content_settings.content_md5)

            try:
                checksum = md5_bytes.hex()
            except AttributeError:
                # Python 3.4: 'bytes' object has no attribute 'hex'
                checksum = codecs.encode(md5_bytes, "hex_codec").decode("ascii")
        else:
            logger.warning("Content MD5 not populated, content will not be validated")
            checksum = None

        return Blob(
            name=azure_blob.name,
            size=azure_blob.properties.content_length,
            checksum=checksum,
            etag=azure_blob.properties.etag,
            container=container,
            driver=self,
            acl=None,
            meta_data=azure_blob.metadata,
            content_disposition=content_settings.content_disposition,
            content_type=content_settings.content_type,
            cache_control=content_settings.cache_control,
            created_at=None,
            modified_at=azure_blob.properties.last_modified,
            expires_at=None,
        )

    def _get_azure_container(self, container_name: str) -> AzureContainer:
        """Get Azure Storage container by name.

        :param container_name: The name of the container to get.
        :type container_name: str

        :return: The container matching the name provided.
        :rtype: :class:`azure.storage.blob.models.Container`
        """
        try:
            azure_container = self.service.get_container_properties(container_name)
        except AzureMissingResourceHttpError as err:
            logger.debug(err)
            raise NotFoundError(messages.CONTAINER_NOT_FOUND % container_name)

        return azure_container

    def _convert_azure_container(self, azure_container: AzureContainer) -> Container:
        """Convert Azure Storage container to Cloud Storage Container.

        :param azure_container: The container to convert.
        :type azure_container: :class:`azure.storage.blob.models.Container`

        :return: A container instance.
        :rtype: :class:`.Container`
        """
        return Container(
            name=azure_container.name,
            driver=self,
            acl=azure_container.properties.public_access,
            meta_data=azure_container.metadata,
            created_at=azure_container.properties.last_modified,
        )

    @property
    def service(self) -> BlockBlobService:
        """The block blob service bound to this driver.

        :return: Service for interacting with the Microsoft Azure Storage API.
        :rtype: :class:`azure.storage.blob.blockblobservice.BlockBlobService`
        """
        return self._service

    def validate_credentials(self) -> None:
        try:
            for _ in self.service.list_containers():
                break
        except AzureHttpError as err:
            raise CredentialsError(str(err))

    @property
    def regions(self) -> List[str]:
        logger.warning("Regions not supported.")
        return []

    def create_container(
        self, container_name: str, acl: str = None, meta_data: MetaData = None
    ) -> Container:
        meta_data = meta_data if meta_data is not None else {}

        # Review options: Off, Blob, Container
        if acl == "container-public-access":
            public_access = PublicAccess.Container
        elif acl == "blob-public-access":
            public_access = PublicAccess.Blob
        else:
            public_access = None

        try:
            self.service.create_container(
                container_name,
                metadata=meta_data,
                public_access=public_access,
                fail_on_exist=False,
            )
        except AzureConflictHttpError:
            logger.debug(messages.CONTAINER_EXISTS, container_name)
        except AzureHttpError as err:
            logger.debug(err)
            raise CloudStorageError(str(err))

        azure_container = self._get_azure_container(container_name)
        return self._convert_azure_container(azure_container)

    def get_container(self, container_name: str) -> Container:
        azure_container = self._get_azure_container(container_name)
        return self._convert_azure_container(azure_container)

    def patch_container(self, container: Container) -> None:
        raise NotImplementedError

    def delete_container(self, container: Container) -> None:
        azure_container = self._get_azure_container(container.name)
        azure_blobs = self.service.list_blobs(azure_container.name, num_results=1)
        if len(azure_blobs.items) > 0:
            raise IsNotEmptyError(messages.CONTAINER_NOT_EMPTY % azure_container.name)

        self.service.delete_container(azure_container.name, fail_not_exist=False)

    def container_cdn_url(self, container: Container) -> str:
        azure_container = self._get_azure_container(container.name)
        url = "{}://{}/{}".format(
            self.service.protocol, self.service.primary_endpoint, azure_container.name,
        )
        return url

    def enable_container_cdn(self, container: Container) -> bool:
        logger.warning(messages.FEATURE_NOT_SUPPORTED, "enable_container_cdn")
        return False

    def disable_container_cdn(self, container: Container) -> bool:
        logger.warning(messages.FEATURE_NOT_SUPPORTED, "disable_container_cdn")
        return False

    def upload_blob(
        self,
        container: Container,
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
        if acl:
            logger.info(messages.OPTION_NOT_SUPPORTED, "acl")

        meta_data = {} if meta_data is None else meta_data
        extra = extra if extra is not None else {}

        extra_args = self._normalize_parameters(extra, self._PUT_OBJECT_KEYS)
        extra_args.setdefault("content_type", content_type)
        extra_args.setdefault("content_disposition", content_disposition)
        extra_args.setdefault("cache_control", cache_control)

        azure_container = self._get_azure_container(container.name)
        blob_name = blob_name or validate_file_or_path(filename)

        # azure does not set content_md5 on backend
        file_hash = file_checksum(filename, hash_type=self.hash_type)
        file_digest = file_hash.digest()
        checksum = base64.b64encode(file_digest).decode("utf-8").strip()
        extra_args.setdefault("content_md5", checksum)

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
        return self._convert_azure_blob(container, azure_blob)

    def get_blob(self, container: Container, blob_name: str) -> Blob:
        azure_container = self._get_azure_container(container.name)
        azure_blob = self._get_azure_blob(azure_container.name, blob_name)
        return self._convert_azure_blob(container, azure_blob)

    def get_blobs(self, container: Container) -> Iterable[Blob]:
        azure_container = self._get_azure_container(container.name)

        azure_blobs = self.service.list_blobs(
            azure_container.name, include=Include(metadata=True)
        )
        for azure_blob in azure_blobs:
            yield self._convert_azure_blob(container, azure_blob)

    def download_blob(self, blob: Blob, destination: FileLike) -> None:
        azure_blob = self._get_azure_blob(blob.container.name, blob.name)

        if isinstance(destination, str):
            self.service.get_blob_to_path(
                container_name=blob.container.name,
                blob_name=azure_blob.name,
                file_path=destination,
            )
        else:
            self.service.get_blob_to_stream(
                container_name=blob.container.name,
                blob_name=azure_blob.name,
                stream=destination,
            )

    def patch_blob(self, blob: Blob) -> None:
        pass

    def delete_blob(self, blob: Blob) -> None:
        azure_blob = self._get_azure_blob(blob.container.name, blob.name)
        self.service.delete_blob(blob.container.name, azure_blob.name)

    def blob_cdn_url(self, blob: Blob) -> str:
        azure_blob = self._get_azure_blob(blob.container.name, blob.name)
        url = self.service.make_blob_url(blob.container.name, azure_blob.name)
        return url

    def generate_container_upload_url(
        self,
        container: Container,
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
        if acl:
            logger.info(messages.OPTION_NOT_SUPPORTED, "acl")

        meta_data = meta_data if meta_data is not None else {}
        extra = extra if extra is not None else {}
        params = self._normalize_parameters(extra, self._POST_OBJECT_KEYS)

        azure_container = self._get_azure_container(container.name)
        expires_at = datetime.utcnow() + timedelta(seconds=expires)

        sas_token = self.service.generate_container_shared_access_signature(
            container_name=azure_container.name,
            permission=BlobPermissions.WRITE,
            expiry=expires_at,
            content_disposition=content_disposition,
            content_type=content_type,
            **params,
        )

        headers = {
            "x-ms-blob-type": "BlockBlob",
            "x-ms-blob-content-type": content_type,
            "x-ms-blob-content-disposition": content_disposition,
            "x-ms-blob-cache-control": cache_control,
        }
        for meta_key, meta_value in meta_data.items():
            key = self._OBJECT_META_PREFIX + meta_key
            headers[key] = meta_value

        upload_url = self.service.make_blob_url(
            container_name=azure_container.name,
            blob_name=blob_name,
            sas_token=sas_token,
        )
        return {"url": upload_url, "fields": None, "headers": headers}

    def generate_blob_download_url(
        self,
        blob: Blob,
        expires: int = 3600,
        method: str = "GET",
        content_disposition: str = None,
        extra: ExtraOptions = None,
    ) -> str:
        extra = extra if extra is not None else {}
        params = self._normalize_parameters(extra, self._GET_OBJECT_KEYS)

        azure_blob = self._get_azure_blob(blob.container.name, blob.name)
        content_type = params.get("content_type", None)
        expires_at = datetime.utcnow() + timedelta(seconds=expires)

        sas_token = self.service.generate_blob_shared_access_signature(
            container_name=blob.container.name,
            blob_name=azure_blob.name,
            permission=BlobPermissions.READ,
            expiry=expires_at,
            content_disposition=content_disposition,
            content_type=content_type,
            **params,
        )
        download_url = self.service.make_blob_url(
            container_name=blob.container.name,
            blob_name=azure_blob.name,
            sas_token=sas_token,
        )
        return download_url

    _OBJECT_META_PREFIX = "x-ms-meta-"

    #: `insert-object
    #: <https://docs.microsoft.com/en-us/rest/api/storageservices/
    # set-blob-properties>`
    _PUT_OBJECT_KEYS = {}  # type: Dict

    #: `post-object
    #: <https://docs.microsoft.com/en-us/rest/api/storageservices/put-blob>`_
    _POST_OBJECT_KEYS = {}  # type: Dict

    #: `get-object
    #: <https://docs.microsoft.com/en-us/rest/api/storageservices/get-blob>`_
    _GET_OBJECT_KEYS = {}  # type: Dict
