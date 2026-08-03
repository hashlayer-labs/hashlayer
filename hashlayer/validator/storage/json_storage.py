"""JSON-file backed validator storage."""

from typing import Optional

from bittensor.core.config import Config
from bittensor.utils.btlogging import logging

from hashlayer.core.storage import BaseJsonStorage
from hashlayer.validator.storage.submission import ValidatorSubmissionMixin


class JsonValidatorStorage(ValidatorSubmissionMixin, BaseJsonStorage):
    def __init__(self, config: Optional["Config"] = None):
        super().__init__(config)
        self.validator_id = self.generate_user_id(config)
        self._init_submission()

    def save_state(self, state: dict) -> None:
        """Save the validator state to a single JSON file."""
        prefix = f"{self.validator_id}_state"
        self.save_data(key="current", data=state, prefix=prefix)
        logging.debug(f"Saved validator state at block {state['current_block']}")
        # Submission to the unified DB is performed on the main-loop schedule
        # (see HashLayerProxyValidator.run), not at save time.

    def load_latest_state(self) -> dict:
        """Load the latest saved validator state."""
        prefix = f"{self.validator_id}_state"
        return self.load_data(key="current", prefix=prefix)

    def close(self):
        """Close thread pool executor and release resources"""
        if hasattr(self, "executor") and self.executor:
            self.executor.shutdown(wait=True)
            logging.debug("Thread pool executor has been closed")

    def __del__(self):
        """Destructor to ensure resource cleanup"""
        try:
            if hasattr(self, "executor") and self.executor:
                self.executor.shutdown(
                    wait=False
                )  # Don't wait to avoid blocking garbage collection
        except Exception:
            # Ignore exceptions in destructor to avoid affecting garbage collection
            pass
