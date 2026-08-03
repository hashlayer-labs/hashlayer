"""Shared validator-info / miner-score submission logic.

`ValidatorSubmissionMixin` holds the proxy-API submission behaviour that was
previously duplicated verbatim between the JSON and Redis storage backends.
The methods are unchanged; only the duplication is removed.
"""

import concurrent.futures
import os
from datetime import datetime

import aiohttp
from bittensor.utils.btlogging import logging


class ValidatorSubmissionMixin:
    """Submit validator info and miner scores to the unified database (proxy API)."""

    def _init_submission(self) -> None:
        """Initialise proxy-API config and the submission thread pool.

        Call from each storage backend's ``__init__`` after ``validator_id`` is set.
        """
        # Unified database API configuration - use environment variables directly
        self.proxy_api_url = os.getenv("SUBNET_PROXY_API_URL", "http://127.0.0.1:8888")
        self.proxy_api_token = os.getenv("SUBNET_PROXY_API_TOKEN", "")

        # Process submit_validator_info configuration, default true
        self.submit_to_db = os.getenv("SUBMIT_VALIDATOR_INFO", "true").lower() == "true"

        # Create thread pool executor for async tasks
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="db_submit"
        )

    async def _submit_validator_info(self, state: dict) -> None:
        """Submit validator information to unified database"""
        try:
            # Extract validator info from state
            validator_info = self._extract_validator_info(state)

            # Send to proxy API
            headers = {}
            if self.proxy_api_token:
                headers["Authorization"] = f"Bearer {self.proxy_api_token}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.proxy_api_url}/api/validators/submit_info",
                    json=validator_info,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        logging.info(
                            (
                                f"✅ ValidatorInformationSubmitSuccess:"
                                f"{validator_info['hotkey'][:8]}..."
                            )
                        )
                    else:
                        logging.warning(
                            f"ValidatorInformationSubmitFailure: {response.status}"
                        )

        except Exception as e:
            logging.error(f"SubmitValidatorInformationFailure: {e}")

    def _extract_validator_info(self, state: dict) -> dict:
        """Extract required information from validator state"""
        return {
            "hotkey": state.get("hotkey", ""),
            "coldkey": state.get("coldkey", ""),
            "uid": state.get("uid", 0),
            "netuid": state.get("netuid", 2),
            "current_block": state.get("current_block", 0),
            "validator_stake": state.get("validator_stake", 0.0),
            "last_update": state.get("last_update", 0),
            "scores": state.get("scores", []),
            "weights": state.get("weights", []),
            "timestamp": datetime.now().isoformat(),
            "validator_version": state.get("version", "unknown"),
            # System monitoring information
            "cpu_usage": state.get("cpu_usage", 0.0),
            "memory_usage": state.get("memory_usage", 0.0),
            "disk_usage": state.get("disk_usage", 0.0),
            "network_latency": state.get("network_latency", 0.0),
        }

    def _extract_miner_scores(self, state: dict) -> list:
        """Extract miner score information from validator state"""
        miner_scores = []

        # Get basic information
        validator_hotkey = state.get("hotkey", "")
        current_block = state.get("current_block", 0)
        scores = state.get("scores", [])
        hotkeys = state.get("hotkeys", [])
        block_at_registration = state.get("block_at_registration", [])

        # Build miner scores directly from state's basic data
        for i, hotkey in enumerate(hotkeys):
            if i < len(scores):
                miner_score = {
                    "validator_hotkey": validator_hotkey,
                    "miner_hotkey": hotkey,
                    "miner_uid": i,
                    "netuid": state.get("netuid", 2),
                    "evaluation_block": current_block,
                    "score": float(scores[i]) if scores[i] is not None else 0.0,
                    "registration_block": (
                        block_at_registration[i]
                        if i < len(block_at_registration)
                        else 0
                    ),
                    "evaluation_time": datetime.now().isoformat(),
                }
                miner_scores.append(miner_score)

        return miner_scores

    async def _submit_miner_scores(self, miner_scores: list) -> None:
        """Submit miner score information to unified database"""
        # Remove empty data check, ensure always submit (even if empty list)
        try:
            headers = {}
            if self.proxy_api_token:
                headers["Authorization"] = f"Bearer {self.proxy_api_token}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.proxy_api_url}/api/validators/submit_miner_scores",
                    json={"miner_scores": miner_scores},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status == 200:
                        logging.info(
                            f"✅ Miner score submission successful: {
                                len(miner_scores)
                            } records"
                        )
                    else:
                        logging.warning(
                            f"Miner score submission failed: {response.status}"
                        )
        except Exception as e:
            logging.error(f"Failed to submit miner scores: {e}")
