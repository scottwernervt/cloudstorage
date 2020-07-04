from http import HTTPStatus

import pytest
import requests

from cloudstorage import Container
from cloudstorage.drivers.microsoft import AzureStorageDriver
from cloudstorage.exceptions import CredentialsError
from tests import settings
from tests.helpers import uri_validator
from tests.integration.base import DriverTestCases
from tests.integration.helpers import cleanup_storage

pytestmark = pytest.mark.skipif(
    not bool(settings.AZURE_ACCOUNT_NAME),
    reason="settings missing account name and key.",
)


@pytest.fixture(scope="module")
def storage():
    driver = AzureStorageDriver(
        account_name=settings.AZURE_ACCOUNT_NAME, key=settings.AZURE_ACCOUNT_KEY
    )
    yield driver
    cleanup_storage(driver)


class TestMicrosoftDriver(DriverTestCases):
    expire_http_status = HTTPStatus.FORBIDDEN

    def test_validate_credentials(self):
        driver = AzureStorageDriver(
            account_name=settings.AZURE_ACCOUNT_NAME, key=settings.AZURE_ACCOUNT_KEY
        )
        assert driver.validate_credentials() is None

    def test_validate_credentials_raises_exception(self):
        driver = AzureStorageDriver(
            account_name=settings.AZURE_ACCOUNT_NAME, key="invalid-key==",
        )
        with pytest.raises(CredentialsError):
            driver.validate_credentials()

    @pytest.mark.skip(reason="Azure does not support enabling CDN.")
    def test_enable_cdn_for_container(self):
        super().test_enable_cdn_for_container()

    @pytest.mark.skip(reason="Azure does not support disabling CDN.")
    def test_disable_cdn_for_container(self):
        super().test_disable_cdn_for_container()

    def test_generate_container_upload_url(self, container: Container, binary_stream):
        form_post = container.generate_upload_url(
            blob_name="prefix_", **settings.BINARY_OPTIONS
        )
        assert "url" in form_post and "fields" in form_post
        assert uri_validator(form_post["url"])

        url = form_post["url"]
        headers = form_post["headers"]
        multipart_form_data = {
            "file": (settings.BINARY_FORM_FILENAME, binary_stream, "image/png"),
        }

        # https://blogs.msdn.microsoft.com/azureossds/2015/03/30/uploading-files-to-
        # azure-storage-using-sasshared-access-signature/
        response = requests.put(url, headers=headers, files=multipart_form_data)
        assert response.status_code == HTTPStatus.CREATED, response.text

        blob = container.get_blob("prefix_")
        assert blob.meta_data == settings.BINARY_OPTIONS["meta_data"]
        assert blob.content_type == settings.BINARY_OPTIONS["content_type"]
        assert (
            blob.content_disposition == settings.BINARY_OPTIONS["content_disposition"]
        )
        assert blob.cache_control == settings.BINARY_OPTIONS["cache_control"]

    def test_generate_container_upload_url_expiration(
        self, container: Container, text_stream
    ):
        form_post = container.generate_upload_url(blob_name="", expires=-10)
        assert "url" in form_post and "fields" in form_post
        assert uri_validator(form_post["url"])

        url = form_post["url"]
        headers = form_post["headers"]
        multipart_form_data = {"file": text_stream}

        response = requests.put(url, headers=headers, files=multipart_form_data)
        assert response.status_code == HTTPStatus.BAD_REQUEST, response.text
