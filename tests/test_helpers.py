from cloudstorage.helpers import file_checksum
from cloudstorage.helpers import file_content_type
from cloudstorage.helpers import read_in_chunks
from cloudstorage.helpers import validate_file_or_path
from tests.settings import *


def test_read_in_chunks(binary_stream):
    block_size = 32
    binary_stream_size = os.fstat(binary_stream.fileno()).st_size
    total_chunks_read = round(binary_stream_size / block_size)

    data = read_in_chunks(binary_stream, block_size=block_size)
    assert sum(1 for _ in data) == total_chunks_read


def test_file_checksum(text_filename):
    file_hash = file_checksum(text_filename, hash_type='md5', block_size=32)
    assert file_hash.hexdigest() == TEXT_MD5_CHECKSUM


def test_validate_file_or_path(text_filename, binary_stream):
    assert validate_file_or_path(text_filename) == TEXT_FILENAME
    assert validate_file_or_path(binary_stream) == BINARY_FILENAME


def test_file_content_type(text_filename, binary_stream):
    assert file_content_type(text_filename) == 'text/plain'
    assert file_content_type(binary_stream) == 'image/png'
