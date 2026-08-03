"""Tabular logging helpers for validator scores and weights.

`ValidatorReportingMixin` groups the human-readable table renderers shared by
the validator classes. The methods are pure formatting/logging helpers driven
by validator instance state (``self.scores``, ``self.metagraph``,
``self.current_block``); the underlying calculations live elsewhere.
"""

from typing import Optional

from bittensor import logging
from tabulate import tabulate


def _grid(rows: list, headers: list) -> str:
    """Render rows as a left-aligned grid table (shared formatting)."""
    return tabulate(
        rows, headers=headers, tablefmt="grid", numalign="right", stralign="left"
    )


class ValidatorReportingMixin:
    """Logging helpers rendering scores/weights as grid tables."""

    def _build_score_table(self) -> Optional[str]:
        """Build the positive-score table sorted high-to-low, or None if empty."""
        rows = []
        for i in sorted(
            range(len(self.scores)), key=lambda s: self.scores[s], reverse=True
        ):
            if self.scores[i] > 0:
                rows.append(
                    [i, f"{self.metagraph.hotkeys[i]}", f"{self.scores[i]:.8f}"]
                )
        if not rows:
            return None
        return _grid(rows, ["UID", "Hotkey", "Score"])

    def _log_weights_and_scores(self, weights: list[float]) -> None:
        """Log per-UID weights (and their normalized percentage) as a table."""
        rows = []
        for i in sorted(range(len(weights)), key=lambda w: weights[w], reverse=True):
            if weights[i] > 0:
                rows.append(
                    [
                        i,
                        f"{self.metagraph.hotkeys[i]}",
                        f"{weights[i]:.10f}",
                        f"{weights[i] * 100:.10f}%",
                    ]
                )

        if not rows:
            logging.info(f"No miners receiving weights at Block {self.current_block}")
            return

        table = _grid(rows, ["UID", "Hotkey", "Weight", "Normalized (%)"])
        logging.info(f"Weights set at Block: {self.current_block}\n{table}")

    def _log_scores(self, coin: str, hash_price: float) -> None:
        """Log current scores, annotating the title with the hash price."""
        table = self._build_score_table()
        if table is None:
            logging.info(
                f"No active miners for {coin} (hash price: ${hash_price:.8f}) at Block {
                    self.current_block
                }"
            )
            return

        title = (
            f"Current Mining Scores - Block {self.current_block} - "
            f"{coin.upper()} (Hash Price: ${hash_price:.8f})"
        )
        logging.info(f"Scores updated at block {self.current_block}")
        logging.info(f".\n{title}\n{table}")

    def _log_share_value_scores(self, coin: str, timeframe: str) -> None:
        """Log current scores, annotating the title with the evaluation window."""
        table = self._build_score_table()
        if table is None:
            logging.info(
                f"No active miners for {coin} (timeframe: {timeframe}) at Block {
                    self.current_block
                }"
            )
            return

        title = (
            f"Current Mining Scores - Block {self.current_block} - "
            f"{coin.upper()} (Timeframe: {timeframe})"
        )
        logging.info(f"Scores updated at block {self.current_block}")
        logging.info(f".\n{title}\n{table}")
