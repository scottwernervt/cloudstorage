"""Cloud Storage

:copyright: (c) 2017 by Scott Werner.
:license: MIT, see LICENSE for more details.
"""

import logging
from enum import Enum, unique
from typing import Union

from cloudstorage.base import Blob, Container, Driver
from cloudstorage.exceptions import CloudStorageError

__all__ = [
    'Driver',
    'Container',
    'Blob',
    'DriverName'
    'get_driver',
    'get_driver_by_name',
]

__title__ = 'Cloud Storage'
__version__ = '0.2'
__author__ = 'Scott Werner'
__license__ = 'MIT'
__copyright__ = 'Copyright 2017 Scott Werner'

Drivers = Union[
    'S3Driver',
    'GoogleStorageDriver',
    'LocalDriver',
    'CloudFilesDriver',
]


@unique
class DriverName(Enum):
    """DriverName enumeration."""
    LOCAL = 'LOCAL'
    S3 = 'S3'
    CLOUDFILES = 'CLOUDFILES'
    GOOGLESTORAGE = 'GOOGLESTORAGE'


_DRIVER_IMPORTS = {
    DriverName.S3: ('cloudstorage.drivers.amazon', 'S3Driver'),
    DriverName.GOOGLESTORAGE: ('cloudstorage.drivers.google',
                               'GoogleStorageDriver'),
    DriverName.LOCAL: ('cloudstorage.drivers.local', 'LocalDriver'),
    DriverName.CLOUDFILES: (
        'cloudstorage.drivers.rackspace', 'CloudFilesDriver'),
}


def get_driver(driver: DriverName) -> Drivers:
    """Get driver class by DriverName enumeration member.

    .. code-block:: python
        
        >>> from cloudstorage import DriverName, get_driver
        >>> driver_cls = get_driver(DriverName.LOCAL)
        <class 'cloudstorage.drivers.local.LocalDriver'>

    :param driver: DriverName member.
    :type driver: :class:`.DriverName`

    :return: DriverName driver class.
    :rtype: :class:`.CloudDriver`
    """
    if driver in _DRIVER_IMPORTS:
        mod_name, driver_name = _DRIVER_IMPORTS[driver]
        _mod = __import__(mod_name, globals(), locals(), [driver_name])
        return getattr(_mod, driver_name)

    raise CloudStorageError("Driver '%s' does not exist." % driver)


def get_driver_by_name(driver_name: str) -> Drivers:
    """Get driver class by driver name.

    .. code-block:: python
        
        >>> from cloudstorage import get_driver_by_name
        >>> driver_cls = get_driver_by_name('LOCAL')
        <class 'cloudstorage.drivers.local.LocalDriver'>

    :param driver_name: Driver name.
    
        * `LOCAL`
        * `S3`
        * `CLOUDFILES`
        * `GOOGLESTORAGE`
    :type driver_name: str

    :return: DriverName driver class.
    :rtype: :class:`.CloudDriver`
    """
    driver = DriverName[driver_name]
    return get_driver(driver)


# Set up logging to ``/dev/null`` like a library is supposed to.
logging.getLogger('cloudstorage').addHandler(logging.NullHandler())
