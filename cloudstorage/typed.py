"""Custom typed annotations."""
from typing import Any, AnyStr, Dict, IO, Optional, Union

FileLike = Union[IO[AnyStr], str]
Acl = Optional[Dict[Any, Any]]
MetaData = Optional[Dict[Any, Any]]
ExtraOptions = Optional[Dict[Any, Any]]
ContentLength = Dict[int, int]
FormPost = Union[str, Dict[Any, Any]]
