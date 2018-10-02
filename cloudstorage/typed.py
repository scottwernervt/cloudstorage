"""Custom typed annotations."""
from io import FileIO, IOBase
from typing import Any, BinaryIO, Dict, Optional, Union

FileLike = Union[IOBase, FileIO, BinaryIO]
Acl = Optional[Dict[Any, Any]]
MetaData = Optional[Dict[Any, Any]]
ContentLength = Dict[int, int]
ExtraOptions = Optional[Dict[Any, Any]]
FormPost = Dict[str, Union[str, Dict]]
