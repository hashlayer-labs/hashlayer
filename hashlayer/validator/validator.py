#! /usr/bin/env python3

# Copyright © 2025 Latent Holdings
# Licensed under MIT

import asyncio
import logging as standard_logging
import os
import sys
import time
import traceback

import psutil
from bittensor import logging
from dotenv import load_dotenv

from hashlayer.core.constants import U16_MAX
from hashlayer.core.pool.metrics import ProxyMetrics, get_metrics_timerange
from hashlayer.core.pricing import CoinPriceAPI
from hashlayer.core.pricing.network_stats import get_current_difficulty
from hashlayer.validator.base import BaseValidator
from hashlayer.validator.constants import COIN
from hashlayer.validator.network import NetworkMonitorMixin
from hashlayer.validator.pool_setup import PoolSetupMixin
from hashlayer.validator.state import StatePersistenceMixin
from hashlayer.validator.weights import WeightsMixin

standard_logging.basicConfig(level=standard_logging.DEBUG, stream=sys.stdout)
standard_logging.getLogger("bittensor").setLevel(standard_logging.DEBUG)

# Fallback BTC price used when the price API is unavailable.
FALLBACK_BTC_PRICE = 95000.0
# Hard cap on the evaluation window to avoid oversized metric queries.
MAX_EVAL_WINDOW_SECONDS = 24 * 60 * 60
# Initial/recovery look-back window for the very first evaluation.
INITIAL_EVAL_WINDOW_SECONDS = 10 * 60


class HashLayerProxyValidator(
    WeightsMixin,
    StatePersistenceMixin,
    PoolSetupMixin,
    NetworkMonitorMixin,
    BaseValidator,
):
    """HashLayer Proxy BTC Validator.

    Composed from focused mixins:
    - PoolSetupMixin            — proxy-pool config + chain publish (add_args/setup)
    - StatePersistenceMixin     — save/restore validator state
    - WeightsMixin              — weight distribution math + set_weights
    - NetworkMonitorMixin       — ping latency self-monitoring
    - BaseValidator             — chain/wallet/metagraph lifecycle + reporting

    Evaluation (`evaluate_miner_share_value`) stays here so its module-level
    dependencies (get_metrics_timerange / get_current_difficulty / time) remain
    the patch targets used by the tests.
    """

    def __init__(self):
        super().__init__()
        self.is_subnet_owner = False
        self.pool = None
        self.pool_config = None
        self.api_config = None
        self.setup_bittensor_objects()
        self.price_api = CoinPriceAPI("coingecko", None)
        self.alpha = 0.8

        self.weights_interval = self.tempo
        if self.tempo < 50:
            self.eval_interval = max(self.config.eval_interval, self.tempo * 30)
            logging.info(
                f"⚠️ Detected small tempo({
                    self.tempo
                }), using larger eval_interval to avoid frequent queries"
            )

        logging.info(
            f"📊 IntervalConfiguration: tempo={self.tempo}, "
            f"eval_interval={self.eval_interval}blocks"
            f"({self.eval_interval * 12 / 60:.1f}minutes), "
            f"weights_interval={self.weights_interval}blocks"
            f"({self.weights_interval * 12 / 60:.1f}minutes)"
        )

        self.config.coins = [COIN]
        self.last_evaluation_timestamp = None

        self.submit_to_db = os.getenv("SUBMIT_VALIDATOR_INFO", "true").lower() == "true"
        self.submit_interval = int(os.getenv("DB_SUBMIT_INTERVAL_SECONDS", "300"))
        self.last_submit_timestamp = None

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def evaluate_miner_share_value(self) -> None:
        """Score miners by the fiat value of the shares they submitted.

        Kept as a single self-contained method (no private helpers) so the test
        suite can bind it onto a ``Mock(spec=...)`` and exercise the real logic
        while every other method stays mocked.
        """
        hotkey_to_uid = {hotkey: uid for uid, hotkey in enumerate(self.hotkeys)}
        current_time = int(time.time())

        # Resolve the evaluation window: short look-back on first run / state
        # recovery, otherwise pick up from the last evaluation (capped).
        if (
            self.last_evaluation_timestamp is None
            or self.last_evaluation_timestamp >= current_time
        ):
            start_time = current_time - INITIAL_EVAL_WINDOW_SECONDS
            logging.info(
                "First evaluation or state recovery - "
                "using last 10 minutes for testing."
            )
        else:
            start_time = self.last_evaluation_timestamp

        end_time = current_time
        if end_time - start_time > MAX_EVAL_WINDOW_SECONDS:
            start_time = end_time - MAX_EVAL_WINDOW_SECONDS
            logging.warning(
                f"Time range capped to {
                    MAX_EVAL_WINDOW_SECONDS / 3600
                } hours to prevent large query."
            )

        logging.info(
            f"Attempting API call with start_time={start_time} and end_time={end_time}"
        )

        try:
            for coin in self.config.coins:
                logging.info(f"Retrieving metrics for coin: {coin}")
                miner_metrics: list[ProxyMetrics] = get_metrics_timerange(
                    self.pool,
                    self.hotkeys,
                    self.block_at_registration,
                    start_time,
                    end_time,
                    coin,
                )

                if not miner_metrics:
                    logging.warning(
                        f"API returned an empty list of metrics for coin {coin}."
                    )
                else:
                    logging.info(
                        f"API call successful. Received {
                            len(miner_metrics)
                        } miner metrics."
                    )

                btc_price = self.price_api.get_price(coin)
                if btc_price is None or btc_price == 0:
                    btc_price = FALLBACK_BTC_PRICE
                    logging.warning(
                        (
                            f"Price API failed for {coin},"
                            f"using fallback price: ${btc_price}"
                        )
                    )
                else:
                    logging.info(f"Successfully fetched {coin} price: ${btc_price}")

                btc_difficulty = get_current_difficulty("bitcoin")
                logging.info(
                    f"Successfully fetched network difficulty: {btc_difficulty:,.0f} "
                    f"(using network difficulty for economic calculation)"
                )

                for metric in miner_metrics:
                    if metric.hotkey not in hotkey_to_uid:
                        continue

                    uid = hotkey_to_uid[metric.hotkey]
                    share_value = metric.get_share_value_fiat(btc_price, btc_difficulty)

                    if share_value > 0:
                        logging.info(
                            f"Share value: {share_value}, hotkey: {
                                metric.hotkey
                            }, uid: {uid}"
                        )
                    self.scores[uid] += share_value

                self._log_share_value_scores(coin, f"{end_time - start_time}s")

            self.last_evaluation_timestamp = current_time
            logging.info(f"Updated last_evaluation_timestamp to {current_time}")

        except Exception as e:
            logging.error(
                f"Failed to retrieve miner metrics for time range "
                f"{start_time} to {end_time}: {e}. "
                f"Keeping last_evaluation_timestamp at "
                f"{self.last_evaluation_timestamp}"
            )
            traceback.print_exc()

    # ------------------------------------------------------------------
    # Run-loop helpers
    # ------------------------------------------------------------------
    def _build_submission_state(self, current_time: int) -> dict:
        """Assemble the rich validator-info payload for the unified database."""
        return {
            "scores": self.scores,
            "hotkeys": self.hotkeys,
            "block_at_registration": self.block_at_registration,
            "current_block": self.current_block,
            "hotkey": self.wallet.hotkey.ss58_address
            if self.wallet and self.wallet.hotkey
            else "",
            "coldkey": self.wallet.coldkeypub.ss58_address
            if self.wallet and self.wallet.coldkeypub
            else "",
            "uid": self.uid if hasattr(self, "uid") else 0,
            "netuid": self.config.netuid,
            "validator_stake": self.metagraph.total_stake[self.uid].tao
            if hasattr(self, "metagraph")
            and hasattr(self, "uid")
            and self.uid < len(self.metagraph.total_stake)
            else 0.0,
            "last_update": self.last_evaluation_timestamp,
            "version": "1.0.0",
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent
            if hasattr(psutil, "disk_usage")
            else 0.0,
            "network_latency": self._measure_network_latency(),
            "timestamp": current_time,
        }

    def _maybe_submit_validator_info(self) -> None:
        """Submit validator info to the DB if enabled and the interval elapsed."""
        if not self.submit_to_db:
            return

        current_time = int(time.time())
        if (
            self.last_submit_timestamp is not None
            and current_time - self.last_submit_timestamp < self.submit_interval
        ):
            return

        logging.info("Scheduled submission of validator information to database")
        try:
            current_state = self._build_submission_state(current_time)
            asyncio.run(self.storage._submit_validator_info(current_state))
            self.last_submit_timestamp = current_time
            logging.info("ValidatorInformationSubmitSuccess")
        except Exception as e:
            logging.error(f"❌ ValidatorInformationSubmitFailure: {e}")

    def _normalized_validator_trust(self) -> float:
        """Query and normalize this validator's on-chain trust to [0, 1]."""
        validator_trust = self.subtensor.query_subtensor(
            "ValidatorTrust",
            params=[self.config.netuid],
        )
        return (
            validator_trust[self.uid] / U16_MAX if validator_trust[self.uid] > 0 else 0
        )

    def _run_sync_cycle(self) -> bool:
        """Run a single resync→evaluate→(weights)→persist cycle.

        Returns ``True`` on success, ``False`` when a failed weight submission
        should short-circuit the rest of the cycle.
        """
        self.resync_metagraph()
        self.evaluate_miner_share_value()

        blocks_since_last_weights = self.subtensor.blocks_since_last_update(
            self.config.netuid, self.uid
        )
        self._maybe_submit_validator_info()

        if blocks_since_last_weights >= self.weights_interval:
            success, err_msg = self.set_weights()
            if not success:
                logging.error(f"Failed to set weights: {err_msg}")
                return False

        self.save_state()

        next_sync_block, sync_reason = self.get_next_sync_block()
        logging.info(
            f"Block: {self.current_block} | "
            f"Next sync: {next_sync_block} | "
            f"Sync reason: {sync_reason} | "
            f"VTrust: {self._normalized_validator_trust():.2f}"
        )
        self._next_sync_block = next_sync_block
        return True

    def run(self):
        if self.config.state == "restore":
            self.restore_state_and_evaluate()
        else:
            self.resync_metagraph()

        logging.info(f"Starting validator loop, current block: {self.current_block}")
        self.ensure_validator_permit()
        self._next_sync_block = self.current_block + self.eval_interval
        logging.info(f"Next sync at block {self._next_sync_block}")

        while True:
            logging.debug(f"Entering main loop. Current block: {self.current_block}")

            try:
                if self.subtensor.wait_for_block(self._next_sync_block):
                    if not self._run_sync_cycle():
                        continue
                else:
                    logging.warning("Timeout waiting for block, retrying...")
                    continue

            except RuntimeError as e:
                logging.error(e)
                traceback.print_exc()

            except KeyboardInterrupt:
                logging.success("Keyboard interrupt detected. Exiting validator.")
                if hasattr(self, "storage") and hasattr(self.storage, "close"):
                    self.storage.close()
                exit()


def main():
    """Main entry point for the validator."""
    load_dotenv()
    logging.info("Validator script starting...")
    validator = HashLayerProxyValidator()
    validator.run()


if __name__ == "__main__":
    main()
