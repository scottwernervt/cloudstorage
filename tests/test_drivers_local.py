import pytest

from cloudstorage.drivers.local import LocalDriver
from cloudstorage.exceptions import IsNotEmptyError
from cloudstorage.exceptions import NotFoundError
from cloudstorage.exceptions import SignatureExpiredError
from tests.helpers import random_container_name, uri_validator
from tests.settings import *

pytestmark = pytest.mark.skipif(not bool(LOCAL_KEY),
                                reason='settings missing key and secret')


@pytest.fixture(scope='module')
def storage():
    driver = LocalDriver(key=LOCAL_KEY, secret=LOCAL_SECRET)

    yield driver

    for container in driver:  # cleanup
        if container.name.startswith(CONTAINER_PREFIX):
            for blob in container:
                blob.delete()

            container.delete()

    os.rmdir(LOCAL_KEY)


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
    assert not container.enable_cdn(), 'Local does not support enabling CDN.'


def test_container_disable_cdn(container):
    assert not container.disable_cdn(), 'Local does not support disabling CDN.'


def test_container_cdn_url(container):
    container.enable_cdn()
    cdn_url = container.cdn_url

    assert uri_validator(cdn_url)
    assert container.name in cdn_url


# noinspection PyShadowingNames
def test_container_generate_upload_url(storage, container):
    form_post = container.generate_upload_url(BINARY_FORM_FILENAME,
                                              **BINARY_OPTIONS)
    assert 'url' in form_post and 'fields' in form_post
    assert 'signature' in form_post['fields']

    signature = form_post['fields']['signature']
    payload = storage.validate_signature(signature)
    assert payload['content_disposition'] == BINARY_OPTIONS[
        'content_disposition']
    assert payload['blob_name'] == BINARY_FORM_FILENAME
    assert payload['container'] == container.name
    assert payload['meta_data'] == BINARY_OPTIONS['meta_data']


# noinspection PyShadowingNames
def test_container_generate_upload_url_expiration(storage, container):
    form_post = container.generate_upload_url(TEXT_FORM_FILENAME, expires=-10)
    signature = form_post['fields']['signature']

    with pytest.raises(SignatureExpiredError):
        storage.validate_signature(signature)


def test_container_get_blob(container, text_blob):
    text_get_blob = container.get_blob(text_blob.name)
    assert text_get_blob == text_blob


def test_container_get_blob_invalid(container):
    blob_name = random_container_name()

    # noinspection PyTypeChecker
    with pytest.raises(NotFoundError):
        container.get_blob(blob_name)


def test_blob_upload_path(container, text_filename):
    blob = container.upload_blob(text_filename)
    assert blob.name == TEXT_FILENAME
    assert blob.checksum == TEXT_MD5_CHECKSUM


def test_blob_upload_stream(container, binary_stream):
    blob = container.upload_blob(filename=binary_stream,
                                 blob_name=BINARY_STREAM_FILENAME,
                                 **BINARY_OPTIONS)
    assert blob.name == BINARY_STREAM_FILENAME
    assert blob.checksum == BINARY_MD5_CHECKSUM


@pytest.mark.skipif(
    LOCAL_KEY.startswith('/tmp'),
    reason='Extended attributes are not supported for tmpfs file system.')
def test_blob_upload_options(container, binary_stream):
    blob = container.upload_blob(binary_stream,
                                 blob_name=BINARY_STREAM_FILENAME,
                                 **BINARY_OPTIONS)
    assert blob.name == BINARY_STREAM_FILENAME
    assert blob.checksum == BINARY_MD5_CHECKSUM
    assert blob.meta_data == BINARY_OPTIONS['meta_data']
    assert blob.content_type == BINARY_OPTIONS['content_type']
    assert blob.content_disposition == BINARY_OPTIONS['content_disposition']


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
    content_disposition = BINARY_OPTIONS.get('content_disposition')
    signature = binary_blob.generate_download_url(
        content_disposition=content_disposition)

    payload = storage.validate_signature(signature)
    assert payload['content_disposition'] == content_disposition
    assert payload['blob_name'] == binary_blob.name
    assert payload['container'] == binary_blob.container.name


# noinspection PyShadowingNames
def test_blob_generate_download_url_expiration(storage, binary_blob):
    signature = binary_blob.generate_download_url(expires=-10)

    with pytest.raises(SignatureExpiredError):
        storage.validate_signature(signature)
