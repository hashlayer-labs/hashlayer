"""Shared constants for the HashLayer validator package."""

# sync-check: opensource probe 2026-08-10 (verify main→labs auto-sync)
# Default subnet uid used when the NETUID env var is not set.
# Production / public netuid will be announced separately — always set NETUID
# explicitly in .env for real deployments.
TESTNET_NETUID = 332

# The single coin this BTC subnet evaluates.
COIN = "bitcoin"

# Coldkeys whose scores are force-zeroed on state restore.
BAD_COLDKEYS = ["5CS96ckqKnd2snQ4rQKAvUpMh2pikRmCHb4H7TDzEt2AM9ZB"]
