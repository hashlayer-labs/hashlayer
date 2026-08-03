"""Redis backed validator storage."""

from typing import Optional

from bittensor.core.config import Config

from hashlayer.core.storage import BaseRedisStorage
from hashlayer.validator.storage.submission import ValidatorSubmissionMixin


class RedisValidatorStorage(ValidatorSubmissionMixin, BaseRedisStorage):
    def __init__(self, config: Optional["Config"] = None):
        super().__init__(config)
        self.validator_id = self.generate_user_id(config)
        self._init_submission()

    def save_state(self, state: dict) -> None:
        """Save the validator state to Redis."""
        prefix = f"{self.validator_id}_state"
        self.save_data(key="current", data=state, prefix=prefix)
        # Submission to the unified DB is performed on the main-loop schedule
        # (see HashLayerProxyValidator.run), not at save time.

    def load_latest_state(self) -> dict:
        """Get validator state for specific block."""
        prefix = f"{self.validator_id}_state"
        return self.load_data(key="current", prefix=prefix)
