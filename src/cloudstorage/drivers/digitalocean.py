import logging
from typing import Dict, List, Any

import boto3

from cloudstorage.drivers.amazon import S3Driver

__all__ = ["DigitalOceanSpacesDriver"]

logger = logging.getLogger(__name__)


class DigitalOceanSpacesDriver(S3Driver):
    """Driver for interacting with DigitalOcean Spaces Service.
    DigitalOcean spaces uses an S3-compatible API, this drivers extends the
    S3 driver to implement API differences.

    .. code-block:: python

        from cloudstorage.drivers.digitalocean import DigitalOceanSpacesDriver

        storage = DigitalOceanSpacesDriver(key='<my-digitalocean-access-key-id>',
                   secret='<my-digitalocean-secret-access-key>',
                   region='sfo2')
        # <Driver: S3 us-east-1>

    References:

    * `DigitalOcean Spaces API
      <https://developers.digitalocean.com/documentation/spaces/>`_

    :param key: DigitalOcean Access Key ID.
    :type key: str

    :param secret: DigitalOcean Secret Access Key.
    :type secret: str

    :param region: (optional) Region to connect to. Defaults to `sfo2`.
    :type region: str

    :param kwargs: (optional) Extra driver options.
    :type kwargs: dict
    """

    name = "DIGITALOCEANSPACES"
    hash_type = "md5"
    url = "https://www.digitalocean.com/products/spaces/"

    def __init__(
        self, key: str, secret: str = None, region: str = "sfo2", **kwargs: Dict
    ) -> None:
        super().__init__(key, secret, region, **kwargs)

    def _create_bucket_params(self, params: Dict[Any, Any]) -> Dict[Any, Any]:
        return params

    @property
    def regions(self) -> List[str]:
        """List of DigitalOcean regions that support Spaces.
        """
        return ["nyc3", "ams3", "sfo2", "sgp1", "fra1"]

    # noinspection PyUnresolvedReferences
    @property
    def s3(self) -> boto3.resources.base.ServiceResource:
        """S3 service resource.

        :return: The s3 resource instance.
        :rtype: :class:`boto3.resources.base.ServiceResource`
        """
        return self.session.resource(
            service_name="s3",
            region_name=self.region,
            endpoint_url=f"https://{self.region}.digitaloceanspaces.com",
        )

    def validate_credentials(self) -> None:
        # Not available
        pass
