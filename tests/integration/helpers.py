from retry import retry

from cloudstorage import Driver
from cloudstorage.exceptions import NotFoundError
from tests import settings


@retry((NotFoundError,), delay=1, backoff=2)
def cleanup_storage(storage: Driver):
    for container in storage:
        if not container.name.startswith(settings.CONTAINER_PREFIX):
            continue

        for blob in container:
            blob.delete()

        container.delete()
