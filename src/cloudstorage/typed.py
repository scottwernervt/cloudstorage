"""Custom typed annotations."""
from typing import Any, BinaryIO, Dict, Optional, TYPE_CHECKING, TextIO, Union

if TYPE_CHECKING:
    from cloudstorage.structures import CaseInsensitiveDict # noqa

FileLike = Union[BinaryIO, TextIO, str]
Acl = Optional[Dict[Any, Any]]
MetaData = Optional["CaseInsensitiveDict"]
ExtraOptions = Optional[Dict[Any, Any]]
ContentLength = Dict[int, int]
FormPost = Union[str, Dict[Any, Any]]
