import pytest

from cloudstorage.helpers import (
    file_checksum,
    file_content_type,
    parse_content_disposition,
    read_in_chunks,
    validate_file_or_path,
)
from tests.settings import *


def test_read_in_chunks(binary_stream):
    block_size = 32
    binary_stream_size = os.fstat(binary_stream.fileno()).st_size
    total_chunks_read = round(binary_stream_size / block_size)

    data = read_in_chunks(binary_stream, block_size=block_size)
    assert sum(1 for _ in data) == total_chunks_read


def test_file_checksum_filename(text_filename):
    file_hash = file_checksum(text_filename, hash_type='md5', block_size=32)
    assert file_hash.hexdigest() == TEXT_MD5_CHECKSUM


def test_file_checksum_stream(binary_stream):
    file_hash = file_checksum(binary_stream, hash_type='md5', block_size=32)
    assert file_hash.hexdigest() == BINARY_MD5_CHECKSUM
    assert binary_stream.tell() == 0


def test_validate_file_or_path(text_filename, binary_stream):
    assert validate_file_or_path(text_filename) == TEXT_FILENAME
    assert validate_file_or_path(binary_stream) == BINARY_FILENAME


def test_file_content_type(text_filename, binary_stream):
    assert file_content_type(text_filename) == 'text/plain'
    assert file_content_type(binary_stream) == 'image/png'


@pytest.mark.parametrize("value,expected", [
    ('', (None, {})),
    ('inline', ('inline', {})),
    ('"inline"', ('inline', {})),
    ('inline; filename="foo.html"', ('inline', {'filename': 'foo.html'})),
    ('attachment', ('attachment', {})),
    ('"attachment"', ('attachment', {})),
    ('attachment; filename="foo.html"',
     ('attachment', {'filename': 'foo.html'})),
], ids=[
    'empty',
    'inline',
    'inline quoted',
    'inline with filename',
    'attachment',
    'attachment quoted',
    'attachment with filename',
])
def test_parse_content_disposition(value, expected):
    disposition, params = parse_content_disposition(value)
    assert disposition == expected[0]
    assert params == expected[1]
