"""Custom typed annotations."""
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, TYPE_CHECKING, TextIO, Union, Type

if TYPE_CHECKING:
    from cloudstorage.structures import CaseInsensitiveDict  # noqa
    from cloudstorage.drivers.amazon import S3Driver  # noqa
    from cloudstorage.drivers.google import GoogleStorageDriver  # noqa
    from cloudstorage.drivers.local import LocalDriver  # noqa
    from cloudstorage.drivers.microsoft import AzureStorageDriver  # noqa
    from cloudstorage.drivers.minio import MinioDriver  # noqa
    from cloudstorage.drivers.rackspace import CloudFilesDriver  # noqa


Drivers = Union[
    Type["S3Driver"],
    Type["GoogleStorageDriver"],
    Type["LocalDriver"],
    Type["AzureStorageDriver"],
    Type["MinioDriver"],
    Type["CloudFilesDriver"],
]
FileLike = Union[BinaryIO, TextIO, str, Path]
Acl = Optional[Dict[Any, Any]]
MetaData = Optional["CaseInsensitiveDict"]
ExtraOptions = Optional[Dict[Any, Any]]
ContentLength = Dict[int, int]
FormPost = Union[str, Dict[Any, Any]]
