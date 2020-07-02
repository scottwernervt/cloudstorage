from cloudstorage import DriverName, get_driver, get_driver_by_name
from cloudstorage.base import Driver


def test_get_driver():
    for provider in DriverName:
        driver = get_driver(provider)
        assert driver.name == provider.name
        assert issubclass(driver, Driver)


def test_get_driver_by_name():
    for provider in DriverName:
        driver = get_driver_by_name(driver_name=provider.name)
        assert driver.name == provider.name
        assert issubclass(driver, Driver)
