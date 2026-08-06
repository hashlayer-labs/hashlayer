"""
Proxy pool metrics implementation for time-based queries.
"""

from dataclasses import dataclass

from hashlayer.core.pool.proxy.pool import ProxyPool

from .base import BaseMetrics

# Current BTC subsidy per block (post-2024 halving).
# Same as TaoHash BLOCK_REWARDS["btc"].
# Scales share work → estimated BTC → USD for weight vs alpha-budget burn logic.
BTC_BLOCK_REWARD = 3.125


@dataclass
class ProxyMetrics(BaseMetrics):
    """
    Mining Metrics for Proxy pool.
    Contains data about the miner's hashrate and shares for a specific time range.
    """

    hashrate: float = 0.0
    shares: int = 0
    share_value: float = 0.0

    def get_share_value_fiat(self, coin_price: float, coin_difficulty: float) -> float:
        """
        Returns the share value for this time period in USD (BTC SHA256d).

        Args:
            coin_price: Current BTC price in USD
            coin_difficulty: Current Bitcoin network difficulty

        Returns:
            float: Share value in USD
        """
        import logging
        import os

        dev_reward_factor = float(os.getenv("DEV_REWARD_FACTOR", "1.0"))

        logging.info(
            f"get_share_value_fiat - coin_price={coin_price}, "
            f"coin_difficulty={coin_difficulty}, share_value={self.share_value}"
        )

        if self.share_value:
            base_value = (
                (self.share_value / coin_difficulty) * BTC_BLOCK_REWARD * coin_price
            )
            calculated_value = base_value * dev_reward_factor
            logging.info(f"get_share_value_fiat - base_value={base_value:.8f}")
            return calculated_value

        logging.warning("get_share_value_fiat - share_value is 0 or None")
        return 0.0


def get_metrics_timerange(
    pool: ProxyPool,
    hotkeys: list[str],
    block_at_registration: list[int],
    start_time: int,
    end_time: int,
    coin: str = "bitcoin",
) -> list[ProxyMetrics]:
    """
    Retrieves mining metrics for all miners for a specific time range.
    """
    metrics = []
    all_workers = pool.get_miner_contributions_timerange(start_time, end_time, coin)

    import logging

    logging.info(f"Retrieved {len(all_workers)} workers from pool API")
    if all_workers:
        sample_keys = list(all_workers.keys())[:3]
        logging.info(f"Sample worker IDs: {sample_keys}")

    hotkeys_to_workers = {}
    worker_ids_to_hotkey_idx = {}

    for i, hotkey in enumerate(hotkeys):
        worker_ids = []

        if hotkey in all_workers:
            worker_ids.append(hotkey)
            logging.debug(f"Found worker using full hotkey: {hotkey}")

        for worker_id in all_workers.keys():
            if "." in worker_id:
                worker_hotkey = worker_id.split(".")[0]
                if worker_hotkey == hotkey:
                    worker_ids.append(worker_id)
                    logging.info(
                        f"Found worker with suffix: {worker_id} matches hotkey: "
                        f"{hotkey[:8]}...{hotkey[-8:]}"
                    )

        if len(worker_ids) > 1:
            logging.info(
                f"Found {len(worker_ids)} workers for hotkey {hotkey[:8]}..., "
                "will aggregate their data"
            )
            hotkeys_to_workers[hotkey] = worker_ids
        elif len(worker_ids) == 1:
            worker_id = worker_ids[0]
            if worker_id in worker_ids_to_hotkey_idx:
                other_hotkey_idx = worker_ids_to_hotkey_idx[worker_id]
                if block_at_registration[i] < block_at_registration[other_hotkey_idx]:
                    other_hotkey = hotkeys[other_hotkey_idx]
                    if other_hotkey in hotkeys_to_workers:
                        del hotkeys_to_workers[other_hotkey]
                    worker_ids_to_hotkey_idx[worker_id] = i
                    hotkeys_to_workers[hotkey] = [worker_id]
            else:
                worker_ids_to_hotkey_idx[worker_id] = i
                hotkeys_to_workers[hotkey] = [worker_id]

    for hotkey in hotkeys:
        worker_ids = hotkeys_to_workers.get(hotkey)

        if worker_ids is None:
            metrics.append(ProxyMetrics(hotkey=hotkey))
            continue

        total_share_value = 0.0
        total_hashrate = 0.0
        total_shares = 0
        hash_rate_unit = "Gh/s"

        for worker_id in worker_ids:
            worker_data = all_workers.get(worker_id, {})
            if worker_data:
                total_share_value += worker_data.get("share_value", 0.0)
                total_hashrate += worker_data.get("hashrate", 0.0)
                total_shares += worker_data.get("shares", 0)
                hash_rate_unit = worker_data.get("hash_rate_unit", "Gh/s")
            else:
                logging.warning(
                    f"No worker data for hotkey {hotkey[:8]}..., worker_id {worker_id}"
                )

        metrics.append(
            ProxyMetrics(
                hotkey=hotkey,
                hashrate=total_hashrate,
                shares=total_shares,
                share_value=total_share_value,
                hash_rate_unit=hash_rate_unit,
            )
        )

    return metrics
