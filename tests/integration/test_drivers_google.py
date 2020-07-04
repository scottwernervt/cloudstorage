import os
import random

from http import HTTPStatus
from time import sleep

import pytest
import requests

from cloudstorage import Container
from cloudstorage.drivers.google import GoogleStorageDriver
from tests import settings
from tests.helpers import uri_validator
from tests.integration.base import DriverTestCases

pytestmark = pytest.mark.skipif(
    not bool(settings.GOOGLE_CREDENTIALS)
    or not os.path.isfile(settings.GOOGLE_CREDENTIALS),
    reason="GOOGLE_CREDENTIALS not set.",
)


@pytest.fixture(scope="module")
def storage():
    driver = GoogleStorageDriver(key=settings.GOOGLE_CREDENTIALS)

    yield driver

    seconds = random.random() * 3
    for container in driver:
        if container.name.startswith(settings.CONTAINER_PREFIX):
            for blob in container:
                sleep(seconds)
                blob.delete()

            sleep(seconds)
            container.delete()


class TestGoogleDriver(DriverTestCases):
    expire_http_status = HTTPStatus.BAD_REQUEST

    def test_validate_credentials(self):
        driver = GoogleStorageDriver(key=settings.GOOGLE_CREDENTIALS)
        assert driver.validate_credentials() is None

    @pytest.mark.skip("Generate invalid private key for gcs service account.")
    def test_validate_credentials_raises_exception(self):
        pass

    def test_generate_container_upload_url(self, container: Container, binary_stream):
        form_post = container.generate_upload_url(
            blob_name="prefix_", **settings.BINARY_OPTIONS
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

        blob = container.get_blob("prefix_" + settings.BINARY_FORM_FILENAME)
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
        fields = form_post["fields"]
        multipart_form_data = {"file": text_stream}
        response = requests.post(url, data=fields, files=multipart_form_data)
        assert response.status_code == HTTPStatus.BAD_REQUEST, response.text
