import random
import string
import time

from functools import wraps
from urllib.parse import urlparse

from minio.error import NoSuchBucket
from retry import retry

from cloudstorage import Driver
from cloudstorage.exceptions import NotFoundError
from tests import settings


@retry((NotFoundError, NoSuchBucket), delay=1, backoff=2)
def cleanup_storage(storage: Driver):
    for container in storage:
        if not container.name.startswith(settings.CONTAINER_PREFIX):
            continue

        for blob in container:
            blob.delete()

        container.delete()


def random_container_name() -> str:
    rand_chars = "".join(random.sample(string.ascii_letters, 8)).lower()
    return "%s-%s" % (settings.CONTAINER_PREFIX, rand_chars)


def uri_validator(uri: string) -> bool:
    if not uri:
        return False

    try:
        result = urlparse(uri)
        return True if [result.scheme, result.netloc, result.path] else False
    except TypeError:
        return False


def rate_limited(delay: int = 1):
    """Rate-limits the decorated function."""

    def decorate(func):
        @wraps(func)
        def rate_limited_function(*args, **kwargs):
            time.sleep(delay)
            return func(*args, **kwargs)

        return rate_limited_function

    return decorate
