import io
import os
import shutil
import multiprocessing as mp
import time
import hashlib

import pytest

from cloudstorage.drivers.local import LocalDriver
from cloudstorage.exceptions import (
    CredentialsError,
    IsNotEmptyError,
    NotFoundError,
    SignatureExpiredError,
)
from tests import settings
from tests.helpers import random_container_name, uri_validator

if settings.LOCAL_KEY and not os.path.exists(settings.LOCAL_KEY):
    os.makedirs(settings.LOCAL_KEY)

pytestmark = pytest.mark.skipif(
    not os.path.isdir(settings.LOCAL_KEY), reason="Directory does not exist."
)


@pytest.fixture(scope="module")
def storage():
    driver = LocalDriver(key=settings.LOCAL_KEY, secret=settings.LOCAL_SECRET)

    yield driver

    for container in driver:  # cleanup
        if container.name.startswith(settings.CONTAINER_PREFIX):
            for blob in container:
                blob.delete()

            container.delete()

    shutil.rmtree(settings.LOCAL_KEY)


def test_driver_validate_credentials():
    if os.name == "nt":
        pytest.skip("skipping Windows incompatible test")
    driver = LocalDriver(key=settings.LOCAL_KEY)
    assert driver.validate_credentials() is None

    driver = LocalDriver(key="/")
    with pytest.raises(CredentialsError) as excinfo:
        driver.validate_credentials()
    assert excinfo.value
    assert excinfo.value.message


# noinspection PyShadowingNames
def test_driver_create_container(storage):
    container_name = random_container_name()
    container = storage.create_container(container_name)
    assert container_name in storage
    assert container.name == container_name


# noinspection PyShadowingNames
def test_driver_get_container(storage, container):
    container_get = storage.get_container(container.name)
    assert container_get.name in storage
    assert container_get == container


# noinspection PyShadowingNames
def test_container_get_invalid(storage):
    container_name = random_container_name()

    # noinspection PyTypeChecker
    with pytest.raises(NotFoundError):
        storage.get_container(container_name)


# noinspection PyShadowingNames
def test_container_delete(storage):
    container_name = random_container_name()
    container = storage.create_container(container_name)
    container.delete()
    assert container.name not in storage


def test_container_delete_not_empty(container, text_blob):
    assert text_blob in container

    # noinspection PyTypeChecker
    with pytest.raises(IsNotEmptyError):
        container.delete()


def test_container_enable_cdn(container):
    assert not container.enable_cdn(), "Local does not support enabling CDN."


def test_container_disable_cdn(container):
    assert not container.disable_cdn(), "Local does not support disabling CDN."


def test_container_cdn_url(container):
    container.enable_cdn()
    cdn_url = container.cdn_url

    assert uri_validator(cdn_url)
    assert container.name in cdn_url


# noinspection PyShadowingNames
def test_container_generate_upload_url(storage, container):
    form_post = container.generate_upload_url(
        settings.BINARY_FORM_FILENAME, **settings.BINARY_OPTIONS
    )
    assert "url" in form_post and "fields" in form_post
    assert "signature" in form_post["fields"]

    signature = form_post["fields"]["signature"]
    payload = storage.validate_signature(signature)
    assert (
        payload["content_disposition"] == settings.BINARY_OPTIONS["content_disposition"]
    )
    assert payload["cache_control"] == settings.BINARY_OPTIONS["cache_control"]
    assert payload["blob_name"] == settings.BINARY_FORM_FILENAME
    assert payload["container"] == container.name
    assert payload["meta_data"] == settings.BINARY_OPTIONS["meta_data"]


# noinspection PyShadowingNames
def test_container_generate_upload_url_expiration(storage, container):
    form_post = container.generate_upload_url(settings.TEXT_FORM_FILENAME, expires=-10)
    signature = form_post["fields"]["signature"]

    with pytest.raises(SignatureExpiredError):
        storage.validate_signature(signature)


def test_container_get_blob(container, text_blob):
    text_get_blob = container.get_blob(text_blob.name)
    assert text_get_blob == text_blob


def test_container_get_blobs(container):
    container.upload_blob(
        io.BytesIO(b'Hello'),
        blob_name='some/where/hello.txt'
    )

    assert [blob.name for blob in container] == ['some/where/hello.txt']


def test_container_get_blob_invalid(container):
    blob_name = random_container_name()

    # noinspection PyTypeChecker
    with pytest.raises(NotFoundError):
        container.get_blob(blob_name)


def test_blob_upload_path(container, text_filename):
    blob = container.upload_blob(text_filename)
    assert blob.name == settings.TEXT_FILENAME
    assert blob.checksum == settings.TEXT_MD5_CHECKSUM


def test_blob_windows_xattr(container, text_filename):
    if os.name != "nt":
        pytest.skip("skipping Windows-only test")
    container.upload_blob(text_filename, meta_data={"test": "testvalue"})
    try:
        container.get_blob(".{}.xattr".format(settings.TEXT_FILENAME))
        pytest.fail("should not be possible to get internal xattr file")
    except NotFoundError:
        pass


def test_blob_windows_xattr_list(container, text_filename):
    if os.name != "nt":
        pytest.skip("skipping Windows-only test")
    container.upload_blob(text_filename, meta_data={"test": "testvalue"})
    for blobitem in container:
        if blobitem.name.startswith(".") and blobitem.name.endswith(".xattr"):
            pytest.fail("should not be possible to get internal xattr file")


def test_blob_upload_stream(container, binary_stream):
    blob = container.upload_blob(
        filename=binary_stream,
        blob_name=settings.BINARY_STREAM_FILENAME,
        **settings.BINARY_OPTIONS,
    )
    assert blob.name == settings.BINARY_STREAM_FILENAME
    assert blob.checksum == settings.BINARY_MD5_CHECKSUM


def test_blob_upload_stream_interrupted(container, binary_bytes):
    BLOB_NAME = "data.bin"
    md5 = hashlib.md5()
    md5.update(binary_bytes.getbuffer())
    mk5_checksum = md5.hexdigest()

    def _upload():
        container.upload_blob(filename=binary_bytes, blob_name=BLOB_NAME)

    p = mp.Process(target=_upload)
    p.start()
    time.sleep(0.01)
    os.kill(p.pid, 9)
    p.join()

    bad_blob = container.get_blob(BLOB_NAME + ".tmp")
    assert bad_blob.checksum != mk5_checksum
    bad_blob.delete()

    with pytest.raises(NotFoundError):
        container.get_blob(BLOB_NAME)


@pytest.mark.skipif(
    settings.LOCAL_KEY.startswith("/tmp"),
    reason="Extended attributes are not supported for tmpfs file system.",
)
def test_blob_upload_options(container, binary_stream):
    blob = container.upload_blob(
        binary_stream,
        blob_name=settings.BINARY_STREAM_FILENAME,
        **settings.BINARY_OPTIONS,
    )
    assert blob.name == settings.BINARY_STREAM_FILENAME
    assert blob.checksum == settings.BINARY_MD5_CHECKSUM
    assert blob.meta_data == settings.BINARY_OPTIONS["meta_data"]
    assert blob.content_type == settings.BINARY_OPTIONS["content_type"]
    assert blob.content_disposition == settings.BINARY_OPTIONS["content_disposition"]
    assert blob.cache_control == settings.BINARY_OPTIONS["cache_control"]


def test_blob_delete(container, text_blob):
    text_blob.delete()
    assert text_blob not in container


def test_blob_cdn_url(binary_blob):
    cdn_url = binary_blob.cdn_url
    assert uri_validator(cdn_url)
    assert binary_blob.container.name in cdn_url
    assert binary_blob.name in cdn_url


# noinspection PyShadowingNames
def test_blob_generate_download_url(storage, binary_blob):
    content_disposition = settings.BINARY_OPTIONS.get("content_disposition")
    signature = binary_blob.generate_download_url(
        content_disposition=content_disposition
    )

    payload = storage.validate_signature(signature)
    assert payload["blob_name"] == binary_blob.name
    assert payload["container"] == binary_blob.container.name
    assert payload["content_disposition"] == content_disposition


# noinspection PyShadowingNames
def test_blob_generate_download_url_expiration(storage, binary_blob):
    signature = binary_blob.generate_download_url(expires=-10)

    with pytest.raises(SignatureExpiredError):
        storage.validate_signature(signature)
