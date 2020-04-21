"""Minio Driver."""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Iterable, List  # noqa: F401
from urllib.parse import quote, urljoin

from inflection import camelize, underscore
from minio import Minio, PostPolicy, definitions
from minio.error import (
    BucketAlreadyExists,
    BucketAlreadyOwnedByYou,
    BucketNotEmpty,
    InvalidAccessKeyId,
    InvalidBucketError,
    InvalidBucketName,
    NoSuchKey,
    ResponseError,
    SignatureDoesNotMatch,
)

from cloudstorage import Blob, Container, Driver, messages
from cloudstorage.exceptions import (
    CloudStorageError,
    CredentialsError,
    IsNotEmptyError,
    NotFoundError,
)
from cloudstorage.helpers import (
    file_content_type,
    validate_file_or_path,
)
from cloudstorage.typed import (
    ContentLength,
    ExtraOptions,
    FileLike,
    FormPost,
    MetaData,
)

__all__ = ["MinioDriver"]

logger = logging.getLogger(__name__)

_REGIONS = [
    "us-east-1",
    "us-west-1",
    "us-west-2",
    "eu-west-1",
    "eu-central-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-1",
    "ap-northeast-2",
    "sa-east-1",
    "cn-north-1",
]


class MinioDriver(Driver):
    """Driver for interacting with any Minio compatible object storage
    server.

    .. code-block:: python

        from cloudstorage.drivers.minio import MinioDriver

        storage = MinioDriver(endpoint='minioserver:port',
                   key='<my-access-key-id>',
                   secret='<my-secret-access-key>',
                   region='us-east-1',
                   secure=True)
        # <Driver: Minio us-east-1>

    References:

    * `Python Client API Reference
      <https://docs.minio.io/docs/python-client-api-reference.html>`_
    * `Minio Python Library <https://github.com/minio/minio-py>`_

    :param endpoint: Minio server to connect to.
    :type endpoint: str

    :param key: Minio access key.
    :type key: str

    :param secret: Minio secret key.
    :type secret: str

    :param region: (optional) Region to connect to. Defaults to `us-east-1`.
    :type region: str

    :param kwargs: (optional) Extra driver options.

                   * secure (`bool`): Use secure connection.
                   * http_client (:class:`urllib3.poolmanager.PoolManager`):
                     Use custom http client.
    :type kwargs: dict
    """

    name = "MINIO"
    url = "https://www.minio.io"

    def __init__(
        self,
        endpoint: str,
        key: str,
        secret: str = None,
        region: str = "us-east-1",
        **kwargs: Dict
    ) -> None:
        secure = kwargs.pop("secure", True)
        http_client = kwargs.pop("http_client", None)
        self._client = Minio(
            endpoint,
            access_key=key,
            secret_key=secret,
            secure=secure,
            region=region,
            http_client=http_client,
        )
        super().__init__(key=key, secret=secret, region=region, **kwargs)

    def __iter__(self) -> Iterable[Container]:
        for bucket in self.client.list_buckets():
            yield self._make_container(bucket)

    def __len__(self) -> int:
        buckets = [bucket for bucket in self.client.list_buckets()]
        return len(buckets)

    @staticmethod
    def _normalize_parameters(
        params: Dict[str, str], normalizers: Dict[str, str]
    ) -> Dict[str, str]:
        normalized = params.copy()

        for key, value in params.items():
            normalized.pop(key)
            if not value:
                continue

            key_inflected = camelize(underscore(key), uppercase_first_letter=True)
            # Only include parameters found in normalizers
            key_overrider = normalizers.get(key_inflected.lower())
            if key_overrider:
                normalized[key_overrider] = value

        return normalized

    def _get_bucket(self, bucket_name: str) -> definitions.Bucket:
        """Get a Minio bucket.

        :param bucket_name: The Bucket's name identifier.
        :type bucket_name: str

        :return: Bucket resource object.
        :rtype: :class:`minio.definitions.Bucket`

        :raises NotFoundError: If the bucket does not exist.
        """
        for bucket in self.client.list_buckets():
            if bucket.name == bucket_name:
                return bucket
        raise NotFoundError(messages.CONTAINER_NOT_FOUND % bucket_name)

    def _make_obj(self, container: Container, obj: definitions.Object) -> Blob:
        """Convert Minio Object to Blob instance.

        :param container: The container that holds the blob.
        :type container: :class:`.Container`

        :param obj: Minio object stats.
        :type obj: :class:`minio.definitions.Object`

        :return: A blob object.
        :rtype: :class:`.Blob`
        """
        obj_metadata = {} if obj.metadata is None else obj.metadata
        meta_data = {}
        for name, value in obj_metadata.items():
            meta_key = re.sub(
                r"\b%s\b" % re.escape(self._OBJECT_META_PREFIX),
                "",
                name,
                flags=re.IGNORECASE,
            )
            if meta_key != name:  # Content-Type key is in the obj meta data
                meta_data[meta_key] = value

        return Blob(
            name=obj.object_name,
            checksum="",
            etag=obj.etag,
            size=obj.size,
            container=container,
            driver=self,
            acl={},
            meta_data=meta_data,
            content_disposition=None,
            content_type=obj.content_type,
            cache_control=None,
            created_at=None,
            modified_at=obj.last_modified,
            expires_at=None,
        )

    def _make_container(self, bucket: definitions.Bucket) -> Container:
        """Convert Minio Bucket to Container.

        :param bucket: Minio bucket.
        :type bucket: :class:`minio.definitions.Bucket`

        :return: The container if it exists.
        :rtype: :class:`.Container`
        """
        created_at = bucket.creation_date.astimezone(tz=None)
        return Container(
            name=bucket.name, driver=self, acl="", meta_data=None, created_at=created_at
        )

    @property
    def client(self) -> Minio:
        """Minio client session.

        :return: Minio client session.
        :rtype: :class:`minio.Minio`
        """
        return self._client

    def validate_credentials(self) -> None:
        try:
            for _ in self.client.list_buckets():
                break
        except (InvalidAccessKeyId, SignatureDoesNotMatch) as err:
            raise CredentialsError(str(err))

    @property
    def regions(self) -> List[str]:
        return _REGIONS

    def create_container(
        self, container_name: str, acl: str = None, meta_data: MetaData = None
    ) -> Container:
        if meta_data:
            logger.info(messages.OPTION_NOT_SUPPORTED, "meta_data")

        if acl:
            logger.info(messages.OPTION_NOT_SUPPORTED, "acl")

        try:
            self.client.make_bucket(container_name)
        except (BucketAlreadyExists, BucketAlreadyOwnedByYou):
            pass
        except (InvalidBucketName, InvalidBucketError, ResponseError) as err:
            raise CloudStorageError(str(err))

        bucket = self._get_bucket(container_name)
        return self._make_container(bucket)

    def get_container(self, container_name: str) -> Container:
        bucket = self._get_bucket(container_name)
        return self._make_container(bucket)

    def patch_container(self, container: Container) -> None:
        raise NotImplementedError

    def delete_container(self, container: Container) -> None:
        bucket = self._get_bucket(container.name)

        try:
            self.client.remove_bucket(container.name)
        except BucketNotEmpty:
            raise IsNotEmptyError(messages.CONTAINER_NOT_EMPTY % bucket.name)

    def container_cdn_url(self, container: Container) -> str:
        return "%s/%s" % (self.client._endpoint_url, container.name)

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
        meta_data = {} if meta_data is None else meta_data
        extra = {} if extra is None else extra

        blob_name = blob_name or validate_file_or_path(filename)

        if not content_type:
            if isinstance(filename, str):
                content_type = file_content_type(filename)
            else:
                content_type = file_content_type(blob_name)

        if isinstance(filename, str):
            self.client.fput_object(
                container.name,
                blob_name,
                filename,
                content_type=content_type,
                metadata=meta_data,
            )
        else:
            length = extra.pop("length", len(filename.read()))
            filename.seek(0)
            self.client.put_object(
                container.name,
                blob_name,
                filename,
                length,
                content_type=content_type,
                metadata=meta_data,
            )
        return self.get_blob(container, blob_name)

    def get_blob(self, container: Container, blob_name: str) -> Blob:
        try:
            obj = self.client.stat_object(container.name, blob_name)
        except NoSuchKey:
            raise NotFoundError(messages.BLOB_NOT_FOUND % (blob_name, container.name))
        return self._make_obj(container, obj)

    def get_blobs(self, container: Container) -> Iterable[Blob]:
        for obj in self.client.list_objects(container.name, recursive=False):
            yield self._make_obj(container, obj)

    def download_blob(self, blob: Blob, destination: FileLike) -> None:
        data = self.client.get_object(blob.container.name, blob.name)

        if isinstance(destination, str):
            with open(destination, "wb") as blob_data:
                for d in data.stream(4096):
                    blob_data.write(d)
        else:
            for d in data.stream(4096):
                destination.write(d)

    def patch_blob(self, blob: Blob) -> None:
        raise NotImplementedError

    def delete_blob(self, blob: Blob) -> None:
        try:
            self.client.remove_object(blob.container.name, blob.name)
        except ResponseError as err:
            raise CloudStorageError(str(err))

    def blob_cdn_url(self, blob: Blob) -> str:
        container_url = self.container_cdn_url(blob.container)
        blob_name_cleaned = quote(blob.name)

        blob_path = "%s/%s" % (container_url, blob_name_cleaned)
        url = urljoin(container_url, blob_path)
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
        if content_disposition:
            logger.warning(messages.OPTION_NOT_SUPPORTED, "content_disposition")

        if cache_control:
            logger.warning(messages.OPTION_NOT_SUPPORTED, "cache_control")

        meta_data = {} if meta_data is None else meta_data

        post_policy = PostPolicy()
        post_policy.set_bucket_name(container.name)
        post_policy.set_key_startswith(blob_name)

        if content_length:
            min_range, max_range = content_length
            post_policy.set_content_length_range(min_range, max_range)

        if content_type:
            post_policy.set_content_type(content_type)

        for meta_name, meta_value in meta_data.items():
            meta_name = self._OBJECT_META_PREFIX + meta_name
            post_policy.policies.append(("eq", "$%s" % meta_name, meta_value))
            post_policy.form_data[meta_name] = meta_value

        expires_date = datetime.utcnow() + timedelta(seconds=expires)
        post_policy.set_expires(expires_date)

        url, fields = self.client.presigned_post_policy(post_policy)
        return {"url": url, "fields": fields}

    def generate_blob_download_url(
        self,
        blob: Blob,
        expires: int = 3600,
        method: str = "GET",
        content_disposition: str = None,
        extra: ExtraOptions = None,
    ) -> str:
        extra = {} if extra is None else extra

        response_headers = self._normalize_parameters(extra, self._GET_OBJECT_KEYS)
        if content_disposition:
            response_headers.setdefault(
                "response-content-disposition", content_disposition
            )

        expires = timedelta(seconds=int(expires))
        url = self.client.presigned_get_object(
            blob.container.name, blob.name, expires, response_headers
        )
        return url

    _OBJECT_META_PREFIX = "X-Amz-Meta-"  # type: str

    #: `S3.Client.generate_presigned_post
    #: <http://boto3.readthedocs.io/en/latest/reference/services/s3.html
    #: #S3.Client.generate_presigned_post>`_
    _POST_OBJECT_KEYS = {
        "acl": "acl",
        "cachecontrol": "Cache-Control",
        "contenttype": "Content-Type",
        "contentdisposition": "Content-Disposition",
        "contentencoding": "Content-Encoding",
        "expires": "Expires",
        "successactionredirect": "success_action_redirect",
        "redirect": "redirect",
        "successactionstatus": "success_action_status",
        "xamzmeta": "x-amz-meta-",
    }

    #: `#S3.Client.get_object
    #: <http://boto3.readthedocs.io/en/latest/reference/services/s3.html
    #: #S3.Client.get_object>`_
    _GET_OBJECT_KEYS = {
        "bucket": "Bucket",
        "ifmatch": "IfMatch",
        "ifmodifiedsince": "IfModifiedSince",
        "ifnonematch": "IfNoneMatch",
        "ifunmodifiedsince": "IfUnmodifiedSince",
        "key": "Key",
        "range": "Range",
        "responsecachecontrol": "ResponseCacheControl",
        "responsecontentdisposition": "ResponseContentDisposition",
        "responsecontentencoding": "ResponseContentEncoding",
        "responsecontentlanguage": "ResponseContentLanguage",
        "responsecontenttype": "ResponseContentType",
        "responseexpires": "ResponseExpires",
        "versionid": "VersionId",
        "ssecustomeralgorithm": "SSECustomerAlgorithm",
        "ssecustomerkey": "SSECustomerKey",
        "requestpayer": "RequestPayer",
        "partnumber": "PartNumber",
        # Extra keys to standardize across all drivers
        "cachecontrol": "ResponseCacheControl",
        "contentdisposition": "ResponseContentDisposition",
        "contentencoding": "ResponseContentEncoding",
        "contentlanguage": "ResponseContentLanguage",
        "contenttype": "ResponseContentType",
        "expires": "ResponseExpires",
    }

    #: `S3.Client.put_object
    #: <http://boto3.readthedocs.io/en/latest/reference/services/s3.html
    #: #S3.Client.put_object>`_
    _PUT_OBJECT_KEYS = {
        "acl": "ACL",
        "body": "Body",
        "bucket": "Bucket",
        "cachecontrol": "CacheControl",
        "contentdisposition": "ContentDisposition",
        "contentencoding": "ContentEncoding",
        "contentlanguage": "ContentLanguage",
        "contentlength": "ContentLength",
        "contentmd5": "ContentMD5",
        "contenttype": "ContentType",
        "expires": "Expires",
        "grantfullcontrol": "GrantFullControl",
        "grantread": "GrantRead",
        "grantreadacp": "GrantReadACP",
        "grantwriteacp": "GrantWriteACP",
        "key": "Key",
        "metadata": "Metadata",
        "serversideencryption": "ServerSideEncryption",
        "storageclass": "StorageClass",
        "websiteredirectlocation": "WebsiteRedirectLocation",
        "ssecustomeralgorithm": "SSECustomerAlgorithm",
        "ssecustomerkey": "SSECustomerKey",
        "ssekmskeyid": "SSEKMSKeyId",
        "requestpayer": "RequestPayer",
        "tagging": "Tagging",
    }

    #: `S3.Client.delete_object
    #: <http://boto3.readthedocs.io/en/latest/reference/services/s3.html
    #: #S3.Client.delete_object>`_
    _DELETE_OBJECT_KEYS = {
        "bucket": "Bucket",
        "key": "Key",
        "mfa": "MFA",
        "versionid": "VersionId",
        "requestpayer": "RequestPayer",
    }

    #: `S3.Bucket.create
    #: <http://boto3.readthedocs.io/en/latest/reference/services/s3.html
    #: #S3.Bucket.create>`_
    _POST_CONTAINER_KEYS = {
        "acl": "ACL",
        "bucket": "Bucket",
        "createbucketconfiguration": "CreateBucketConfiguration",
        "locationconstraint": "LocationConstraint",
        "grantfullcontrol": "GrantFullControl",
        "grantread": "GrantRead",
        "grantreadacp": "GrantReadACP",
        "grantwrite": "GrantWrite",
        "grantwriteacp": "GrantWriteACP",
    }
