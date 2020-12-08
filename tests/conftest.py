import os
import io
from tempfile import mkstemp

import pytest

from tests import settings
from tests.helpers import random_container_name

ROOT = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(scope="module")
def storage():
    pass


# noinspection PyShadowingNames
@pytest.fixture(scope="module")
def container(storage):
    container_name = random_container_name()
    container = storage.create_container(container_name)

    yield container


@pytest.fixture(scope="session")
def text_filename():
    return os.path.join(ROOT, "data", settings.TEXT_FILENAME)


# noinspection PyShadowingNames
@pytest.fixture(scope="function")
def text_stream(text_filename):
    with open(text_filename, "rb") as text_stream:
        yield text_stream


# noinspection PyShadowingNames
@pytest.fixture(scope="function")
def text_blob(container, text_filename):
    text_blob = container.upload_blob(text_filename)

    yield text_blob

    if text_blob in container:
        text_blob.delete()


# noinspection PyShadowingNames
@pytest.fixture(scope="session")
def binary_filename():
    return os.path.join(ROOT, "data", settings.BINARY_FILENAME)


# noinspection PyShadowingNames
@pytest.fixture(scope="function")
def binary_stream(binary_filename):
    with open(binary_filename, "rb") as binary_stream:
        yield binary_stream


@pytest.fixture(scope="function")
def binary_bytes():
    f = io.BytesIO()
    f.write(b'1' * 1024 * 1024 * 10)
    f.seek(0)
    yield f


# noinspection PyShadowingNames
@pytest.fixture(scope="function")
def binary_blob(container, binary_filename):
    binary_blob = container.upload_blob(binary_filename)

    yield binary_blob

    if binary_blob in container:
        binary_blob.delete()


@pytest.fixture(scope="function")
def temp_file():
    fd, path = mkstemp(prefix=settings.CONTAINER_PREFIX)
    if os.name == "nt":
        # Must close in Windows, otherwise errors as file being used
        os.close(fd)
    yield path
    os.remove(path)
