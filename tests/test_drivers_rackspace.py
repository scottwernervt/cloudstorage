try:
    from http import HTTPStatus
except ImportError:
    # noinspection PyUnresolvedReferences
    from httpstatus import HTTPStatus

import pytest
import requests
from rfc6266_parser import parse_headers

from cloudstorage.drivers.rackspace import CloudFilesDriver
from cloudstorage.exceptions import CloudStorageError
from cloudstorage.exceptions import IsNotEmptyError
from cloudstorage.exceptions import NotFoundError
from cloudstorage.helpers import file_checksum
from tests.helpers import random_container_name, uri_validator
from tests.settings import *

pytestmark = pytest.mark.skipif(not bool(RACKSPACE_KEY),
                                reason='settings missing key and secret')


@pytest.fixture(scope='module')
def storage():
    driver = CloudFilesDriver(RACKSPACE_KEY, RACKSPACE_SECRET, RACKSPACE_REGION)

    yield driver

    for container in driver:  # cleanup
        if container.name.startswith(CONTAINER_PREFIX):
            for blob in container:
                try:
                    blob.delete()
                except NotFoundError:
                    # TODO: TESTS: Rackspace sometimes throws ResourceNotFound
                    pass

            container.delete()


# noinspection PyShadowingNames
def test_driver_create_container(storage):
    container_name = random_container_name()
    container = storage.create_container(container_name)
    assert container_name in storage
    assert container.name == container_name


# noinspection PyShadowingNames
def test_driver_create_container_invalid_name(storage):
    # noinspection PyTypeChecker
    with pytest.raises(CloudStorageError):
        storage.create_container('c' * 257)


# noinspection PyShadowingNames
def test_driver_get_container(storage, container):
    container_existing = storage.get_container(container.name)
    assert container_existing.name in storage
    assert container_existing == container


# noinspection PyShadowingNames
def test_driver_get_container_invalid(storage):
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
    assert container.enable_cdn()


def test_container_disable_cdn(container):
    assert container.disable_cdn()


def test_container_cdn_url(container):
    container.enable_cdn()
    cdn_url = container.cdn_url

    assert uri_validator(cdn_url)
    # container name not found in url


def test_container_generate_upload_url(container, binary_stream):
    form_post = container.generate_upload_url(blob_name='prefix_')
    assert 'url' in form_post and 'fields' in form_post
    assert uri_validator(form_post['url'])

    url = form_post['url']
    fields = form_post['fields']
    multipart_form_data = {
        'file': (BINARY_FORM_FILENAME, binary_stream, 'image/png'),
    }
    response = requests.post(url, data=fields, files=multipart_form_data)
    assert response.status_code == HTTPStatus.CREATED, response.text

    blob = container.get_blob('prefix_' + BINARY_FORM_FILENAME)
    # Option meta_data is not supported for rackspace upload url.
    assert blob.content_type == BINARY_OPTIONS['content_type']
    # Option content_disposition is not supported for rackspace upload url.


def test_container_generate_upload_url_expiration(container, text_stream):
    form_post = container.generate_upload_url(blob_name='', expires=-10)
    assert 'url' in form_post and 'fields' in form_post
    assert uri_validator(form_post['url'])

    url = form_post['url']
    fields = form_post['fields']
    multipart_form_data = {
        'file': text_stream
    }
    response = requests.post(url, data=fields, files=multipart_form_data)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.text


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
    blob = container.upload_blob(binary_stream,
                                 blob_name=BINARY_STREAM_FILENAME,
                                 **BINARY_OPTIONS)
    assert blob.name == BINARY_STREAM_FILENAME
    assert blob.checksum == BINARY_MD5_CHECKSUM


def test_blob_upload_options(container, binary_stream):
    blob = container.upload_blob(binary_stream,
                                 blob_name=BINARY_STREAM_FILENAME,
                                 **BINARY_OPTIONS)
    assert blob.name == BINARY_STREAM_FILENAME
    assert blob.checksum == BINARY_MD5_CHECKSUM
    assert blob.meta_data == BINARY_OPTIONS['meta_data']
    # TODO: Openstack Bug: Always returns "text/html; charset=UTF-8"
    # assert blob.content_type == BINARY_OPTIONS['content_type']
    assert blob.content_disposition == BINARY_OPTIONS['content_disposition']


def test_blob_delete(container, text_blob):
    text_blob.delete()
    assert text_blob not in container


def test_blob_download_path(binary_blob, temp_file):
    binary_blob.download(temp_file)
    hash_type = binary_blob.driver.hash_type
    download_hash = file_checksum(temp_file, hash_type=hash_type)
    assert download_hash.hexdigest() == BINARY_MD5_CHECKSUM


def test_blob_download_stream(binary_blob, temp_file):
    with open(temp_file, 'wb') as download_file:
        binary_blob.download(download_file)

    hash_type = binary_blob.driver.hash_type
    download_hash = file_checksum(temp_file, hash_type=hash_type)
    assert download_hash.hexdigest() == BINARY_MD5_CHECKSUM


def test_blob_cdn_url(container, binary_blob):
    container.enable_cdn()
    cdn_url = binary_blob.cdn_url

    assert uri_validator(cdn_url)
    # container name not found in url
    assert binary_blob.name in cdn_url


def test_blob_generate_download_url(binary_blob, temp_file):
    content_disposition = BINARY_OPTIONS.get('content_disposition')
    download_url = binary_blob.generate_download_url(
        content_disposition=content_disposition)
    assert uri_validator(download_url)

    response = requests.get(download_url)
    assert response.status_code == HTTPStatus.OK, response.text
    # Rackspace adds extra garbage to the header
    # 'attachment; filename=avatar-attachment.png;
    #  filename*=UTF-8\\'\\'avatar-attachment.png'
    parsed_disposition = parse_headers(response.headers['content-disposition'])
    response_disposition = '{}; filename={}'.format(
        parsed_disposition.disposition,
        parsed_disposition.filename_unsafe)
    assert response_disposition == content_disposition

    with open(temp_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=128):
            f.write(chunk)

    hash_type = binary_blob.driver.hash_type
    download_hash = file_checksum(temp_file, hash_type=hash_type)
    assert download_hash.hexdigest() == BINARY_MD5_CHECKSUM


def test_blob_generate_download_url_expiration(binary_blob):
    download_url = binary_blob.generate_download_url(expires=-10)
    assert uri_validator(download_url)

    response = requests.get(download_url)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.text
