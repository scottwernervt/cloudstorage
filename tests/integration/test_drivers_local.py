import os
import shutil

from http import HTTPStatus

import pytest

from cloudstorage import Blob, Container, Driver
from cloudstorage.drivers.local import LocalDriver
from cloudstorage.exceptions import CredentialsError, SignatureExpiredError
from cloudstorage.helpers import file_checksum
from tests import settings
from tests.integration.base import DriverTestCases
from tests.integration.helpers import cleanup_storage

if settings.LOCAL_KEY and not os.path.exists(settings.LOCAL_KEY):
    os.makedirs(settings.LOCAL_KEY)

pytestmark = pytest.mark.skipif(
    not os.path.isdir(settings.LOCAL_KEY), reason="Directory does not exist."
)


@pytest.fixture(scope="module")
def storage():
    driver = LocalDriver(key=settings.LOCAL_KEY, secret=settings.LOCAL_SECRET)
    yield driver
    cleanup_storage(driver)
    shutil.rmtree(settings.LOCAL_KEY)


@pytest.fixture(scope="module")
def windows_storage(storage):
    driver = LocalDriver(key=settings.LOCAL_KEY, secret=settings.LOCAL_SECRET)
    driver.is_windows = True
    driver.create_container("windows")

    yield driver

    cleanup_storage(driver)
    shutil.rmtree(settings.LOCAL_KEY)


class TestLocalDriver(DriverTestCases):
    expire_http_status = HTTPStatus.FORBIDDEN

    @pytest.mark.skipif(os.name == "nt", reason="Test incompatible with Windows.")
    def test_validate_credentials(self):
        driver = LocalDriver(key=settings.LOCAL_KEY)
        assert driver.validate_credentials() is None

    def test_validate_credentials_raises_exception(self):
        driver = LocalDriver(key="/")
        with pytest.raises(CredentialsError):
            driver.validate_credentials()

    @pytest.mark.skip(reason="Local does not support enabling CDN.")
    def test_enable_cdn_for_container(self, container: Container):
        super().test_enable_cdn_for_container(container)

    @pytest.mark.skip(reason="Local does not support disabling CDN.")
    def test_disable_cdn_for_container(self, container: Container):
        super().test_disable_cdn_for_container(container)

    @pytest.mark.skipif(os.name == "posix", reason="Test incompatible with Linux.")
    def test_create_container_raises_cloud_storage_error(self, storage):
        super().test_create_container_raises_cloud_storage_error(storage)

    @pytest.mark.skipif(
        settings.LOCAL_KEY.startswith("/tmp"),
        reason="Extended attributes are not supported for tmpfs file system.",
    )
    def test_upload_blob_with_options(
        self, container: Container, binary_stream, temp_file
    ):
        super().test_upload_blob_with_options(container, binary_stream, temp_file)

    def test_generate_container_upload_url(
        self, storage: Driver, container: Container, binary_stream
    ):
        form_post = container.generate_upload_url(
            settings.BINARY_FORM_FILENAME, **settings.BINARY_OPTIONS
        )
        assert "url" in form_post and "fields" in form_post
        assert "signature" in form_post["fields"]

        signature = form_post["fields"]["signature"]
        payload = storage.validate_signature(signature)
        assert (
            payload["content_disposition"]
            == settings.BINARY_OPTIONS["content_disposition"]
        )
        assert payload["cache_control"] == settings.BINARY_OPTIONS["cache_control"]
        assert payload["blob_name"] == settings.BINARY_FORM_FILENAME
        assert payload["container"] == container.name
        assert payload["meta_data"] == settings.BINARY_OPTIONS["meta_data"]

    def test_generate_container_upload_url_expiration(
        self, storage: Driver, container: Container, text_stream
    ):
        form_post = container.generate_upload_url(
            settings.TEXT_FORM_FILENAME, expires=-10
        )
        signature = form_post["fields"]["signature"]

        with pytest.raises(SignatureExpiredError):
            storage.validate_signature(signature)

    def test_generate_blob_download_url(
        self, storage: Driver, binary_blob: Blob, temp_file
    ):
        content_disposition = settings.BINARY_OPTIONS.get("content_disposition")
        signature = binary_blob.generate_download_url(
            content_disposition=content_disposition
        )

        payload = storage.validate_signature(signature)
        assert payload["blob_name"] == binary_blob.name
        assert payload["container"] == binary_blob.container.name
        assert payload["content_disposition"] == content_disposition

    def test_generate_blob_download_url_expiration(
        self, storage: Driver, binary_blob: Blob
    ):
        signature = binary_blob.generate_download_url(expires=-10)

        with pytest.raises(SignatureExpiredError):
            storage.validate_signature(signature)

    def test_upload_blob_with_options_on_windows_env(
        self, windows_storage: LocalDriver, binary_stream, temp_file
    ):
        container = windows_storage.get_container("windows")
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

    def test_container_does_not_return_xattr_files_on_windows_env(
        self, windows_storage: LocalDriver, text_filename, temp_file
    ):
        container = windows_storage.get_container("windows")
        container.upload_blob(text_filename, meta_data={"test": "testvalue"})
        for blob in container:
            assert not blob.name.startswith(".")
            assert not blob.name.endswith(".xattr")
