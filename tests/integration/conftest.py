import os

from pathlib import Path

import pytest

from tests.integration.helpers import random_container_name

PWD_PATH = Path(os.path.dirname(os.path.realpath(__file__)))
DATA_PATH = PWD_PATH.parents[0] / "data"


@pytest.fixture(scope="module")
def container(storage):
    container_name = random_container_name()
    container = storage.create_container(container_name)
    yield container


@pytest.fixture(scope="function")
def text_blob(container, text_filename):
    text_blob = container.upload_blob(text_filename)

    yield text_blob

    if text_blob in container:
        text_blob.delete()


@pytest.fixture(scope="function")
def binary_blob(container, binary_filename):
    binary_blob = container.upload_blob(binary_filename)

    yield binary_blob

    if binary_blob in container:
        binary_blob.delete()
