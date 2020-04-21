"""Google Cloud Storage Driver."""
import base64
import codecs
import logging
import os
import pathlib
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any, Dict, Iterable, List  # noqa: F401

# noinspection PyPackageRequirements
from google.auth.exceptions import GoogleAuthError

# noinspection PyPackageRequirements
from google.cloud import storage

# noinspection PyPackageRequirements
from google.cloud.exceptions import Conflict, NotFound

# noinspection PyPackageRequirements
from google.cloud.storage.blob import Blob as GoogleBlob

# noinspection PyPackageRequirements
from google.cloud.storage.bucket import Bucket
from inflection import underscore

from cloudstorage import Blob, Container, Driver, messages
from cloudstorage.exceptions import (
    CloudStorageError,
    CredentialsError,
    IsNotEmptyError,
    NotFoundError,
)
from cloudstorage.helpers import file_content_type, validate_file_or_path
from cloudstorage.typed import (
    ContentLength,
    ExtraOptions,
    FileLike,
    FormPost,
    MetaData,
)

__all__ = ["GoogleStorageDriver"]

logger = logging.getLogger(__name__)


class GoogleStorageDriver(Driver):
    """Driver for interacting with Google Cloud Storage.

    The driver will check for `GOOGLE_APPLICATION_CREDENTIALS` environment
    variable before connecting. If not found, the driver will use service
    worker credentials json file path passed to `key` argument.

    .. code-block:: python

        from cloudstorage.drivers.google import GoogleStorageDriver

        credentials_json_file = '/path/cloud-storage-service-account.json'
        storage = GoogleStorageDriver(key=credentials_json_file)
        # <Driver: GOOGLESTORAGE>

    .. todo: Support for container or blob encryption key.
    .. todo: Support for buckets with more than 256 objects on iteration.

    References:

    * `Google Cloud Storage Documentation
      <https://cloud.google.com/storage/docs>`_
    * `Storage Client
      <https://googleapis.github.io/google-cloud-python/latest/storage/index.html>`_
    * `snippets.py
      <https://github.com/GoogleCloudPlatform/python-docs-samples/blob/
      master/storage/cloud-client/snippets_test.py>`_

    :param key: (optional) File path to service worker credentials json file.
    :type key: str or None

    :param kwargs: (optional) Extra driver options.
    :type kwargs: dict

    :raise CloudStorageError: If `GOOGLE_APPLICATION_CREDENTIALS` environment
      variable is not set and/or credentials json file is not passed to the
      `key` argument.
    """

    name = "GOOGLESTORAGE"
    hash_type = "md5"  # TODO: QUESTION: Switch to crc32c?
    url = "https://cloud.google.com/storage"

    def __init__(self, key: str = None, **kwargs: Dict) -> None:
        super().__init__(key=key, **kwargs)

        if key:
            os.environ[self._CREDENTIALS_ENV_NAME] = key
        else:
            logger.debug(
                "No key provided, attempting to authenticate with Google Metadata API"
            )

        google_application_credentials = os.getenv(self._CREDENTIALS_ENV_NAME)
        if google_application_credentials and not os.path.isfile(
            google_application_credentials
        ):
            raise CredentialsError(
                "Please set environment variable "
                "'GOOGLE_APPLICATION_CREDENTIALS' or provider file path "
                "to Google service account key json file."
            )

        self._client = storage.Client()

    def __iter__(self) -> Iterable[Container]:
        for bucket in self.client.list_buckets():
            yield self._make_container(bucket)

    def __len__(self) -> int:
        containers = self.client.list_buckets()
        return len(list(containers))

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

    def _get_blob(self, bucket_name: str, blob_name: str) -> GoogleBlob:
        """Get a blob object by name.

        :param bucket_name: The name of the container that containers the blob.
        :type bucket_name:

        :param blob_name: The name of the blob to get.
        :type blob_name: str

        :return: The blob object if it exists.
        :rtype: :class:`google.client.storage.blob.Blob`
        """
        bucket = self._get_bucket(bucket_name)

        blob = bucket.get_blob(blob_name)
        if not blob:
            raise NotFoundError(messages.BLOB_NOT_FOUND % (blob_name, bucket_name))

        return blob

    def _get_bucket(self, bucket_name: str) -> Bucket:
        """Get a bucket by name.

        :param bucket_name: The name of the bucket to get.
        :type bucket_name: str

        :return: The bucket matching the name provided.
        :rtype: :class:`google.cloud.storage.bucket.Bucket`
        """
        try:
            return self.client.get_bucket(bucket_name)
        except NotFound:
            raise NotFoundError(messages.CONTAINER_NOT_FOUND % bucket_name)

    def _make_container(self, bucket: Bucket) -> Container:
        """Convert Google Storage Bucket to Cloud Storage Container.

        :param bucket: The bucket to convert.
        :type bucket: :class:`google.client.storage.bucket.Bucket`

        :return: A container instance.
        :rtype: :class:`.Container`
        """
        acl = bucket.acl
        created_at = bucket.time_created.astimezone(tz=None)
        return Container(
            name=bucket.name,
            driver=self,
            acl=acl,
            meta_data=None,
            created_at=created_at,
        )

    def _make_blob(self, container: Container, blob: GoogleBlob) -> Blob:
        """Convert Google Storage Blob to a Cloud Storage Blob.

        References:

        * `Objects <https://cloud.google.com/storage/docs/json_api/v1/objects>`_

        :param container: Container instance.
        :type container: :class:`.Container`

        :param blob: Google Storage blob.
        :type blob: :class:`google.cloud.storage.blob.Blob`

        :return: Blob instance.
        :rtype: :class:`.Blob`
        """
        etag_bytes = base64.b64decode(blob.etag)

        try:
            etag = etag_bytes.hex()
        except AttributeError:
            # Python 3.4: 'bytes' object has no attribute 'hex'
            etag = codecs.encode(etag_bytes, "hex_codec").decode("ascii")

        md5_bytes = base64.b64decode(blob.md5_hash)

        try:
            md5_hash = md5_bytes.hex()
        except AttributeError:
            # Python 3.4: 'bytes' object has no attribute 'hex'
            md5_hash = codecs.encode(md5_bytes, "hex_codec").decode("ascii")

        return Blob(
            name=blob.name,
            checksum=md5_hash,
            etag=etag,
            size=blob.size,
            container=container,
            driver=self,
            acl=blob.acl,
            meta_data=blob.metadata,
            content_disposition=blob.content_disposition,
            content_type=blob.content_type,
            cache_control=blob.cache_control,
            created_at=blob.time_created,
            modified_at=blob.updated,
        )

    @property
    def client(self) -> storage.client.Client:
        """The client bound to this driver.

        :return: Client for interacting with the Google Cloud Storage API.
        :rtype: :class:`google.cloud.storage.client.Client`
        """
        return self._client

    def validate_credentials(self) -> None:
        try:
            for _ in self.client.list_buckets():
                break
        except GoogleAuthError as err:
            raise CredentialsError(str(err))

    @property
    def regions(self) -> List[str]:
        logger.warning("Regions not supported.")
        return []

    def create_container(
        self, container_name: str, acl: str = None, meta_data: MetaData = None
    ) -> Container:
        if meta_data:
            logger.warning(messages.OPTION_NOT_SUPPORTED, "meta_data")

        try:
            bucket = self.client.create_bucket(container_name)
        except Conflict:
            logger.debug(messages.CONTAINER_EXISTS, container_name)
            bucket = self._get_bucket(container_name)
        except ValueError as err:
            raise CloudStorageError(str(err))

        if acl:
            bucket.acl.save_predefined(acl)

        return self._make_container(bucket)

    def get_container(self, container_name: str) -> Container:
        bucket = self._get_bucket(container_name)
        return self._make_container(bucket)

    def patch_container(self, container: Container) -> None:
        raise NotImplementedError

    def delete_container(self, container: Container) -> None:
        bucket = self._get_bucket(container.name)

        try:
            bucket.delete()
        except Conflict as err:
            if err.code == HTTPStatus.CONFLICT:
                raise IsNotEmptyError(messages.CONTAINER_NOT_EMPTY % bucket.name)
            raise

    def container_cdn_url(self, container: Container) -> str:
        return "https://storage.googleapis.com/%s" % container.name

    def enable_container_cdn(self, container: Container) -> bool:
        bucket = self._get_bucket(container.name)
        bucket.make_public(recursive=True, future=True)
        return True

    def disable_container_cdn(self, container: Container) -> bool:
        bucket = self._get_bucket(container.name)
        bucket.acl.all().revoke_read()  # opposite of make_public
        bucket.acl.save()
        return True

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
        extra = extra if extra is not None else {}
        extra_args = self._normalize_parameters(extra, self._PUT_OBJECT_KEYS)

        extra_args.setdefault("metadata", meta_data)
        extra_args.setdefault("content_type", content_type)
        extra_args.setdefault("content_disposition", content_disposition)
        extra_args.setdefault("cache_control", cache_control)

        bucket = self._get_bucket(container.name)

        blob_name = blob_name or validate_file_or_path(filename)
        blob = bucket.blob(blob_name)

        # Default Content-Type is application/octet-stream for upload_from_file
        if not content_type:
            content_type = file_content_type(blob.name)

        if isinstance(filename, str):
            blob.upload_from_filename(filename=filename, content_type=content_type)
        else:
            blob.upload_from_file(file_obj=filename, content_type=content_type)

        if acl:
            blob.acl.save_predefined(acl)

        # Google object metadata (Content-Type set above)
        for attr_name, attr_value in extra_args.items():
            if attr_name and hasattr(blob, attr_name):
                setattr(blob, attr_name, attr_value)

        blob.patch()
        return self._make_blob(container, blob)

    def get_blob(self, container: Container, blob_name: str) -> Blob:
        g_blob = self._get_blob(container.name, blob_name)
        return self._make_blob(container, g_blob)

    def get_blobs(self, container: Container) -> Iterable[Blob]:
        bucket = self._get_bucket(container.name)
        for blob in bucket.list_blobs():
            yield self._make_blob(container, blob)

    def download_blob(self, blob: Blob, destination: FileLike) -> None:
        g_blob = self._get_blob(blob.container.name, blob.name)

        if isinstance(destination, str):
            g_blob.download_to_filename(destination)
        else:
            g_blob.download_to_file(destination)

    def patch_blob(self, blob: Blob) -> None:
        raise NotImplementedError

    def delete_blob(self, blob: Blob) -> None:
        g_blob = self._get_blob(blob.container.name, blob.name)
        g_blob.delete()

    def blob_cdn_url(self, blob: Blob) -> str:
        return self._get_blob(blob.container.name, blob.name).public_url

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
        meta_data = meta_data if meta_data is not None else {}
        extra = extra if extra is not None else {}
        extra_norm = self._normalize_parameters(extra, self._POST_OBJECT_KEYS)

        bucket = self._get_bucket(container.name)

        conditions = [
            # file name can start with any valid character.
            ["starts-with", "$key", ""]
        ]  # type: List[Any]
        fields = {}

        if acl:
            conditions.append({"acl": acl})
            fields["acl"] = acl

        headers = {
            "Content-Disposition": content_disposition,
            "Content-Type": content_type,
            "Cache-Control": cache_control,
        }
        for header_name, header_value in headers.items():
            if not header_value:
                continue

            fields[header_name.lower()] = header_value
            conditions.append(["eq", "$" + header_name, header_value])

        # Add content-length-range which is a tuple
        if content_length:
            min_range, max_range = content_length
            conditions.append(["content-length-range", min_range, max_range])

        for meta_name, meta_value in meta_data.items():
            meta_name = self._OBJECT_META_PREFIX + meta_name
            fields[meta_name] = meta_value
            conditions.append({meta_name: meta_value})

        # Add extra conditions and fields
        for extra_name, extra_value in extra_norm.items():
            fields[extra_name] = extra_value
            conditions.append({extra_name: extra_value})

        # Determine key value for blob name when uploaded
        if not blob_name:  # user provided filename
            fields["key"] = "${filename}"
        else:
            path = pathlib.Path(blob_name)
            if path.suffix:  # blob_name is filename
                fields["key"] = blob_name
            else:  # prefix + user provided filename
                fields["key"] = blob_name + "${filename}"

        logger.debug("conditions=%s", conditions)
        logger.debug("fields=%s", fields)

        expiration = datetime.utcnow() + timedelta(seconds=expires)

        # noinspection PyTypeChecker
        policy = bucket.generate_upload_policy(
            conditions=conditions, expiration=expiration
        )

        fields.update(policy)
        url = "https://{bucket_name}.storage.googleapis.com".format(
            bucket_name=container.name
        )
        return {"url": url, "fields": fields}

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

        expiration = timedelta(seconds=int(expires))
        method_norm = method.upper()
        response_type = params.get("content_type", None)
        generation = params.get("version", None)

        g_blob = self._get_blob(blob.container.name, blob.name)
        return g_blob.generate_signed_url(
            expiration=expiration,
            method=method_norm,
            content_type="",
            generation=generation,
            response_disposition=content_disposition,
            response_type=response_type,
        )

    _CREDENTIALS_ENV_NAME = "GOOGLE_APPLICATION_CREDENTIALS"
    _OBJECT_META_PREFIX = "x-goog-meta-"

    #: `insert-object
    #: <https://cloud.google.com/storage/docs/json_api/v1/objects/insert>`
    #: Mapping is for blob class attribute names
    _PUT_OBJECT_KEYS = {
        "acl": "acl",
        "bucket": "bucket",
        "cache_control": "cache_control",
        "content_disposition": "content_disposition",
        "content_encoding": "content_encoding",
        "content_length": "content_length",
        "content_type": "content_type",
        "expires": "expires",
        "meta_data": "metadata",
    }

    #: `post-object
    #: <https://cloud.google.com/storage/docs/xml-api/post-object>`_
    _POST_OBJECT_KEYS = {
        "acl": "acl",
        "bucket": "bucket",
        "cache_control": "Cache-Control",
        "content_disposition": "Content-Disposition",
        "content_encoding": "Content-Encoding",
        "content_length": "Content-Length",
        "content_type": "Content-Type",
        "expires": "Expires",
        "key": "Key",
        "success_action_redirect": "success_action_redirect",
        "success_action_status": "success_action_status",
        "meta_data": "Metadata",
        "x_goog_meta_": "x-goog-meta-",
        "content_length_range": "content-length-range",
    }

    #: `get-object
    #: <https://cloud.google.com/storage/docs/xml-api/get-object>`_
    _GET_OBJECT_KEYS = {
        "content_disposition": "response_disposition",
        "content_type": "response_type",
    }
