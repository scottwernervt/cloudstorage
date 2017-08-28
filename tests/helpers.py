import string
from urllib.parse import urlparse

import random

from tests.settings import CONTAINER_PREFIX


def random_container_name():
    rand_chars = ''.join(random.sample(string.ascii_letters, 8)).lower()
    return '%s-%s' % (CONTAINER_PREFIX, rand_chars)


def uri_validator(uri):
    if not uri:
        return False

    try:
        result = urlparse(uri)
        return True if [result.scheme, result.netloc, result.path] else False
    except TypeError:
        return False
