"""Helper methods for Cloud Storage."""

import hashlib
import mimetypes
import os
from io import FileIO
from typing import Iterable, Union

# noinspection PyPackageRequirements
import magic

from cloudstorage.base import FileLike


def read_in_chunks(file_object: FileIO,
                   block_size: int = 4096) -> Iterable[bytes]:
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


def file_checksum(filename: str, hash_type: str = 'md5',
                  block_size: int = 4096) -> str:
    """Returns checksum for file.
   
    .. code-block:: python
        
        from cloudstorage.helpers import file_checksum
        
        picture_path = '/path/picture.png'
        file_checksum(picture_path, hash_type='sha256')
        # '03ef90ba683795018e541ddfb0ae3e958a359ee70dd4fccc7e747ee29b5df2f8'

    Source: `get-md5-hash-of-big-files-in-python <http://stackoverflow.com/
    questions/1131220/get-md5-hash-of-big-files-in-python>`_
    
    :param filename: File path.
    :type filename: str
    
    :param hash_type: Hash algorithm function name.
    :type hash_type:  str

    :param block_size: (optional) Chunk size.
    :type block_size: int

    :return: Hex digest of file.
    :rtype: :func:`hash.hexdigest`
    
    :raise RuntimeError: If the hash algorithm is not found in :mod:`hashlib`.
    """
    try:
        m = getattr(hashlib, hash_type)()
    except AttributeError:
        raise RuntimeError('Invalid or unsupported hash type: %s' % hash_type)

    with open(filename, 'rb') as f:
        # for chunk in iter(lambda: f.read(block_size), b''):
        for chunk in read_in_chunks(f, block_size=block_size):
            m.update(chunk)

    return m.hexdigest()


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
            name = os.path.basename(filename.name)
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
