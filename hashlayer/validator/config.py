"""Configuration and logging bootstrap for validators.

`ValidatorConfigMixin` owns everything required to turn process arguments and
environment variables into a parsed ``bittensor`` config, plus the per-wallet
logging directory setup. It is intentionally free of any chain/wallet state so
it can sit at the bottom of the validator argument chain: subclass mixins call
``super().add_args(parser)`` and ultimately land here.
"""

import argparse
import os

from bittensor import Subtensor, logging
from bittensor.core.config import Config
from bittensor_wallet import Wallet

from hashlayer.core.pool import Pool
from hashlayer.core.pricing import CoinPriceAPI
from hashlayer.validator.constants import TESTNET_NETUID
from hashlayer.validator.storage import JsonValidatorStorage, RedisValidatorStorage


class ValidatorConfigMixin:
    """Argument parsing and logging directory bootstrap."""

    def get_config(self):
        """Build the argument parser and parse it into a bittensor Config."""
        parser = argparse.ArgumentParser()
        self.add_args(parser)
        return Config(parser)

    def add_args(self, parser: argparse.ArgumentParser):
        """Register the validator's own arguments and those of its dependencies.

        This is the root of the ``add_args`` cooperative chain, so it does not
        call ``super().add_args`` — subclass mixins do that on the way down.
        """
        parser.add_argument(
            "--worker_prefix",
            required=False,
            default="",
            help="A prefix for the workers names miners will use.",
        )
        parser.add_argument(
            "--netuid",
            type=int,
            default=os.getenv("NETUID", TESTNET_NETUID),
            help="The chain subnet uid.",
        )
        parser.add_argument(
            "--eval_interval",
            type=int,
            default=25,
            help="The interval on which to run evaluation across the metagraph.",
        )
        parser.add_argument(
            "--state",
            type=str,
            choices=["restore", "fresh"],
            default="restore",
            help=(
                "Whether to restore previous validator state ('restore') or "
                "start fresh ('fresh')."
            ),
        )
        parser.add_argument(
            "--storage",
            type=str,
            choices=["json", "redis"],
            default=os.getenv("STORAGE_TYPE", "json"),
            help="Storage type to use (json or redis)",
        )

        # Dependencies that contribute their own CLI arguments.
        for provider in (
            Subtensor,
            logging,
            Wallet,
            Pool,
            CoinPriceAPI,
            JsonValidatorStorage,
            RedisValidatorStorage,
        ):
            provider.add_args(parser)

    def setup_logging_path(self) -> None:
        """Compute and create the per-wallet/per-netuid logging directory."""
        self.config.full_path = os.path.expanduser(
            "{}/{}/{}/netuid{}/{}".format(
                self.config.logging.logging_dir,
                self.config.wallet.name,
                self.config.wallet.hotkey,
                self.config.netuid,
                "validator",
            )
        )
        os.makedirs(self.config.full_path, exist_ok=True)

    def setup_logging(self) -> None:
        """Initialise the bittensor logger against the computed directory."""
        logging(config=self.config, logging_dir=self.config.full_path)
        logging.info(
            f"Running validator for subnet: {self.config.netuid} on network: "
            f"{self.config.subtensor.network} with config:\n{self.config}"
        )
