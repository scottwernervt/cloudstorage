"""Helper methods for Cloud Storage."""
import hashlib
import mimetypes
import os
from _hashlib import HASH
from typing import BinaryIO, Dict, Generator, Optional, TextIO, Tuple, Union

import magic  # type: ignore

from cloudstorage.typed import FileLike


def read_in_chunks(
    file_object: Union[BinaryIO, TextIO], block_size: int = 4096
) -> Generator[Union[bytes, str], None, None]:
    """Return a generator which yields data in chunks.

    Source: `read-file-in-chunks-ram-usage-read-strings-from-binary-file
    <https://stackoverflow.com/questions/17056382/
    read-file-in-chunks-ram-usage-read-strings-from-binary-files>`_

    :param file_object: File object to read in chunks.
    :type file_object: file object

    :param block_size: (optional) Chunk size.
    :type block_size: int

    :yield: The next chunk in file object.
    :yield type: `bytes`
    """
    for chunk in iter(lambda: file_object.read(block_size), b""):
        yield chunk


def file_checksum(
    filename: FileLike, hash_type: str = "md5", block_size: int = 4096
) -> HASH:
    """Returns checksum for file.

    .. code-block:: python

        from cloudstorage.helpers import file_checksum

        picture_path = '/path/picture.png'
        file_checksum(picture_path, hash_type='sha256')
        # '03ef90ba683795018e541ddfb0ae3e958a359ee70dd4fccc7e747ee29b5df2f8'

    Source: `get-md5-hash-of-big-files-in-python <https://stackoverflow.com/
    questions/1131220/get-md5-hash-of-big-files-in-python>`_

    :param filename: File path or stream.
    :type filename: str or FileLike

    :param hash_type: Hash algorithm function name.
    :type hash_type:  str

    :param block_size: (optional) Chunk size.
    :type block_size: int

    :return: Hash of file.

    :raise RuntimeError: If the hash algorithm is not found in :mod:`hashlib`.

    .. versionchanged:: 0.4
      Returns :class:`_hashlib.HASH` instead of `HASH.hexdigest()`.
    """
    try:
        file_hash = getattr(hashlib, hash_type)()
    except AttributeError:
        raise RuntimeError("Invalid or unsupported hash type: %s" % hash_type)

    if isinstance(filename, str):
        with open(filename, "rb") as file_:
            for chunk in read_in_chunks(file_, block_size=block_size):
                file_hash.update(chunk)
    else:
        for chunk in read_in_chunks(filename, block_size=block_size):
            file_hash.update(chunk)
        # rewind the stream so it can be re-read later
        if filename.seekable():
            filename.seek(0)

    return file_hash


def validate_file_or_path(filename: FileLike) -> Optional[str]:
    """Return filename from file path or from file like object.

    Source: `rackspace/pyrax/object_storage.py <https://github.com/pycontribs/
    pyrax/blob/master/pyrax/object_storage.py>`_

    :param filename: File path or file like object.
    :type filename: str or file

    :return: Filename.
    :rtype: str or None

    :raise FileNotFoundError: If the file path is invalid.
    """
    name = None

    if isinstance(filename, str):
        if not os.path.exists(filename):
            raise FileNotFoundError(filename)

        name = os.path.basename(filename)
    else:
        try:
            name = os.path.basename(str(filename.name))
        except AttributeError:
            pass

    return name


def file_content_type(filename: FileLike) -> Optional[str]:
    """Guess content type for file path or file like object.

    :param filename: File path or file like object.
    :type filename: str or file

    :return: Content type.
    :rtype: str or None
    """
    content_type = None

    if isinstance(filename, str):
        if os.path.isfile(filename):
            content_type = magic.from_file(filename=filename, mime=True)
        else:
            content_type = mimetypes.guess_type(filename)[0]
    else:  # BufferedReader
        name = validate_file_or_path(filename)
        if name:
            content_type = mimetypes.guess_type(name)[0]

    return content_type


def parse_content_disposition(data: str) -> Tuple[Optional[str], Dict]:
    """Parse Content-Disposition header.

    Example: ::

        >>> parse_content_disposition('inline')
        ('inline', {})

        >>> parse_content_disposition('attachment; filename="foo.html"')
        ('attachment', {'filename': 'foo.html'})

    Source: `pyrates/multifruits <https://github.com/pyrates/multifruits>`_

    :param data: Content-Disposition header value.
    :type data: str

    :return: Disposition type and fields.
    :rtype: tuple
    """
    dtype = None
    params = {}
    length = len(data)
    start = 0
    end = 0
    i = 0
    quoted = False
    previous = ""
    field = None

    while i < length:
        c = data[i]
        if not quoted and c == ";":
            if dtype is None:
                dtype = data[start:end]
            elif field is not None:
                params[field.lower()] = data[start:end].replace("\\", "")
                field = None
            i += 1
            start = end = i
        elif c == '"':
            i += 1
            if not previous or previous != "\\":
                if not quoted:
                    start = i
                quoted = not quoted
            else:
                end = i
        elif c == "=":
            field = data[start:end]
            i += 1
            start = end = i
        elif c == " ":
            i += 1
            if not quoted and start == end:  # Leading spaces.
                start = end = i
        else:
            i += 1
            end = i

        previous = c

    if i:
        if dtype is None:
            dtype = data[start:end].lower()
        elif field is not None:
            params[field.lower()] = data[start:end].replace("\\", "")

    return dtype, params
