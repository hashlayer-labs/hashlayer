"""Validator state persistence (save / restore) for the proxy validator.

`StatePersistenceMixin` owns the rich save-state snapshot and the
restore-then-evaluate startup path. Behaviour is unchanged from the original
inline methods.
"""

from bittensor import logging

from hashlayer.validator.constants import BAD_COLDKEYS


class StatePersistenceMixin:
    """Persist and restore validator scoring state via the storage backend."""

    def save_state(self) -> None:
        state = {
            "scores": self.scores,
            "hotkeys": self.hotkeys,
            "block_at_registration": self.block_at_registration,
            "current_block": self.current_block,
            "last_evaluation_timestamp": self.last_evaluation_timestamp,
            "hotkey": (
                self.wallet.hotkey.ss58_address
                if self.wallet and self.wallet.hotkey
                else ""
            ),
            "coldkey": (
                self.wallet.coldkeypub.ss58_address
                if self.wallet and self.wallet.coldkeypub
                else ""
            ),
            "uid": self.uid if hasattr(self, "uid") else 0,
            "netuid": self.config.netuid,
            "validator_stake": (
                self.metagraph.total_stake[self.uid].tao
                if hasattr(self, "metagraph")
                and hasattr(self, "uid")
                and self.uid < len(self.metagraph.total_stake)
                else 0.0
            ),
            "last_update": self.last_evaluation_timestamp,
            "version": "1.0.0",
        }

        logging.info("=== Validator State Details ===")
        logging.info(f"Block: {state['current_block']}")
        logging.info(f"UID: {state['uid']}")
        logging.info(f"Netuid: {state['netuid']}")
        logging.info(
            f"Hotkey: {state['hotkey'][:8]}..."
            f"{state['hotkey'][-8:] if state['hotkey'] else 'N/A'}"
        )
        logging.info(
            f"Coldkey: {state['coldkey'][:8]}..."
            f"{state['coldkey'][-8:] if state['coldkey'] else 'N/A'}"
        )
        logging.info(f"Validator Stake: {state['validator_stake']:.4f} TAO")
        logging.info(f"Scores Count: {len(state['scores']) if state['scores'] else 0}")
        logging.info(
            f"Hotkeys Count: {len(state['hotkeys']) if state['hotkeys'] else 0}"
        )
        logging.info(f"Last Evaluation: {state['last_evaluation_timestamp']}")
        logging.info(f"Version: {state['version']}")
        logging.info("===============================")

        self.storage.save_state(state)
        logging.info(
            f"Saved validator state at block {self.current_block} with timestamp {
                self.last_evaluation_timestamp
            }"
        )

    def restore_state_and_evaluate(self) -> None:
        state = self.storage.load_latest_state()
        if state is None:
            logging.info("No previous state found, starting fresh")
            return

        blocks_down = self.current_block - state["current_block"]
        if blocks_down >= (self.tempo * 1.5):
            logging.warning(
                f"Validator was down for {blocks_down} blocks (> {
                    self.tempo * 1.5
                }). Starting fresh."
            )
            return

        total_hotkeys = len(state.get("hotkeys", []))
        self.scores = state.get("scores", [0.0] * total_hotkeys)
        self.hotkeys = state.get("hotkeys", [])
        self.block_at_registration = state.get("block_at_registration", [])
        self.last_evaluation_timestamp = state.get("last_evaluation_timestamp", None)
        self.resync_metagraph()

        for idx in range(len(self.hotkeys)):
            if self.metagraph.coldkeys[idx] in BAD_COLDKEYS:
                self.scores[idx] = 0.0

        logging.warning(f"Validator was down for {blocks_down} blocks.")
        self.evaluate_miner_share_value()

        logging.success(
            f"Successfully restored validator state with last evaluation timestamp: {
                self.last_evaluation_timestamp
            }"
        )
