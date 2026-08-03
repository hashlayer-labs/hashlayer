"""Subnet-owner pool configuration and chain setup for the proxy validator.

`PoolSetupMixin` extends the base bittensor object setup with the proxy-pool
specifics: it registers proxy-pool CLI args, configures the pool (owner) or
the proxy API client (non-owner), and publishes pool info to the chain.
Behaviour is unchanged from the original inline methods.
"""

import argparse
import os

from bittensor import Subtensor, logging
from bittensor_wallet.bittensor_wallet import Wallet

from hashlayer.core.chain_data.pool_info import (
    encode_pool_info,
    get_pool_info,
    publish_pool_info,
)
from hashlayer.core.pool import Pool, PoolBase
from hashlayer.core.pool.proxy import ProxyPool, ProxyPoolAPI
from hashlayer.core.pool.proxy.config import ProxyPoolAPIConfig, ProxyPoolConfig


class PoolSetupMixin:
    """Pool/proxy configuration layered on top of the base chain setup."""

    def add_args(self, parser: argparse.ArgumentParser):
        super().add_args(parser)
        ProxyPoolConfig.add_args(parser)
        ProxyPoolAPIConfig.add_args(parser)

    def setup_bittensor_objects(self):
        super().setup_bittensor_objects()
        self.burn_uid = self.get_burn_uid()
        self.burn_hotkey = self.get_burn_hotkey()
        self.is_subnet_owner = self.burn_hotkey == self.wallet.hotkey.ss58_address

        if self.is_subnet_owner:
            logging.info("SN owner detected - setting up pool configuration")
            try:
                self.pool_config = ProxyPoolConfig.from_args(self.config)
                self.api_config = ProxyPoolAPIConfig.from_args(self.config)
                self.pool = Pool(
                    pool_info=self.pool_config.to_pool_info(), config=self.api_config
                )
                self.publish_pool_info(
                    self.subtensor, self.config.netuid, self.wallet, self.pool
                )
                logging.info(
                    (
                        f"Pool configured with domain/IP:"
                        f"{self.pool.get_pool_info().domain}"
                    )
                )
            except Exception as e:
                logging.error(
                    f"Subnet owner must provide pool configuration via command line "
                    f"(--pool.domain, --pool.port) or environment variables "
                    f"(PROXY_DOMAIN, PROXY_PORT). Error: {e}"
                )
                exit(1)
        else:
            proxy_url = os.getenv("SUBNET_PROXY_API_URL")
            api_token = os.getenv("SUBNET_PROXY_API_TOKEN")

            if not proxy_url:
                raise ValueError(
                    "SUBNET_PROXY_API_URL environment variable must be set"
                )
            if not api_token:
                raise ValueError(
                    "SUBNET_PROXY_API_TOKEN environment variable must be set"
                )

            api = ProxyPoolAPI(proxy_url=proxy_url, api_token=api_token)
            self.pool = ProxyPool(pool_info=None, api=api)

    def publish_pool_info(
        self, subtensor: "Subtensor", netuid: int, wallet: "Wallet", pool: PoolBase
    ) -> None:
        pool_info = pool.get_pool_info()
        pool_info_bytes = encode_pool_info(pool_info)
        published_pool_info = get_pool_info(
            subtensor, netuid, wallet.hotkey.ss58_address
        )

        if published_pool_info is not None:
            logging.info("Pool info detected.")
            published_pool_info_bytes = encode_pool_info(published_pool_info)
            if published_pool_info_bytes == pool_info_bytes:
                logging.success("Pool info is already published.")
                return
            else:
                logging.info("Pool info is outdated.")

        logging.info("Publishing pool info to the chain.")
        success = publish_pool_info(subtensor, netuid, wallet, pool_info_bytes)
        if not success:
            logging.error("Failed to publish pool info")
            exit(1)
        else:
            logging.success("Pool info published successfully")
