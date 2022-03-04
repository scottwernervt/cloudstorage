import logging
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Union

from owncloud import Client, FileInfo, HTTPResponseError

from cloudstorage import Blob, Container, Driver, messages
from cloudstorage.exceptions import (
    CloudStorageError,
    CredentialsError,
    IsNotEmptyError,
    NotFoundError,
)
from cloudstorage.helpers import (
    read_in_chunks,
)
from cloudstorage.typed import (
    ContentLength,
    ExtraOptions,
    FileLike,
    FormPost,
    MetaData,
)


logger = logging.getLogger(__name__)


class OwnCloudDriver(Driver):

    name = "OWNCLOUD"
    url = "https://owncloud.com/"

    def __init__(
        self,
        endpoint: str,
        user: str = None,
        password: str = None,
        **kwargs,
    ):
        if user is None:
            if password is None:
                # Public link with no credentials.
                self._client = Client.from_public_link(endpoint)
            else:
                # Password-protected public link.
                self._client = Client.from_public_link(endpoint, password)
        else:
            # Normal login with a password.
            if password is None:
                raise TypeError("password required when username is given")
            self._client = Client(endpoint)
            self._client.login(user, password)
        self._endpoint = endpoint
        super().__init__(key=user, secret=password, region=endpoint)

    def __iter__(self) -> Iterable[Container]:
        for info in self._list("/"):
            if info.is_dir():
                yield self._make_container(info)

    def __len__(self) -> int:
        # More space efficient than list(...).
        return sum(1 for _ in self)

    def _list(
        self,
        dir_name: str,
        depth: Union[int, Literal["infinity"]] = 1,
    ) -> Iterable[FileInfo]:
        logger.debug("listing '%s' (depth %s)", dir_name, depth)
        try:
            return self._client.list(dir_name, depth)
        except HTTPResponseError as e:
            if e.status_code == 404:
                raise NotFoundError(messages.CONTAINER_NOT_FOUND % dir_name) \
                    from None

    def _get_info(self, name: str) -> FileInfo:
        try:
            logger.debug("reading info for %s", name)
            info = self._client.file_info(name)
            if info is None:
                # According to the docs, None will be returned, but in practice
                # it rather seems to be 404 errors. Anyway, we support both.
                raise NotFoundError("'%s' not found." % name)
            return info
        except HTTPResponseError as e:
            if e.status_code == 404:
                raise NotFoundError("'%s' not found." % name) from None
            raise

    def _get_dir_info(self, dir_path: str) -> FileInfo:
        try:
            info = self._get_info(dir_path)
            if not info.is_dir():  # We're explicitly looking for dirs.
                raise NotFoundError(messages.CONTAINER_NOT_FOUND % dir_path)
            return info
        except NotFoundError:
            raise NotFoundError(messages.CONTAINER_NOT_FOUND % dir_path) \
                from None

    def _get_file_info(self, dir_path: str, file_path: str) -> FileInfo:
        try:
            info = self._get_info("%s/%s" % (dir_path, file_path))
            if info.is_dir():  # We're explicitly _not_ looking for dirs.
                raise NotFoundError(
                    messages.BLOB_NOT_FOUND % (file_path, dir_path)
                )
            return info
        except NotFoundError:
            raise NotFoundError(
                messages.BLOB_NOT_FOUND % (file_path, dir_path)
            ) from None

    def _make_blob(
        self,
        container: Container,
        blob: Union[str, FileInfo],
    ) -> Blob:
        # blob can either be a string (we have to look up the file info) or a
        # FileInfo (because it has been retrieved from a listing already) for
        # which we need to compute the name.
        blob_name = blob if isinstance(blob, str) else blob.path
        # blob_name is assumed to be relative to container. If it starts with a
        # slash, however, we instead make sure that it's inside of the
        # container and convert its name to a relative one.
        if blob_name.startswith("/"):
            if not blob_name.startswith("/" + container.name + "/"):
                raise NotFoundError(
                    messages.BLOB_NOT_FOUND % (blob_name, container.name)
                )
            blob_name = blob_name[len(container.name)+2:]
        info = self._get_file_info(container.name, blob_name) \
            if isinstance(blob, str) else blob

        if info.is_dir():  # A dir does not count as a blob.
            raise NotFoundError(
                messages.BLOB_NOT_FOUND % (blob_name, container.name)
            )

        return Blob(
            name=blob_name,
            # ownCloud does have server-side checksumming, but it currently
            # cannot be accessed using their library:
            # <https://github.com/owncloud/pyocclient/issues/234#issuecomment-1057215886>
            checksum="",
            etag=info.get_etag(),
            size=info.get_size(),
            container=container,
            driver=self,
            acl=None,
            meta_data=info.attributes,  # TODO: Does this make sense?
            content_disposition=None,
            content_type=info.get_content_type(),
            cache_control=None,
            created_at=None,
            modified_at=info.get_last_modified(),
            expires_at=None,
        )

    def _make_container(self, dir: Union[str, FileInfo]) -> Container:
        if not isinstance(dir, FileInfo):
            dir = self._get_dir_info(dir)

        name = dir.get_path().lstrip("/")
        if not dir.is_dir():  # A file does not count as a container.
            raise NotFoundError(messages.CONTAINER_NOT_FOUND % name)

        return Container(
            name=name, driver=self,
        )

    def _mkdirs(self, path: str, check_first: bool = True) -> None:
        logger.info("recursively creating directories: %s", path)
        if check_first:
            # First, check if the complete path already exists.
            try:
                info: FileInfo = self._get_dir_info(path)
                if info.is_dir():
                    logger.debug("'%s' is already a directory", path)
                    return  # Nothing to do.
            except:
                # Okay, we'll have to create it.
                pass

        here = []
        created = False
        for seg in path.strip("/").split("/"):
            here.append(seg)
            joined = "/".join(here)
            if created:
                # We created the previous segment, so we probably can skip
                # checking whether the current one exists (it shouldn't)
                # and instead go straight to creating the new segment.
                logger.debug("blindly creating: %s", joined)
                self._client.mkdir(joined)
                continue
            # Else, we should check whether the segment exists and what it is.
            try:
                info: FileInfo = self._get_info(joined)
                if not info.is_dir():
                    # A non-directory exists here already, we can't continue.
                    raise CloudStorageError("'%s' is not a container" % here)
                # When we're here, the segment exists and is a dir. Continue.
            except NotFoundError:
                # This segment doesn't exist yet, create it.
                logger.debug("creating: %s", joined)
                self._client.mkdir(joined)
                created = True

    @staticmethod
    def _normalize_parameters(
        params: Dict[str, str], normalizers: Dict[str, str],
    ) -> Dict[str, str]:
        raise NotImplementedError()

    def blob_cdn_url(self, blob: Blob) -> str:
        logger.warn(messages.FEATURE_NOT_SUPPORTED, "blob_cdn_url")
        raise NotImplementedError()

    def container_cdn_url(self, container: Container) -> str:
        logger.warn(messages.FEATURE_NOT_SUPPORTED, "container_cdn_url")
        raise NotImplementedError()

    def create_container(
        self, container_name: str, acl: str = None, meta_data: MetaData = None,
    ) -> Container:
        if acl is not None:
            logger.info(messages.OPTION_NOT_SUPPORTED, "acl")
        if meta_data is not None:
            logger.info(messages.OPTION_NOT_SUPPORTED, "meta_data")

        self._mkdirs(container_name)

        return self._make_container(container_name)

    def delete_blob(self, blob: Blob) -> None:
        # TODO: Error handling.
        logger.info("deleting blob: %s", blob)
        self._client.delete(blob.path)

    def delete_container(self, container: Container) -> None:
        # TODO: Error handling.
        logger.info("deleting container: %s", container)
        # Note that ownCloud will delete directories that still have files
        # and/or folders in them without complaining, but since the
        # cloudstorage docs say that all blobs in a container must have been
        # deleted prior to deleting the container, we explicitly check for
        # that. We do ignore empty subdirectories, however. All of this
        # somewhat resembles "normal" blob storage providers though.
        for _ in container:
            raise IsNotEmptyError(
                messages.CONTAINER_NOT_EMPTY % container.name
            )
        self._client.delete(container.name)

    def disable_container_cdn(self, container: Container) -> bool:
        logger.warn(messages.FEATURE_NOT_SUPPORTED, "disable_container_cdn")
        return False

    def download_blob(self, blob: Blob, destination: FileLike) -> None:
        # TODO: Error handling.
        if isinstance(destination, Path):
            destination = str(destination)
        content = self._client.get_file_contents(blob.path)
        if isinstance(destination, str):
            with open(destination, "wb") as file:
                file.write(content)
        else:
            destination.write(content)

    def enable_container_cdn(self, container: Container) -> bool:
        logger.warn(messages.FEATURE_NOT_SUPPORTED, "enable_container_cdn")
        return False

    def generate_blob_download_url(
        self,
        blob: Blob,
        expires: int = 3600,
        method: str = "GET",
        content_disposition: str = None,
        extra: ExtraOptions = None,
    ) -> str:
        logger.warn(
            messages.FEATURE_NOT_SUPPORTED, "generate_blob_download_url"
        )
        raise NotImplementedError()

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
        logger.warn(
            messages.FEATURE_NOT_SUPPORTED, "generate_blob_download_url"
        )
        raise NotImplementedError()

    def get_blob(self, container: Container, blob_name: str) -> Blob:
        return self._make_blob(container, blob_name)

    def get_blobs(self, container: Container) -> Iterable[Blob]:
        for item in self._list(container.name, "infinity"):
            if not item.is_dir():
                # _make_blob will also convert item.path to a relative one.
                yield self._make_blob(container, item)

    def get_container(self, container_name: str) -> Container:
        return self._make_container(container_name)

    def patch_blob(self, blob: Blob) -> None:
        # TODO: Implement for mime type, maybe more attributes?
        raise NotImplementedError()

    def patch_container(self, container: Container) -> None:
        # TODO: Not sure which attributes make sense here.
        raise NotImplementedError()

    def regions(self) -> List[str]:
        return [self._endpoint]

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
        chunk_size=1024,
        extra: ExtraOptions = None,
    ) -> Blob:
        # TODO: Warnings for unsupported options.
        blob_path = "%s/%s" % (container.name, blob_name)
        logger.info("will upload a %s to '%s'", type(filename), blob_path)
        if isinstance(filename, Path):
            filename = str(filename)
        # Unintuitively, `filename` can also be a file-like object.
        method = self._client.put_file if isinstance(filename, str) \
            else self._client.put_file_contents

        # Optimistic upload attempt.
        try:
            method(blob_path, filename)
        except HTTPResponseError as e:
            logger.debug("optimistic upload failed (%d)", e.status_code)
            if e.status_code == 409:
                # Usually means "a parent directory does not exist".
                self._mkdirs(
                    "/".join(blob_path.split("/")[:-1]),
                    check_first=False,  # We already know it doesn't exist.
                )
                # Try again.
                method(blob_path, filename)

        logger.info("upload of '%s' succeeded", blob_path)
        return self._make_blob(container, blob_name)

    def validate_credentials(self) -> None:
        # TODO: Check whether this works for all login variants.
        try:
            for _ in self._list(""):
                break
        except HTTPResponseError as e:
            if e.status_code == 401:
                raise CredentialsError("unauthorized")
