"""Weight calculation and on-chain submission for the proxy validator.

Miner scores are hashrate-based. Loyalty coefficient C is always applied
when proxy config + flows are available: effective score = hashrate × C.
"""

from bittensor import logging

from hashlayer.core.bittensor_compat import extrinsic_result
from hashlayer.core.constants import (
    OWNER_TAKE,
    PAYOUT_FACTOR,
    SPLIT_WITH_MINERS,
    VERSION_KEY,
)
from hashlayer.core.loyalty import (
    LoyaltyConfig,
    NeutralLoyaltyFlowProvider,
    ProxyLoyaltyFlowProvider,
    apply_loyalty_to_scores,
    build_coefficients_for_coldkeys,
    loyalty_config_from_dict,
)


class WeightsMixin:
    """Compute miner weights from scores and submit them to the chain."""

    # Override in tests. Production auto-upgrades Neutral → Proxy when API exists.
    loyalty_flow_provider = NeutralLoyaltyFlowProvider()

    def calculate_weights_distribution(
        self,
        total_value: float,
        scores: list[float] | None = None,
    ) -> list[float]:
        score_vec = self.scores if scores is None else scores
        weights = [0.0] * len(self.hotkeys)
        tao_price = self.price_api.get_price("bittensor")
        subnet_price = self.subtensor.subnet(self.config.netuid).price.tao
        alpha_price = subnet_price * tao_price
        own_stake_weight = self.metagraph.total_stake[self.uid].tao
        total_stake = sum(self.metagraph.total_stake).tao
        blocks_to_set_for = self.current_block - self.last_update
        alpha_to_dist = (
            blocks_to_set_for
            * (1 - OWNER_TAKE)
            * SPLIT_WITH_MINERS
            * (own_stake_weight / total_stake)
        )
        value_to_dist = alpha_to_dist * alpha_price
        scaled_total_value = total_value * PAYOUT_FACTOR

        if scaled_total_value > value_to_dist:
            weights = [score / scaled_total_value for score in score_vec]
        else:
            weights_to_dist = scaled_total_value / value_to_dist
            weights = [(score / total_value) * weights_to_dist for score in score_vec]

        remaining = max(0.0, 1.0 - sum(weights))
        if remaining > 0:
            weights[self.burn_uid] += remaining
        return weights

    def _loyalty_coldkeys(self) -> list[str]:
        try:
            return list(self.metagraph.coldkeys)
        except Exception:
            return [""] * len(self.hotkeys)

    def _resolve_loyalty_config(self) -> LoyaltyConfig | None:
        """Load loyalty params from proxy only.

        Fetch failure → None (all failing validators agree: no × C this round).
        """
        api = getattr(getattr(self, "pool", None), "api", None)
        if api is not None and hasattr(api, "get_loyalty_config"):
            try:
                payload = api.get_loyalty_config()
                cfg = loyalty_config_from_dict(payload)
                logging.info(
                    "Loyalty config from proxy: "
                    f"version={cfg.version} "
                    f"cmax={cfg.params.cmax} a={cfg.params.a} d={cfg.params.d} "
                    f"emission_floor_ratio={cfg.params.emission_floor_ratio} "
                    f"window_blocks={cfg.window_blocks}"
                )
                return cfg
            except Exception as exc:
                logging.warning(
                    f"Loyalty config fetch failed, skipping ×C this round: {exc}"
                )
                return None

        logging.debug("Loyalty config: no proxy API; skipping ×C")
        return None

    def _get_loyalty_flow_provider(self):
        """Prefer explicit provider; else proxy flows; else neutral (C≈1)."""
        provider = getattr(self, "loyalty_flow_provider", None)
        if provider is not None and not isinstance(
            provider, NeutralLoyaltyFlowProvider
        ):
            return provider
        api = getattr(getattr(self, "pool", None), "api", None)
        if api is not None and hasattr(api, "get_loyalty_flows"):
            return ProxyLoyaltyFlowProvider(api)
        return provider or NeutralLoyaltyFlowProvider()

    def _log_loyalty_round(
        self,
        cfg: LoyaltyConfig,
        provider: object,
        samples: list,
        scores: list[float],
        effective: list[float],
    ) -> None:
        """Emit structured loyalty params + per-round summary for ops."""
        meta = getattr(provider, "last_meta", None) or {}
        if meta:
            logging.info(
                "Loyalty flows meta: "
                f"f_source={meta.get('f_source')} "
                f"netuid={meta.get('netuid')} "
                f"start_block={meta.get('start_block')} "
                f"end_block={meta.get('end_block')} "
                f"window_blocks={meta.get('window_blocks')} "
                f"median_e7={meta.get('median_e7')} "
                f"flow_rows={meta.get('flow_rows')} "
                f"requested_coldkeys={meta.get('requested_coldkeys')} "
                f"as_of_ts={meta.get('as_of_ts')}"
            )
        else:
            logging.info(
                "Loyalty flows meta: f_source=local/neutral (no proxy flows payload)"
            )

        n = len(samples)
        if n == 0:
            logging.info("Loyalty applied: n=0 (no samples)")
            return

        cs = [s.c for s in samples]
        cold_starts = sum(1 for s in samples if s.cold_start)
        zero_f = sum(1 for s in samples if s.f == 0.0)
        boosted = sum(1 for c in cs if c > 1.0 + 1e-9)
        penalized = sum(1 for c in cs if c < 1.0 - 1e-9)
        logging.info(
            "Loyalty params: "
            f"version={cfg.version} cmax={cfg.params.cmax} "
            f"a={cfg.params.a} d={cfg.params.d} "
            f"emission_floor_ratio={cfg.params.emission_floor_ratio} "
            f"window_blocks={cfg.window_blocks}"
        )
        logging.info(
            "Loyalty summary: "
            f"n={n} cold_start={cold_starts} f_eq_0={zero_f} "
            f"boosted={boosted} penalized={penalized} "
            f"C_min={min(cs):.4f} C_max={max(cs):.4f} "
            f"C_avg={sum(cs) / n:.4f} "
            f"score_sum_before={sum(scores):.6g} "
            f"score_sum_after={sum(effective):.6g}"
        )

        # Preview first UIDs with score before/after.
        preview_n = min(12, n)
        parts = []
        for i, s in enumerate(samples[:preview_n]):
            ck = s.coldkey or "-"
            ck_short = (ck[:8] + "…") if len(ck) > 8 else ck
            x_s = "CS" if s.x is None else f"{s.x:.4g}"
            parts.append(
                f"uid={i} ck={ck_short} "
                f"F={s.f:.4g} E={s.e7:.4g} E'={s.e7_used:.4g} "
                f"x={x_s} C={s.c:.4f} "
                f"score={scores[i]:.4g}→{effective[i]:.4g}"
            )
        logging.info("Loyalty preview: " + " | ".join(parts))

        # Highlight extreme C for ops (not full dump).
        extremes = [
            (i, s)
            for i, s in enumerate(samples)
            if s.c <= 0.25 or s.c >= cfg.params.cmax - 0.05
        ][:8]
        if extremes:
            logging.info(
                "Loyalty extremes: "
                + " | ".join(
                    f"uid={i} ck={(s.coldkey or '-')[:10]} "
                    f"F={s.f:.4g} E={s.e7:.4g} C={s.c:.4f}"
                    for i, s in extremes
                )
            )

    def _effective_scores_for_weights(self) -> list[float]:
        """Always apply loyalty coefficient C when proxy data is available."""
        cfg = self._resolve_loyalty_config()
        if cfg is None:
            logging.info("Loyalty skipped this round (no config / fetch failed)")
            return list(self.scores)

        coldkeys = self._loyalty_coldkeys()
        if len(coldkeys) != len(self.scores):
            logging.warning(
                "Loyalty skipped: coldkeys/scores length mismatch "
                f"({len(coldkeys)} vs {len(self.scores)})"
            )
            return list(self.scores)

        provider = self._get_loyalty_flow_provider()
        try:
            samples = build_coefficients_for_coldkeys(
                coldkeys,
                provider,
                params=cfg.params,
            )
        except Exception as exc:
            logging.error(f"Loyalty provider failed, leaving scores unchanged: {exc}")
            return list(self.scores)

        coefficients = [s.c for s in samples]
        effective = apply_loyalty_to_scores(
            self.scores,
            coefficients,
            apply=True,
        )
        self._log_loyalty_round(cfg, provider, samples, list(self.scores), effective)
        return effective

    def set_weights(self) -> tuple[bool, str]:
        effective_scores = self._effective_scores_for_weights()
        total_value = sum(effective_scores)
        if total_value == 0:
            logging.info("No miners are mining, we should burn the alpha")
            weights = [0.0] * len(self.hotkeys)
            weights[self.burn_uid] = 1.0
        else:
            weights = self.calculate_weights_distribution(
                total_value,
                scores=effective_scores,
            )

        return self._set_weights_direct(weights)

    def _set_weights_direct(self, weights: list[float]) -> tuple[bool, str]:
        """Submit weights directly to the chain"""
        logging.info("Using direct weight submission (commit-reveal disabled)")
        logging.info("Attempting to send set_weights transaction to Subtensor...")

        response = self.subtensor.set_weights(
            netuid=self.config.netuid,
            wallet=self.wallet,
            uids=list(range(len(self.hotkeys))),
            weights=weights,
            wait_for_inclusion=True,
            version_key=VERSION_KEY,
        )
        success, err_msg = extrinsic_result(response)

        if success:
            logging.success("Successfully set weights on the chain.")
            self._log_weights_and_scores(weights)
            self.last_update = self.current_block
            self.scores = [0.0] * len(self.hotkeys)
            return True, err_msg
        else:
            logging.error("Failed to set weights. The transaction was not successful.")
            logging.error(f"Error from subtensor: {err_msg}")
            return False, err_msg
