"""Local File System Driver."""
import errno
import hashlib
import json
import logging
import os
import pathlib
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List

import filelock
import itsdangerous
from inflection import underscore

from cloudstorage import Blob, Container, Driver, messages
from cloudstorage.exceptions import (
    CloudStorageError,
    CredentialsError,
    IsNotEmptyError,
    NotFoundError,
    SignatureExpiredError,
)
from cloudstorage.helpers import (
    file_checksum,
    file_content_type,
    read_in_chunks,
    validate_file_or_path,
)
from cloudstorage.typed import (
    ContentLength,
    ExtraOptions,
    FileLike,
    FormPost,
    MetaData,
)

if os.name != "nt":
    import xattr  # noqa: E402

__all__ = ["LocalDriver"]

logger = logging.getLogger(__name__)

IGNORE_FOLDERS = [".lock", ".hash", ".DS_STORE"]


@contextmanager
def lock_local_file(path: str) -> filelock.FileLock:
    """Platform dependent file lock.

    :param path: File or directory path to lock.
    :type path: str

    :yield: File lock context manager.
    :yield type: :class:`filelock.FileLock`

    :raise CloudStorageError: If lock could not be acquired.
    """
    lock = filelock.FileLock(path + ".lock")

    try:
        lock.acquire(timeout=0.1)
    except filelock.Timeout:
        raise CloudStorageError("Lock timeout")

    yield lock

    if lock.is_locked:
        lock.release()

    if os.path.exists(lock.lock_file):
        os.remove(lock.lock_file)


class LocalDriver(Driver):
    """Driver for interacting with local file-system.

    .. code-block:: python

        from cloudstorage.drivers.local import LocalDriver

        path = '/home/user/webapp/storage'
        storage = LocalDriver(key=path, secret='<my-secret>', salt='<my-salt>')
        # <Driver: LOCAL>

    Modified Source:
    `libcloud.storage.drivers.local.LocalCloudDriver <https://github.com/apache
    /libcloud/blob/trunk/libcloud/storage/drivers/local.py>`_

    :param key: Storage path directory: `/home/user/webapp/storage`.
    :type key: str

    :param secret: (optional) Secret key for pre-signed download and upload
      URLs.
    :type secret: str or None

    :param salt: (optional) Salt for namespacing download and upload
      pre-signed URLs. For more information. see `itsdangerous
      <https://palletsprojects.com/p/itsdangerous/>`_.
    :type salt: str or None

    :param kwargs: (optional) Extra driver options.
    :type kwargs: dict

    :raise NotADirectoryError: If the key storage path is invalid or does not
      exist.
    """

    name = "LOCAL"
    hash_type = "md5"
    url = ""

    def __init__(
        self, key: str, secret: str = None, salt: str = None, **kwargs: Dict
    ) -> None:
        super().__init__(key, secret, **kwargs)

        self.base_path = key
        self.salt = salt
        self.is_windows = os.name == "nt"

        try:
            if not os.path.exists(key):
                os.makedirs(key)
        except PermissionError as err:
            raise CredentialsError(str(err))

        # Check if base path is a directory and not a file
        if not os.path.isdir(self.base_path):
            raise NotADirectoryError("The base path '%s' is not a directory." % key)

    def __iter__(self) -> Iterable[Container]:
        for container_name in self._get_folders():
            yield self._make_container(container_name)

    def __len__(self) -> int:
        return len(list(self._get_folders()))

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

    def _make_serializer(self) -> itsdangerous.URLSafeTimedSerializer:
        """Returns URL Safe Timed Serializer for signing payloads.

        :return: Serializer for dumping and loading into a URL safe string.
        :rtype: :class:`itsdangerous.URLSafeTimedSerializer`
        """
        # TODO: Throw exception if secret / salt not set.
        return itsdangerous.URLSafeTimedSerializer(
            secret_key=self.secret,
            salt=self.salt,
            signer_kwargs={"key_derivation": "hmac", "digest_method": "SHA1"},
        )

    def _make_xattr(self, filename: str):
        """
        Make a xattr-like object depending on the current platform.
        :param filename:
        :return:
        """
        if self.is_windows:
            return XattrWindows(filename)
        return xattr.xattr(filename)

    def _check_path_accessible(self, path: str) -> bool:
        """
        Check if the path is accessible. In windows custom files are used to simulate
        file attributes, these must not be accessed.

        :param filename:
        :return:
        """
        if self.is_windows:
            p = pathlib.Path(path)
            if p.name.startswith(".") and p.name.endswith(".xattr"):
                return False
        return True

    def _get_folders(self) -> Iterable[str]:
        """Iterate over first level folders found in base path.

        :yield: Iterable[str]
        :yield type: str
        """
        for container_name in os.listdir(self.base_path):
            full_path = os.path.join(self.base_path, container_name)
            if not self._check_path_accessible(full_path):
                continue
            if not os.path.isdir(full_path):
                continue

            yield container_name

    def _get_folder_path(self, container: Container, validate: bool = True) -> str:
        """Get the container's full folder path.

        :param container: A container instance.
        :type container: :class:`.Container`

        :param validate: If True, verify that folder exists.
        :type validate: bool

        :return: Full folder path to the container.
        :rtype: str

        :raises NotFoundError: If the container doesn't exist.
        """
        full_path = os.path.join(self.base_path, container.name)
        if validate and not self._check_path_accessible(full_path):
            raise NotFoundError(messages.CONTAINER_NOT_FOUND % container.name)
        if validate and not os.path.isdir(full_path):
            raise NotFoundError(messages.CONTAINER_NOT_FOUND % container.name)

        return full_path

    def _set_file_attributes(self, filename: str, attributes: Dict) -> None:
        """Set extended filesystem attributes to a file.

        Metadata is set to `user.metadata.<attr-name>` and remaining attributes
        are set to `user.<attr-name>`.

        References:

        * `xattr <https://github.com/xattr/xattr>`_

        :param filename: Filename path.
        :type filename: str

        :param attributes: Dictionary of `meta_data`, `content_<name>`, etc.
        :type attributes: dict

        :return: NoneType
        :rtype: None

        :raises CloudStorageError: If the local file system does not support
          extended filesystem attributes.
        """
        xattrs = self._make_xattr(filename)

        for key, value in attributes.items():
            if not value:
                continue

            try:
                if key == "meta_data":
                    for meta_key, meta_value in value.items():
                        # user.metadata.name
                        attr_name = (
                            self._OBJECT_META_PREFIX + "metadata." + meta_key
                        )  # noqa: E126
                        xattrs[attr_name] = meta_value.encode("utf-8")
                else:
                    # user.name
                    attr_name = self._OBJECT_META_PREFIX + key
                    xattrs[attr_name] = value.encode("utf-8")
            except OSError:
                logger.warning(messages.LOCAL_NO_ATTRIBUTES)

    def _get_file_path(self, blob: Blob) -> str:
        """Get the blob's full folder path.

        :param blob: A blob instance.
        :type blob: :class:`.Blob`

        :return: Full folder path to the blob.
        :rtype: str
        """
        return os.path.join(self.base_path, blob.container.name, blob.name)

    @staticmethod
    def _make_path(path: str, ignore_existing: bool = True) -> None:
        """Create a folder.

        :param path: Folder path to create.
        :type path: str

        :param ignore_existing: If True, ignore existing folder.
        :type ignore_existing: bool

        :return: NoneType
        :rtype: None

        :raises CloudStorageError: If folder exists and  `ignore_existing` is
          False.
        """
        try:
            os.makedirs(path)
        except OSError:
            logger.debug(messages.CONTAINER_EXISTS, path)
            exp = sys.exc_info()[1]
            if exp.errno == errno.EEXIST and not ignore_existing:
                raise CloudStorageError(exp.strerror)

    def _make_container(self, folder_name: str) -> Container:
        """Convert a folder name to a Cloud Storage Container.

        :param folder_name: The folder name to convert.
        :type folder_name: str

        :return: A container instance.
        :rtype: :class:`.Container`

        :raises FileNotFoundError: If container does not exist.
        """
        full_path = os.path.join(self.base_path, folder_name)
        if not self._check_path_accessible(full_path):
            raise NotFoundError(messages.CONTAINER_NOT_FOUND % folder_name)

        try:
            stat = os.stat(full_path)
        except FileNotFoundError:
            raise NotFoundError(messages.CONTAINER_NOT_FOUND % folder_name)

        created_at = datetime.fromtimestamp(stat.st_ctime, timezone.utc)

        return Container(
            name=folder_name, driver=self, meta_data=None, created_at=created_at
        )

    def _make_blob(self, container: Container, object_name: str) -> Blob:
        """Convert local file name to a Cloud Storage Blob.

        :param container: Container instance.
        :type container: :class:`.Container`

        :param object_name: Filename.
        :type object_name: str

        :return: Blob instance.
        :rtype: :class:`.Blob`
        """
        full_path = os.path.join(self.base_path, container.name, object_name)
        if not self._check_path_accessible(full_path):
            raise NotFoundError(messages.BLOB_NOT_FOUND % (object_name, container.name))

        object_path = pathlib.Path(full_path)

        try:
            stat = os.stat(str(object_path))
        except FileNotFoundError:
            raise NotFoundError(messages.BLOB_NOT_FOUND % (object_name, container.name))

        meta_data = {}
        content_type = None
        content_disposition = None
        cache_control = None

        try:
            attributes = self._make_xattr(full_path)

            for attr_key, attr_value in attributes.items():
                value_str = None

                try:
                    value_str = attr_value.decode("utf-8")
                except UnicodeDecodeError:
                    pass

                if attr_key.startswith(self._OBJECT_META_PREFIX + "metadata"):
                    meta_key = attr_key.split(".")[-1]
                    meta_data[meta_key] = value_str
                elif attr_key.endswith("content_type"):
                    content_type = value_str
                elif attr_key.endswith("content_disposition"):
                    content_disposition = value_str
                elif attr_key.endswith("cache_control"):
                    cache_control = value_str
                else:
                    logger.warning("Unknown file attribute '%s'", attr_key)
        except OSError:
            logger.warning(messages.LOCAL_NO_ATTRIBUTES)

        # TODO: QUESTION: Option to disable checksum for large files?
        # TODO: QUESTION: Save a .hash file for each file?
        file_hash = file_checksum(full_path, hash_type=self.hash_type)
        checksum = file_hash.hexdigest()

        etag = hashlib.sha1(full_path.encode("utf-8")).hexdigest()
        created_at = datetime.fromtimestamp(stat.st_ctime, timezone.utc)
        modified_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc)

        return Blob(
            name=object_name,
            checksum=checksum,
            etag=etag,
            size=stat.st_size,
            container=container,
            driver=self,
            acl=None,
            meta_data=meta_data,
            content_disposition=content_disposition,
            content_type=content_type,
            cache_control=cache_control,
            created_at=created_at,
            modified_at=modified_at,
        )

    def validate_credentials(self) -> None:
        if not os.access(self.base_path, os.W_OK):
            raise CredentialsError(
                "[Errno 13] Permission denied: '{}'".format(self.base_path)
            )

    @property
    def regions(self) -> List[str]:
        return []

    def create_container(
        self, container_name: str, acl: str = None, meta_data: MetaData = None
    ) -> Container:
        if acl:
            logger.info(messages.OPTION_NOT_SUPPORTED, "acl")

        if meta_data:
            logger.info(messages.OPTION_NOT_SUPPORTED, "meta_data")

        full_path = os.path.join(self.base_path, container_name)
        if not self._check_path_accessible(full_path):
            raise CloudStorageError(messages.CONTAINER_NAME_INVALID)

        self._make_path(full_path, ignore_existing=True)
        try:
            with lock_local_file(full_path):
                self._make_path(full_path, ignore_existing=True)
        except FileNotFoundError:
            raise CloudStorageError(messages.CONTAINER_NAME_INVALID)

        return self._make_container(container_name)

    def get_container(self, container_name: str) -> Container:
        return self._make_container(container_name)

    def patch_container(self, container: Container) -> None:
        raise NotImplementedError

    def delete_container(self, container: Container) -> None:
        for _ in self.get_blobs(container):
            raise IsNotEmptyError(messages.CONTAINER_NOT_EMPTY % container.name)

        path = self._get_folder_path(container, validate=True)

        with lock_local_file(path):
            try:
                shutil.rmtree(path)
            except shutil.Error as err:
                raise CloudStorageError(err.strerror)

    def container_cdn_url(self, container: Container) -> str:
        return self._get_folder_path(container)

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

        attributes = self._normalize_parameters(extra, self._PUT_OBJECT_KEYS)
        attributes.setdefault("meta_data", meta_data)
        attributes.setdefault("content_disposition", content_disposition)
        attributes.setdefault("cache_control", cache_control)

        path = self._get_folder_path(container, validate=True)

        blob_name = blob_name or validate_file_or_path(filename)
        blob_path = os.path.join(path, blob_name)

        base_path = os.path.dirname(blob_path)
        self._make_path(base_path)

        tmp_blob_path = f'{blob_path}.tmp'

        with lock_local_file(blob_path):
            if isinstance(filename, str):
                shutil.copy(filename, tmp_blob_path)
            else:
                with open(tmp_blob_path, "wb") as blob_file:
                    for data in filename:
                        blob_file.write(data)
                    os.fsync(blob_file.fileno())

        os.rename(tmp_blob_path, blob_path)
        # Disable execute mode on file
        os.chmod(blob_path, int("664", 8))

        if not content_type:
            attributes["content_type"] = file_content_type(blob_path)
        else:
            attributes["content_type"] = content_type

        # Set meta data and other attributes
        self._set_file_attributes(blob_path, attributes)

        return self.get_blob(container, blob_name)

    def get_blob(self, container: Container, blob_name: str) -> Blob:
        return self._make_blob(container, blob_name)

    def get_blobs(self, container: Container) -> Iterable[Blob]:
        container_path = self._get_folder_path(container, validate=True)

        for folder, sub_folders, files in os.walk(container_path, topdown=True):
            # Remove unwanted sub-folders
            for sub_folder in IGNORE_FOLDERS:
                if sub_folder in sub_folders:
                    sub_folders.remove(sub_folder)

            for name in files:
                full_path = os.path.join(folder, name)
                if not self._check_path_accessible(full_path):
                    continue
                object_name = pathlib.Path(full_path).name
                yield self._make_blob(container, object_name)

    def download_blob(self, blob: Blob, destination: FileLike) -> None:
        blob_path = self._get_file_path(blob)

        if isinstance(destination, str):
            base_name = os.path.basename(destination)
            if not base_name and not os.path.exists(destination):
                raise CloudStorageError("Path %s does not exist." % destination)

            if not base_name:
                file_path = os.path.join(destination, blob.name)
            else:
                file_path = destination

            shutil.copy(blob_path, file_path)
        else:
            with open(blob_path, "rb") as blob_file:
                for data in read_in_chunks(blob_file):
                    destination.write(data)

    def patch_blob(self, blob: Blob) -> None:
        raise NotImplementedError

    def delete_blob(self, blob: Blob) -> None:
        path = self._get_file_path(blob)

        with lock_local_file(path):
            try:
                os.unlink(path)
            except OSError as err:
                logger.exception(err)

        if self.is_windows:
            xattr = XattrWindows(path)
            xattr.remove_attributes()

    def blob_cdn_url(self, blob: Blob) -> str:
        return os.path.join(self.base_path, blob.container.name, blob.name)

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

        expiration = datetime.utcnow() + timedelta(seconds=expires)
        expires_at = expiration.timestamp()

        fields = {
            "blob_name": blob_name,
            "container": container.name,
            "expires": expires_at,
        }

        payload = {
            "acl": acl,
            "meta_data": meta_data,
            "content_disposition": content_disposition,
            "content_length": content_length,
            "content_type": content_type,
            "cache_control": cache_control,
            "max_age": int(expires),
        }
        payload.update(**fields)
        payload.update(**extra)

        serializer = self._make_serializer()
        token = serializer.dumps(payload)
        fields["signature"] = token

        return {"url": "", "fields": fields}

    def generate_blob_download_url(
        self,
        blob: Blob,
        expires: int = 3600,
        method: str = "GET",
        content_disposition: str = None,
        extra: ExtraOptions = None,
    ) -> str:
        extra = extra if extra is not None else {}
        serializer = self._make_serializer()

        expiration = datetime.utcnow() + timedelta(seconds=expires)
        expires_at = expiration.timestamp()

        payload = {
            "max_age": int(expires),
            "expires": expires_at,
            "blob_name": blob.name,
            "container": blob.container.name,
            "method": method,
            "content_disposition": content_disposition,
        }
        payload.update(**extra)

        signature = serializer.dumps(payload)
        return str(signature)

    def validate_signature(self, signature):
        """Validate signed signature and return payload if valid.

        :param signature: Signature.
        :type signature: str

        :return: Deserialized signature payload.
        :rtype: dict

        :raises SignatureExpiredError: If the signature has expired.
        """
        serializer = self._make_serializer()
        payload = serializer.loads(signature, max_age=None)
        max_age = payload.get("max_age", 0)

        # https://github.com/pallets/itsdangerous/issues/43
        try:
            return serializer.loads(signature, max_age=max_age)
        except itsdangerous.SignatureExpired:
            raise SignatureExpiredError

    _OBJECT_META_PREFIX = "user."

    _PUT_OBJECT_KEYS = {
        "metadata": "meta_data",
    }


class XattrWindows:
    """
    Simulate xattr on windows.

    A file named ".<filename>.xattr" will be created on the same directory as the
    source file.
    """

    def __init__(self, filename) -> None:
        self.filename = filename
        p = pathlib.Path(filename)
        self.xattr_filename = os.path.join(p.parent, ".{}.xattr".format(p.name))

    def __setitem__(self, key, value) -> None:
        """
        Write an attribute to the json file.
        """
        data = self._load()
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        data[key] = value
        with open(self.xattr_filename, "w") as outfile:
            json.dump(data, outfile)

    def items(self):
        """
        Return a list of the attributes.
        :return:
        """
        # xattr returns items as bytes, must convert all str first
        items = self._load()
        ret = {}
        for itemname, itemvalue in items.items():
            if isinstance(itemvalue, str):
                ret[itemname] = itemvalue.encode("utf-8")
            else:
                ret[itemname] = itemvalue
        return ret.items()

    def _load(self) -> Dict:
        """
        Load json file if it exists
        :return:
        """
        if os.path.exists(self.xattr_filename):
            with open(self.xattr_filename) as json_file:
                return json.load(json_file)
        return {}

    def remove_attributes(self):
        if os.path.exists(self.xattr_filename):
            with lock_local_file(self.xattr_filename):
                try:
                    os.unlink(self.xattr_filename)
                except OSError as err:
                    logger.exception(err)
