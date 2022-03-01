import logging
from typing import Iterable, Union

from owncloud import Client, FileInfo, HTTPResponseError

from cloudstorage import Container, Driver, messages
from cloudstorage.exceptions import (
    NotFoundError,
)


logger = logging.getLogger(__name__)


class OwnCloudDriver(Driver):

    name = "OWNCLOUD"
    hash_type = "md5"  # TODO: What is this?
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
        super().__init__(key=user, secret=password, region=endpoint)

    def __iter__(self) -> Iterable[Container]:
        for info in self._list(""):
            if info.is_dir():
                yield self._make_container(info)

    def __len__(self) -> int:
        # More space efficient than list(...).
        return sum(1 for _ in self)

    def _list(self, dir_name) -> Iterable[FileInfo]:
        try:
            return self._client.list(dir_name)
        except HTTPResponseError as e:
            if e.status_code == 404:
                raise NotFoundError(messages.CONTAINER_NOT_FOUND % dir_name)

    def _get_info(self, name: str) -> FileInfo:
        try:
            return self._client.file_info(name)
        except HTTPResponseError as e:
            if e.status_code == 404:
                raise NotFoundError("'%s' not found." % name)
            raise e

    def _get_dir_info(self, dir_name: str) -> FileInfo:
        try:
            info = self._get_info(dir_name)
            if not info.is_dir():
                raise NotFoundError(messages.CONTAINER_NOT_FOUND % dir_name)
            return info
        except NotFoundError:
            raise NotFoundError(messages.CONTAINER_NOT_FOUND % dir_name)

    def _make_container(self, dir: Union[str, FileInfo]) -> Container:
        if not isinstance(dir, FileInfo):
            info = self._get_dir_info(dir)
        return Container(
            name=info.get_path(), driver=self,
        )
