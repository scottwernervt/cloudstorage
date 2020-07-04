from http import HTTPStatus
from time import sleep

import pytest
import requests

from cloudstorage import Blob, Container
from cloudstorage.drivers.minio import MinioDriver
from cloudstorage.exceptions import CredentialsError
from tests import settings
from tests.helpers import uri_validator
from tests.integration.base import DriverTestCases
from tests.integration.helpers import cleanup_storage

pytestmark = pytest.mark.skipif(
    not bool(settings.MINIO_ACCESS_KEY), reason="MINIO_ACCESS_KEY not set."
)


@pytest.fixture(scope="module")
def storage():
    driver = MinioDriver(
        settings.MINIO_ENDPOINT,
        settings.MINIO_ACCESS_KEY,
        settings.MINIO_SECRET_KEY,
        settings.MINIO_REGION,
    )
    yield driver
    cleanup_storage(driver)


class TestMinioDriver(DriverTestCases):
    expire_http_status = HTTPStatus.FORBIDDEN

    def test_validate_credentials(self):
        driver = MinioDriver(
            settings.MINIO_ENDPOINT,
            settings.MINIO_ACCESS_KEY,
            settings.MINIO_SECRET_KEY,
            settings.MINIO_REGION,
        )
        assert driver.validate_credentials() is None

    def test_validate_credentials_raises_exception(self):
        driver = MinioDriver(
            settings.MINIO_ENDPOINT,
            settings.MINIO_ACCESS_KEY,
            "invalid-secret",
            settings.MINIO_REGION,
        )
        with pytest.raises(CredentialsError):
            driver.validate_credentials()

    @pytest.mark.skip(reason="Minio does not support enabling CDN.")
    def test_enable_cdn_for_container(self):
        pass

    @pytest.mark.skip(reason="Minio does not support disabling CDN.")
    def test_disable_cdn_for_container(self):
        pass

    def test_generate_container_upload_url(self, container: Container, binary_stream):
        form_post = container.generate_upload_url(
            settings.BINARY_FORM_FILENAME, **settings.BINARY_OPTIONS
        )
        assert "url" in form_post and "fields" in form_post
        assert uri_validator(form_post["url"])

        url = form_post["url"]
        fields = form_post["fields"]
        multipart_form_data = {
            "file": (settings.BINARY_FORM_FILENAME, binary_stream, "image/png"),
        }
        response = requests.post(url, data=fields, files=multipart_form_data)
        assert response.status_code == HTTPStatus.NO_CONTENT, response.text

        blob = container.get_blob(settings.BINARY_FORM_FILENAME)
        assert blob.meta_data == settings.BINARY_OPTIONS["meta_data"]
        assert blob.content_type == settings.BINARY_OPTIONS["content_type"]

    def test_generate_container_upload_url_expiration(
        self, container: Container, text_stream
    ):
        form_post = container.generate_upload_url(
            settings.TEXT_FORM_FILENAME, expires=1
        )
        assert "url" in form_post and "fields" in form_post
        assert uri_validator(form_post["url"])

        sleep(1.1)  # cannot generate a policy with -1 value

        url = form_post["url"]
        fields = form_post["fields"]
        multipart_form_data = {"file": text_stream}
        response = requests.post(url, data=fields, files=multipart_form_data)

        if "s3" in container.driver.client._endpoint_url:
            http_code = HTTPStatus.FORBIDDEN
        else:  # minio server
            http_code = HTTPStatus.BAD_REQUEST

        assert response.status_code == http_code, response.text

    def test_generate_blob_download_url_expiration(self, binary_blob: Blob):
        download_url = binary_blob.generate_download_url(expires=1)
        assert uri_validator(download_url)

        sleep(1.1)  # cannot generate a policy with -1 value

        response = requests.get(download_url)
        assert response.status_code == HTTPStatus.FORBIDDEN, response.text
