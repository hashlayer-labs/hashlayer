"""Chain, wallet and metagraph lifecycle for validators.

`ChainStateMixin` connects the validator to the network and keeps its local
view of the metagraph (hotkeys, scores, registration blocks) in sync. It also
provides the burn-uid lookups and the block-scheduling math used by the run
loop. Behaviour mirrors the original inline ``BaseValidator`` methods.
"""

from typing import Optional

from bittensor import Subtensor, logging
from bittensor_wallet import Wallet


class ChainStateMixin:
    """Network connection plus metagraph/score bookkeeping."""

    def setup_bittensor_objects(self) -> None:
        """Build wallet/subtensor/metagraph and confirm validator registration.

        Steps: initialise the wallet, connect the subtensor, fetch the
        metagraph (falling back to the legacy API when the selective
        mechagraph call is unavailable), then resolve this validator's UID and
        seed the local score/hotkey arrays.
        """
        logging.info("Setting up Bittensor objects.")

        self.wallet = Wallet(config=self.config)
        logging.info(f"Wallet: {self.wallet}")

        self.subtensor = Subtensor(config=self.config)
        logging.info(f"Subtensor: {self.subtensor}")

        try:
            self.metagraph = self.subtensor.get_metagraph_info(self.config.netuid)
        except ValueError as e:
            if "get_selective_mechagraph" in str(e):
                logging.warning(
                    (
                        f"get_selective_mechagraph not available,"
                        f"trying alternative method: {e}"
                    )
                )
                # Fall back to the legacy metagraph API.
                self.metagraph = self.subtensor.metagraph(self.config.netuid)
            else:
                raise e
        logging.info(
            f"Metagraph: "
            f"<netuid:{self.metagraph.netuid}, "
            f"n:{len(self.metagraph.axons)}, "
            f"block:{self.metagraph.block}, "
            f"network: {self.subtensor.network}>"
        )

        if self.wallet.hotkey.ss58_address not in self.metagraph.hotkeys:
            logging.error(
                f"\nYour validator: {self.wallet}"
                f" is not registered to chain connection: {self.subtensor}"
                f"\nRun 'btcli register' and try again."
            )
            exit()

        # Each validator gets a unique identity (UID) in the network.
        self.uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
        logging.info(f"Running validator on uid: {self.uid}")

        self.current_block = self.metagraph.block
        self.hotkeys = self.metagraph.hotkeys
        self.block_at_registration = self.metagraph.block_at_registration
        self.scores = [0.0] * len(self.metagraph.total_stake)
        self.tempo = self.subtensor.tempo(self.config.netuid)

    def save_state(self) -> None:
        """Persist the minimal scoring snapshot to storage."""
        state = {
            "scores": self.scores,
            "hotkeys": self.hotkeys,
            "block_at_registration": self.block_at_registration,
            "current_block": self.current_block,
        }
        self.storage.save_state(state)
        logging.info(f"Saved validator state at block {self.current_block}")

    def resync_metagraph(self) -> None:
        """Refresh the metagraph and reconcile score arrays.

        Handles two kinds of change: hotkey replacements at existing UIDs
        (their score is reset) and metagraph growth from new registrations
        (existing scores are carried over into a larger array).
        """
        logging.info("Resyncing metagraph...")

        previous_hotkeys = self.hotkeys

        self.metagraph = self.subtensor.get_metagraph_info(self.config.netuid)
        self.current_block = self.metagraph.block

        if previous_hotkeys == self.metagraph.hotkeys:
            logging.debug("No metagraph changes detected")
            return

        logging.info("Metagraph updated, handling registrations and replacements")

        # 1. Hotkey replacements at existing UIDs reset that UID's score.
        for uid, hotkey in enumerate(previous_hotkeys):
            if (
                uid < len(self.metagraph.hotkeys)
                and hotkey != self.metagraph.hotkeys[uid]
            ):
                logging.info(
                    (
                        f"Hotkey replaced at uid {uid}: {hotkey}"
                        f"-> {self.metagraph.hotkeys[uid]}"
                    )
                )
                self.scores[uid] = 0.0

        # 2. New registrations grow the score array, preserving existing values.
        if len(previous_hotkeys) < len(self.metagraph.hotkeys):
            old_size = len(previous_hotkeys)
            new_size = len(self.metagraph.hotkeys)
            logging.info(f"Metagraph size increased from {old_size} to {new_size}")

            new_scores = [0.0] * new_size
            for i in range(min(old_size, len(self.scores))):
                new_scores[i] = self.scores[i]
            self.scores = new_scores

            for uid in range(old_size, new_size):
                logging.info(
                    f"New registration at uid {uid}: {self.metagraph.hotkeys[uid]}"
                )

        self.hotkeys = self.metagraph.hotkeys
        self.block_at_registration = self.metagraph.block_at_registration
        logging.info(f"Metagraph sync complete at block {self.current_block}")

    def get_burn_uid(self) -> Optional[int]:
        """Return the UID of the subnet owner."""
        sn_owner_hotkey = self.subtensor.query_subtensor(
            "SubnetOwnerHotkey",
            params=[self.config.netuid],
        )
        return self.metagraph.hotkeys.index(sn_owner_hotkey)

    def get_burn_hotkey(self) -> Optional[int]:
        """Return the hotkey of the subnet owner."""
        return self.subtensor.query_subtensor(
            "SubnetOwnerHotkey",
            params=[self.config.netuid],
        )

    def get_next_sync_block(self) -> tuple[int, str]:
        """Work out the next block to sync at and why.

        Returns ``(next_block, sync_reason)`` where ``sync_reason`` is either
        ``"Regular sync"`` or ``"Weights due"`` depending on whether a weights
        submission is owed before the next regular interval.
        """
        sync_reason = "Regular sync"
        next_sync = self.current_block + self.eval_interval

        blocks_since_last_weights = self.subtensor.blocks_since_last_update(
            self.config.netuid, self.uid
        )
        blocks_until_weights = self.weights_interval - blocks_since_last_weights
        next_weights_block = self.current_block + blocks_until_weights + 1

        if blocks_since_last_weights >= self.weights_interval:
            return self.current_block + 1, "Weights due"

        if next_weights_block <= next_sync:
            return next_weights_block, "Weights due"

        return next_sync, sync_reason

    def ensure_validator_permit(self) -> None:
        """Confirm the validator holds a permit (no-op on local testnet)."""
        # validator_permits = self.subtensor.query_subtensor(
        #     "ValidatorPermit",
        #     params=[self.config.netuid],
        # ).value
        # if not validator_permits[self.uid]:
        #     blocks_since_last_step = self.subtensor.query_subtensor(
        #         "BlocksSinceLastStep",
        #         block=self.current_block,
        #         params=[self.config.netuid],
        #     ).value
        #     time_to_wait = (self.tempo - blocks_since_last_step) * BLOCK_TIME + 0.1
        #     logging.error(
        #         f"Validator permit not found. Waiting {time_to_wait} seconds."
        #     )
        #     target_block = self.current_block + (self.tempo - blocks_since_last_step)
        #     self.subtensor.wait_for_block(target_block)
        logging.info("Skipping validator permit check for local testnet.")
        return
