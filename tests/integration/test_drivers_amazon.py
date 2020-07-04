from http import HTTPStatus

import pytest
import requests

from cloudstorage import Container
from cloudstorage.drivers.amazon import S3Driver
from cloudstorage.exceptions import CredentialsError
from tests import settings
from tests.integration.base import DriverTestCases
from tests.integration.helpers import cleanup_storage, uri_validator

pytestmark = pytest.mark.skipif(
    not bool(settings.AMAZON_KEY), reason="AMAZON_KEY not set.",
)


@pytest.fixture(scope="module")
def storage():
    driver = S3Driver(
        settings.AMAZON_KEY, settings.AMAZON_SECRET, settings.AMAZON_REGION
    )
    yield driver
    cleanup_storage(driver)


class TestAmazonDriver(DriverTestCases):
    expire_http_status = HTTPStatus.FORBIDDEN

    def test_validate_credentials(self):
        driver = S3Driver(
            settings.AMAZON_KEY, settings.AMAZON_SECRET, settings.AMAZON_REGION
        )
        assert driver.validate_credentials() is None

    def test_validate_credentials_raises_exception(self):
        driver = S3Driver(settings.AMAZON_KEY, "invalid-secret", settings.AMAZON_REGION)
        with pytest.raises(CredentialsError):
            driver.validate_credentials()

    @pytest.mark.skip(reason="S3 does not support enabling CDN.")
    def test_enable_cdn_for_container(self):
        pass

    @pytest.mark.skip(reason="S3 does not support disabling CDN.")
    def test_disable_cdn_for_container(self):
        pass

    def test_generate_container_upload_url(
        self, storage: S3Driver, container: Container, binary_stream
    ):
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
        assert (
            blob.content_disposition == settings.BINARY_OPTIONS["content_disposition"]
        )
        assert blob.cache_control == settings.BINARY_OPTIONS["cache_control"]

    def test_generate_container_upload_url_expiration(
        self, storage: S3Driver, container: Container, text_stream
    ):
        form_post = container.generate_upload_url(
            settings.TEXT_FORM_FILENAME, expires=-10
        )
        assert "url" in form_post
        assert uri_validator(form_post["url"])
        assert "fields" in form_post

        url = form_post["url"]
        fields = form_post["fields"]
        multipart_form_data = {"file": text_stream}
        response = requests.post(url, data=fields, files=multipart_form_data)
        assert response.status_code == HTTPStatus.FORBIDDEN, response.text
