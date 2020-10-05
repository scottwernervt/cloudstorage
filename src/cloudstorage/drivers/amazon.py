"""Amazon Simple Storage Service (S3) Driver."""
import logging
from typing import Any, Dict, Iterable, List, TYPE_CHECKING  # noqa: F401
from urllib.parse import quote, urljoin

import boto3
from botocore.exceptions import ClientError, ParamValidationError, WaiterError
from inflection import camelize, underscore

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

if TYPE_CHECKING:
    from cloudstorage.structures import CaseInsensitiveDict  # noqa

__all__ = ["S3Driver"]

logger = logging.getLogger(__name__)


class S3Driver(Driver):
    """Driver for interacting with Amazon Simple Storage Service (S3).

    .. code-block:: python

        from cloudstorage.drivers.amazon import S3Driver

        storage = S3Driver(key='<my-aws-access-key-id>',
                   secret='<my-aws-secret-access-key>',
                   region='us-east-1')
        # <Driver: S3 us-east-1>

    References:

    * `Boto 3 Docs <https://boto3.amazonaws.com/v1/documentation/api/
      latest/index.html>`_
    * `Amazon S3 REST API Introduction
      <https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html>`_

    :param key: AWS Access Key ID.
    :type key: str

    :param secret: AWS Secret Access Key.
    :type secret: str

    :param region: (optional) Region to connect to. Defaults to `us-east-1`.
    :type region: str

    :param kwargs: (optional) Extra driver options.
    :type kwargs: dict
    """

    name = "S3"
    hash_type = "md5"
    url = "https://aws.amazon.com/s3/"

    def __init__(
        self, key: str, secret: str = None, region: str = "us-east-1", **kwargs: Dict
    ) -> None:
        region = region.lower()
        super().__init__(key=key, secret=secret, region=region, **kwargs)

        self._session = boto3.Session(
            aws_access_key_id=key, aws_secret_access_key=secret, region_name=region
        )

        # session required for loading regions list
        if region not in self.regions:
            raise CloudStorageError(messages.REGION_NOT_FOUND % region)

    def __iter__(self) -> Iterable[Container]:
        for bucket in self.s3.buckets.all():
            yield self._make_container(bucket)

    def __len__(self) -> int:
        buckets = [bucket for bucket in self.s3.buckets.all()]
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

    def _get_bucket(self, bucket_name: str, validate: bool = True):
        """Get a S3 bucket.

        :param bucket_name: The Bucket's name identifier.
        :type bucket_name: str

        :param validate: If True, verify that the bucket exists.
        :type validate: bool

        :return: S3 bucket resource object.
        :rtype: :class:`boto3.s3.Bucket`

        :raises NotFoundError: If the bucket does not exist.
        :raises CloudStorageError: Boto 3 client error.
        """
        bucket = self.s3.Bucket(bucket_name)

        if validate:
            try:
                response = self.s3.meta.client.head_bucket(Bucket=bucket_name)
                logger.debug("response=%s", response)
            except ClientError as err:
                error_code = int(err.response["Error"]["Code"])
                if error_code == 404:
                    raise NotFoundError(messages.CONTAINER_NOT_FOUND % bucket_name)

                raise CloudStorageError(
                    "%s: %s"
                    % (err.response["Error"]["Code"], err.response["Error"]["Message"])
                )

            try:
                bucket.wait_until_exists()
            except WaiterError as err:
                logger.error(err)

        return bucket

    def _make_blob(self, container: Container, object_summary) -> Blob:
        """Convert S3 Object Summary to Blob instance.

        :param container: The container that holds the blob.
        :type container: :class:`.Container`

        :param object_summary: S3 object summary.
        :type object_summary: :class:`boto3.s3.ObjectSummary`

        :return: A blob object.
        :rtype: :class:`.Blob`

        :raise NotFoundError: If the blob object doesn't exist.
        """
        try:
            name = object_summary.key
            #: etag wrapped in quotes
            checksum = etag = object_summary.e_tag.replace('"', "")
            size = object_summary.size

            acl = object_summary.Acl()
            meta_data = object_summary.meta.data.get("Metadata", {})
            content_disposition = object_summary.meta.data.get(
                "ContentDisposition", None
            )
            content_type = object_summary.meta.data.get("ContentType", None)
            cache_control = object_summary.meta.data.get("CacheControl", None)
            modified_at = object_summary.last_modified
            created_at = None
            expires_at = None  # TODO: FEATURE: Delete at / expires at
        except ClientError as err:
            error_code = int(err.response["Error"]["Code"])
            if error_code == 404:
                raise NotFoundError(
                    messages.BLOB_NOT_FOUND % (object_summary.key, container.name)
                )

            raise CloudStorageError(
                "%s: %s"
                % (err.response["Error"]["Code"], err.response["Error"]["Message"])
            )

        return Blob(
            name=name,
            checksum=checksum,
            etag=etag,
            size=size,
            container=container,
            driver=self,
            acl=acl,
            meta_data=meta_data,
            content_disposition=content_disposition,
            content_type=content_type,
            cache_control=cache_control,
            created_at=created_at,
            modified_at=modified_at,
            expires_at=expires_at,
        )

    def _make_container(self, bucket) -> Container:
        """Convert S3 Bucket to Container.

        :param bucket: S3 bucket object.
        :type bucket: :class:`boto3.s3.Bucket`

        :return: The container if it exists.
        :rtype: :class:`.Container`
        """
        acl = bucket.Acl()
        created_at = bucket.creation_date.astimezone(tz=None)
        return Container(
            name=bucket.name,
            driver=self,
            acl=acl,
            meta_data=None,
            created_at=created_at,
        )

    def _create_bucket_params(self, params: Dict[Any, Any]) -> Dict[Any, Any]:
        """Process extra create bucket params.

        :param params: Default create bucket parameters.
        :return: Final create bucket parameters.
        """
        # TODO: BUG: Creating S3 bucket in us-east-1
        if self.region != "us-east-1":
            params["CreateBucketConfiguration"] = {
                "LocationConstraint": self.region,
            }
        return params

    @property
    def session(self) -> boto3.session.Session:
        """Amazon Web Services session.

        :return: AWS session.
        :rtype: :class:`boto3.session.Session`
        """
        return self._session

    # noinspection PyUnresolvedReferences
    @property
    def s3(self) -> boto3.resources.base.ServiceResource:
        """S3 service resource.

        :return: The s3 resource instance.
        :rtype: :class:`boto3.resources.base.ServiceResource`
        """
        return self.session.resource(service_name="s3", region_name=self.region)

    def validate_credentials(self) -> None:
        try:
            self.session.client("sts").get_caller_identity()
        except ClientError as err:
            raise CredentialsError(str(err))

    @property
    def regions(self) -> List[str]:
        return self.session.get_available_regions("s3")

    def create_container(
        self, container_name: str, acl: str = None, meta_data: MetaData = None
    ) -> Container:
        if meta_data:
            logger.info(messages.OPTION_NOT_SUPPORTED, "meta_data")

        # Required parameters
        params = {
            "Bucket": container_name,
        }  # type: Dict[Any, Any]

        if acl:
            params["ACL"] = acl.lower()

        params = self._create_bucket_params(params)

        logger.debug("params=%s", params)

        try:
            bucket = self.s3.create_bucket(**params)
        except ParamValidationError as err:
            msg = err.kwargs.get("report", messages.CONTAINER_NAME_INVALID)
            raise CloudStorageError(msg)

        try:
            bucket.wait_until_exists()
        except WaiterError as err:
            logger.error(err)

        return self._make_container(bucket)

    def get_container(self, container_name: str) -> Container:
        bucket = self._get_bucket(container_name)
        return self._make_container(bucket)

    def patch_container(self, container: Container) -> None:
        raise NotImplementedError

    def delete_container(self, container: Container) -> None:
        bucket = self._get_bucket(container.name, validate=False)

        try:
            bucket.delete()
        except ClientError as err:
            error_code = err.response["Error"]["Code"]
            if error_code == "BucketNotEmpty":
                raise IsNotEmptyError(messages.CONTAINER_NOT_EMPTY % bucket.name)
            raise

    def container_cdn_url(self, container: Container) -> str:
        bucket = self._get_bucket(container.name, validate=False)
        endpoint_url = bucket.meta.client.meta.endpoint_url
        return "%s/%s" % (endpoint_url, container.name)

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

        extra_args = self._normalize_parameters(extra, self._PUT_OBJECT_KEYS)

        config = boto3.s3.transfer.TransferConfig(io_chunksize=chunk_size)

        # Default arguments
        extra_args.setdefault("Metadata", meta_data)
        extra_args.setdefault("StorageClass", "STANDARD")

        if acl:
            extra_args.setdefault("ACL", acl.lower())

        if cache_control:
            extra_args.setdefault("CacheControl", cache_control)

        if content_disposition:
            extra_args["ContentDisposition"] = content_disposition

        blob_name = blob_name or validate_file_or_path(filename)

        # Boto uses application/octet-stream by default
        if not content_type:
            if isinstance(filename, str):
                # TODO: QUESTION: Any advantages between filename vs blob_name?
                extra_args["ContentType"] = file_content_type(filename)
            else:
                extra_args["ContentType"] = file_content_type(blob_name)
        else:
            extra_args["ContentType"] = content_type

        logger.debug("extra_args=%s", extra_args)

        if isinstance(filename, str):
            self.s3.Bucket(container.name).upload_file(
                Filename=filename, Key=blob_name, ExtraArgs=extra_args, Config=config
            )
        else:
            self.s3.Bucket(container.name).upload_fileobj(
                Fileobj=filename, Key=blob_name, ExtraArgs=extra_args, Config=config
            )

        return self.get_blob(container, blob_name)

    def get_blob(self, container: Container, blob_name: str) -> Blob:
        object_summary = self.s3.ObjectSummary(
            bucket_name=container.name, key=blob_name
        )
        return self._make_blob(container, object_summary)

    def get_blobs(self, container: Container) -> Iterable[Blob]:
        bucket = self._get_bucket(container.name, validate=False)
        for key in bucket.objects.all():  # s3.ObjectSummary
            yield self._make_blob(container, key)

    def download_blob(self, blob: Blob, destination: FileLike) -> None:
        if isinstance(destination, str):
            self.s3.Bucket(name=blob.container.name).download_file(
                Key=blob.name, Filename=destination, ExtraArgs={}
            )
        else:
            self.s3.Bucket(name=blob.container.name).download_fileobj(
                Key=blob.name, Fileobj=destination, ExtraArgs={}
            )

    def patch_blob(self, blob: Blob) -> None:
        raise NotImplementedError

    def delete_blob(self, blob: Blob) -> None:
        # Required parameters
        params = {
            "Bucket": blob.container.name,
            "Key": blob.name,
        }

        logger.debug("params=%s", params)

        try:
            response = self.s3.meta.client.delete_object(**params)
            logger.debug("response=%s", response)
        except ClientError as err:
            error_code = int(err.response["Error"]["Code"])
            if error_code != 200 or error_code != 204:
                raise NotFoundError(
                    messages.BLOB_NOT_FOUND % (blob.name, blob.container.name)
                )
            raise

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
        meta_data = {} if meta_data is None else meta_data
        extra = {} if extra is None else extra
        extra_norm = self._normalize_parameters(extra, self._POST_OBJECT_KEYS)

        conditions = []  # type: List[Any]
        fields = {}  # type: Dict[Any, Any]

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

        return self.s3.meta.client.generate_presigned_post(
            Bucket=container.name,
            Key=blob_name,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=int(expires),
        )

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

        # Required parameters
        params["Bucket"] = blob.container.name
        params["Key"] = blob.name

        # Optional
        if content_disposition:
            params["ResponseContentDisposition"] = content_disposition

        logger.debug("params=%s", params)
        return self.s3.meta.client.generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=int(expires),
            HttpMethod=method.lower(),
        )

    _OBJECT_META_PREFIX = "x-amz-meta-"  # type: str

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
        # Extra keys to standarize across all drivers
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
