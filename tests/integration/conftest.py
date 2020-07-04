import os

from tempfile import NamedTemporaryFile
from pathlib import Path

import pytest

from tests import settings
from tests.helpers import random_container_name

PWD_PATH = Path(os.path.dirname(os.path.realpath(__file__)))
DATA_PATH = PWD_PATH.parents[0] / "data"


@pytest.fixture(scope="module")
def container(storage):
    container_name = random_container_name()
    container = storage.create_container(container_name)
    yield container


@pytest.fixture(scope="session")
def text_filename():
    return DATA_PATH / settings.TEXT_FILENAME


@pytest.fixture(scope="function")
def text_stream(text_filename):
    with open(text_filename, "rb") as text_stream:
        yield text_stream


@pytest.fixture(scope="function")
def text_blob(container, text_filename):
    text_blob = container.upload_blob(text_filename)

    yield text_blob

    if text_blob in container:
        text_blob.delete()


@pytest.fixture(scope="session")
def binary_filename():
    return DATA_PATH / Path(settings.BINARY_FILENAME)


@pytest.fixture(scope="function")
def binary_stream(binary_filename):
    with open(binary_filename, "rb") as binary_stream:
        yield binary_stream


@pytest.fixture(scope="function")
def binary_blob(container, binary_filename):
    binary_blob = container.upload_blob(binary_filename)

    yield binary_blob

    if binary_blob in container:
        binary_blob.delete()


@pytest.fixture(scope="function")
def temp_file():
    with NamedTemporaryFile(prefix=settings.CONTAINER_PREFIX) as temp_file:
        yield temp_file.name
