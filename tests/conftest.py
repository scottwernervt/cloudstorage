import pytest
from tempfile import mkstemp

from tests.helpers import random_container_name
from tests.settings import *

ROOT = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(scope='module')
def storage():
    pass


# noinspection PyShadowingNames
@pytest.fixture(scope='module')
def container(storage):
    container_name = random_container_name()
    container = storage.create_container(container_name)

    yield container


@pytest.fixture(scope='session')
def text_filename():
    return os.path.join(ROOT, 'data', TEXT_FILENAME)


# noinspection PyShadowingNames
@pytest.fixture(scope='function')
def text_stream(text_filename):
    with open(text_filename, 'rb') as text_stream:
        yield text_stream


# noinspection PyShadowingNames
@pytest.fixture(scope='function')
def text_blob(container, text_filename):
    text_blob = container.upload_blob(text_filename)

    yield text_blob

    if text_blob in container:
        text_blob.delete()


# noinspection PyShadowingNames
@pytest.fixture(scope='session')
def binary_filename():
    return os.path.join(ROOT, 'data', BINARY_FILENAME)


# noinspection PyShadowingNames
@pytest.fixture(scope='function')
def binary_stream(binary_filename):
    with open(binary_filename, 'rb') as binary_stream:
        yield binary_stream


# noinspection PyShadowingNames
@pytest.fixture(scope='function')
def binary_blob(container, binary_filename):
    binary_blob = container.upload_blob(binary_filename)

    yield binary_blob

    if binary_blob in container:
        binary_blob.delete()


@pytest.fixture(scope='function')
def temp_file():
    _, path = mkstemp(prefix=CONTAINER_PREFIX)
    yield path
    os.remove(path)
