from http import HTTPStatus

import pytest
import requests

from cloudstorage import Blob, Container, Driver
from cloudstorage.drivers.rackspace import CloudFilesDriver
from cloudstorage.exceptions import CredentialsError, NotFoundError
from cloudstorage.helpers import file_checksum, parse_content_disposition
from tests import settings
from tests.helpers import uri_validator
from tests.integration.base import DriverTestCases

pytestmark = pytest.mark.skipif(
    not bool(settings.RACKSPACE_KEY), reason="settings missing key and secret"
)


@pytest.fixture(scope="module")
def storage():
    driver = CloudFilesDriver(
        settings.RACKSPACE_KEY, settings.RACKSPACE_SECRET, settings.RACKSPACE_REGION
    )

    yield driver

    for container in driver:  # cleanup
        if container.name.startswith(settings.CONTAINER_PREFIX):
            for blob in container:
                try:
                    blob.delete()
                except NotFoundError:
                    # TODO: TESTS: Rackspace sometimes throws ResourceNotFound
                    pass

            container.delete()


class TestRackspaceDriver(DriverTestCases):
    expire_http_status = HTTPStatus.UNAUTHORIZED

    def test_validate_credentials(self):
        driver = CloudFilesDriver(
            settings.RACKSPACE_KEY, settings.RACKSPACE_SECRET, settings.RACKSPACE_REGION
        )
        assert driver.validate_credentials() is None

    def test_validate_credentials_raises_exception(self):
        driver = CloudFilesDriver(
            settings.RACKSPACE_KEY, "invalid-secret", settings.RACKSPACE_REGION
        )
        with pytest.raises(CredentialsError):
            driver.validate_credentials()

    def test_container_cdn_url_property(self, container: Container):
        """Container name not in cdn url."""
        container.enable_cdn()
        assert uri_validator(container.cdn_url)

    def test_generate_container_upload_url(
        self, storage: CloudFilesDriver, container: Container, binary_stream
    ):
        form_post = container.generate_upload_url(blob_name="prefix_")
        assert "url" in form_post and "fields" in form_post
        assert uri_validator(form_post["url"])

        url = form_post["url"]
        fields = form_post["fields"]
        multipart_form_data = {
            "file": (settings.BINARY_FORM_FILENAME, binary_stream, "image/png"),
        }
        response = requests.post(url, data=fields, files=multipart_form_data)
        assert response.status_code == HTTPStatus.CREATED, response.text

        blob = container.get_blob("prefix_" + settings.BINARY_FORM_FILENAME)
        # Options not supported: meta_data, content_disposition, and cache_control.
        assert blob.content_type == settings.BINARY_OPTIONS["content_type"]

    def test_generate_container_upload_url_expiration(
        self, storage: CloudFilesDriver, container: Container, text_stream
    ):
        form_post = container.generate_upload_url(blob_name="", expires=-10)
        assert "fields" in form_post
        assert "url" in form_post
        assert uri_validator(form_post["url"])

        url = form_post["url"]
        fields = form_post["fields"]
        multipart_form_data = {"file": text_stream}
        response = requests.post(url, data=fields, files=multipart_form_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response.text

    def test_upload_blob_with_options(self, container, binary_stream):
        """Cache-Control not found and Openstack SDK always returns
        Content-Type: "text/html; charset=UTF-8.
        """
        blob = container.upload_blob(
            binary_stream,
            blob_name=settings.BINARY_STREAM_FILENAME,
            **settings.BINARY_OPTIONS,
        )
        assert blob.name == settings.BINARY_STREAM_FILENAME
        assert blob.checksum == settings.BINARY_MD5_CHECKSUM
        assert blob.meta_data == settings.BINARY_OPTIONS["meta_data"]
        assert (
            blob.content_disposition == settings.BINARY_OPTIONS["content_disposition"]
        )

    def test_blob_cdn_url_property(self, container: Container, binary_blob):
        """Container name not in cdn url."""
        container.enable_cdn()
        assert uri_validator(binary_blob.cdn_url)
        assert binary_blob.name in binary_blob.cdn_url

    def test_generate_blob_download_url(
        self, storage: Driver, binary_blob: Blob, temp_file
    ):
        """Rackspace adds garbage to header:

        attachment; filename=avatar-attachment.png;
        filename*=UTF-8\\'\\'avatar-attachment.png'
        """
        content_disposition = settings.BINARY_OPTIONS.get("content_disposition")
        download_url = binary_blob.generate_download_url(
            content_disposition=content_disposition
        )
        assert uri_validator(download_url)

        response = requests.get(download_url)
        assert response.status_code == HTTPStatus.OK, response.text
        disposition, params = parse_content_disposition(
            response.headers["content-disposition"]
        )
        response_disposition = "{}; filename={}".format(disposition, params["filename"])
        assert response_disposition == content_disposition

        with open(temp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=128):
                f.write(chunk)

        hash_type = binary_blob.driver.hash_type
        download_hash = file_checksum(temp_file, hash_type=hash_type)
        assert download_hash.hexdigest() == settings.BINARY_MD5_CHECKSUM
