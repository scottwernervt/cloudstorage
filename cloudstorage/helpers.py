"""Helper methods for Cloud Storage."""
import mimetypes
from _hashlib import HASH
from typing import Iterator, Union

import hashlib
import magic
import os

from cloudstorage.base import FileLike


def read_in_chunks(file_object: FileLike,
                   block_size: int = 4096) -> Iterator[bytes]:
    """Return a generator which yields data in chunks.

    Source: `read-file-in-chunks-ram-usage-read-strings-from-binary-file 
    <http://stackoverflow.com/questions/17056382/
    read-file-in-chunks-ram-usage-read-strings-from-binary-files>`_

    :param file_object: File object to read in chunks.
    :type file_object: file object

    :param block_size: (optional) Chunk size.
    :type block_size: int

    :yield: The next chunk in file object.
    :yield type: `bytes`
    """
    for chunk in iter(lambda: file_object.read(block_size), b''):
        yield chunk


def file_checksum(filename: Union[str, FileLike], hash_type: str = 'md5',
                  block_size: int = 4096) -> HASH:
    """Returns checksum for file.

    .. code-block:: python

        from cloudstorage.helpers import file_checksum

        picture_path = '/path/picture.png'
        file_checksum(picture_path, hash_type='sha256')
        # '03ef90ba683795018e541ddfb0ae3e958a359ee70dd4fccc7e747ee29b5df2f8'

    Source: `get-md5-hash-of-big-files-in-python <http://stackoverflow.com/
    questions/1131220/get-md5-hash-of-big-files-in-python>`_

    :param filename: File path or stream.
    :type filename: str or FileLike

    :param hash_type: Hash algorithm function name.
    :type hash_type:  str

    :param block_size: (optional) Chunk size.
    :type block_size: int

    :return: Hash of file.
    :rtype: :class:`_hashlib.HASH`

    :raise RuntimeError: If the hash algorithm is not found in :mod:`hashlib`.

    .. versionchanged:: 0.4
      Returns :class:`_hashlib.HASH` instead of `HASH.hexdigest()`.
    """
    try:
        file_hash = getattr(hashlib, hash_type)()
    except AttributeError:
        raise RuntimeError('Invalid or unsupported hash type: %s' % hash_type)

    if isinstance(filename, str):
        with open(filename, 'rb') as file_:
            for chunk in read_in_chunks(file_, block_size=block_size):
                file_hash.update(chunk)
    else:
        for chunk in read_in_chunks(filename, block_size=block_size):
            file_hash.update(chunk)

    return file_hash


def validate_file_or_path(filename: Union[str, FileLike]) -> Union[str, None]:
    """Return filename from file path or from file like object.

    Source: `rackspace/pyrax/object_storage.py <https://github.com/rackspace/
    pyrax/blob/master/pyrax/object_storage.py>`_

    :param filename: File path or file like object.
    :type filename: str or file

    :return: Filename.
    :rtype: str

    :raise FileNotFoundError: If the file path is invalid.
    """
    if isinstance(filename, str):
        # Make sure it exists
        if not os.path.exists(filename):
            raise FileNotFoundError(filename)
        name = os.path.basename(filename)
    else:
        try:
            name = os.path.basename(str(filename.name))
        except AttributeError:
            name = None

    return name


def file_content_type(filename: Union[str, FileLike]) -> Union[str, None]:
    """Guess content type for file path or file like object.

    :param filename: File path or file like object.
    :type filename: str or file 

    :return: Content type.
    :rtype: str
    """
    if isinstance(filename, str):
        if os.path.isfile(filename):
            content_type = magic.from_file(filename=filename, mime=True)
        else:
            content_type = mimetypes.guess_type(filename)[0]
    else:  # BufferedReader
        name = validate_file_or_path(filename)
        content_type = mimetypes.guess_type(name)[0]

    return content_type
