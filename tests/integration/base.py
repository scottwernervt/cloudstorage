from http import HTTPStatus
from pathlib import Path

import pytest
import requests

from cloudstorage import Blob, Container, Driver
from cloudstorage.exceptions import (
    CloudStorageError,
    IsNotEmptyError,
    NotFoundError,
)
from cloudstorage.helpers import file_checksum
from tests import settings
from tests.integration.helpers import random_container_name, uri_validator


def _get_blob_checksum(blob: Blob, download_to) -> str:
    """Helper to download blob and get its checksum.

    Not all driver's store checksum with the blob like Minio.
    """
    blob.download(download_to)
    hash_type = blob.driver.hash_type
    download_hash = file_checksum(download_to, hash_type=hash_type)
    return download_hash.hexdigest()


# noinspection PyMethodMayBeStatic
class DriverTestCases:
    expire_http_status: int = HTTPStatus.FORBIDDEN

    def test_validate_credentials(self):
        raise NotImplementedError

    def test_validate_credentials_raises_exception(self):
        raise NotImplementedError

    def test_create_container(self, storage: Driver):
        container_name = random_container_name()
        container = storage.create_container(container_name)
        assert container_name in storage
        assert container.name == container_name

    def test_create_container_raises_cloud_storage_error(self, storage: Driver):
        with pytest.raises(CloudStorageError):
            storage.create_container("?!<>containername<>!?")

    def test_get_container(self, storage: Driver, container: Container):
        container_existing = storage.get_container(container.name)
        assert container_existing.name in storage
        assert container_existing == container

    def test_delete_container(self, storage: Driver):
        container_name = random_container_name()
        container = storage.create_container(container_name)
        container.delete()
        assert container.name not in storage

    def test_delete_container_raises_is_not_empty(
        self, container: Container, text_blob: Blob
    ):
        assert text_blob in container
        with pytest.raises(IsNotEmptyError):
            container.delete()

    def test_enable_cdn_for_container(self, container: Container):
        assert container.enable_cdn()

    def test_disable_cdn_for_container(self, container: Container):
        assert container.disable_cdn()

    def test_container_cdn_url_property(self, container: Container):
        assert uri_validator(container.cdn_url)
        assert container.name in container.cdn_url

    def test_generate_container_upload_url(
        self, storage: Driver, container: Container, binary_stream
    ):
        raise NotImplementedError

    def test_generate_container_upload_url_expiration(
        self, storage: Driver, container: Container, text_stream
    ):
        raise NotImplementedError

    def test_get_blob(self, container: Container, text_blob: Blob):
        blob = container.get_blob(text_blob.name)
        assert blob == text_blob

    def test_get_blob_raises_not_found(self, container: Container):
        blob_name = random_container_name()
        with pytest.raises(NotFoundError):
            container.get_blob(blob_name)

    def test_upload_blob_from_path(
        self, container: Container, text_filename, temp_file
    ):
        blob = container.upload_blob(text_filename)
        assert blob.name == settings.TEXT_FILENAME

        blob_checksum = _get_blob_checksum(blob, temp_file)
        assert blob_checksum == settings.TEXT_MD5_CHECKSUM

    def test_upload_blob_from_pathlib(
        self, container: Container, text_filename, temp_file
    ):
        blob = container.upload_blob(Path(text_filename))
        assert blob.name == settings.TEXT_FILENAME

        blob_checksum = _get_blob_checksum(blob, temp_file)
        assert blob_checksum == settings.TEXT_MD5_CHECKSUM

    def test_upload_blob_from_stream(
        self, container: Container, text_filename, temp_file
    ):
        blob = container.upload_blob(Path(text_filename))
        assert blob.name == settings.TEXT_FILENAME

        blob_checksum = _get_blob_checksum(blob, temp_file)
        assert blob_checksum == settings.TEXT_MD5_CHECKSUM

    def test_upload_blob_with_options(
        self, container: Container, binary_stream, temp_file
    ):
        blob = container.upload_blob(
            filename=binary_stream,
            blob_name=settings.BINARY_STREAM_FILENAME,
            **settings.BINARY_OPTIONS,
        )
        assert blob.name == settings.BINARY_STREAM_FILENAME
        assert blob.meta_data == settings.BINARY_OPTIONS["meta_data"]
        assert blob.content_type == settings.BINARY_OPTIONS["content_type"]

        blob.download(temp_file)
        hash_type = blob.driver.hash_type
        download_hash = file_checksum(temp_file, hash_type=hash_type)
        assert download_hash.hexdigest() == settings.BINARY_MD5_CHECKSUM

    def test_delete_blob(self, container: Container, text_blob: Blob):
        text_blob.delete()
        assert text_blob not in container

    def test_download_blob_to_path(self, binary_blob: Blob, temp_file):
        binary_blob.download(temp_file)
        hash_type = binary_blob.driver.hash_type
        download_hash = file_checksum(temp_file, hash_type=hash_type)
        assert download_hash.hexdigest() == settings.BINARY_MD5_CHECKSUM

    def test_download_blob_to_pathlib_path(self, binary_blob: Blob, temp_file):
        binary_blob.download(Path(temp_file))
        hash_type = binary_blob.driver.hash_type
        download_hash = file_checksum(temp_file, hash_type=hash_type)
        assert download_hash.hexdigest() == settings.BINARY_MD5_CHECKSUM

    def test_download_blob_to_stream(self, binary_blob: Blob, temp_file):
        with open(temp_file, "wb") as download_file:
            binary_blob.download(download_file)

        hash_type = binary_blob.driver.hash_type
        download_hash = file_checksum(temp_file, hash_type=hash_type)
        assert download_hash.hexdigest() == settings.BINARY_MD5_CHECKSUM

    def test_blob_cdn_url_property(self, container: Container, binary_blob):
        container.enable_cdn()
        assert uri_validator(binary_blob.cdn_url)
        assert binary_blob.container.name in binary_blob.cdn_url
        assert binary_blob.name in binary_blob.cdn_url

    def test_generate_blob_download_url(
        self, storage: Driver, binary_blob: Blob, temp_file
    ):
        content_disposition = settings.BINARY_OPTIONS.get("content_disposition")
        download_url = binary_blob.generate_download_url(
            content_disposition=content_disposition
        )
        assert uri_validator(download_url)

        response = requests.get(download_url)
        assert response.status_code == HTTPStatus.OK, response.text
        assert response.headers["content-disposition"] == content_disposition

        with open(temp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=128):
                f.write(chunk)

        hash_type = binary_blob.driver.hash_type
        download_hash = file_checksum(temp_file, hash_type=hash_type)
        assert download_hash.hexdigest() == settings.BINARY_MD5_CHECKSUM

    def test_generate_blob_download_url_expiration(
        self, storage: Driver, binary_blob: Blob
    ):
        download_url = binary_blob.generate_download_url(expires=-10)
        assert uri_validator(download_url)

        response = requests.get(download_url)
        assert response.status_code == self.expire_http_status, response.text
