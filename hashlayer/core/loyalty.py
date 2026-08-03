"""Loyalty coefficient C for miner weight = hashrate_score × C.

See docs/Loyalty_Coefficient_Mechanism.md:

    x = F / E7
    x >= 0:  C = 1 + (Cmax - 1) * (1 - exp(-x / a))
    x <  0:  C = max(0, 1 + x / d)

Parameters (cmax/a/d/…) come from proxy. Loyalty is always applied when
config + flows are available. On fetch failure, skip ×C so all failing
validators behave the same.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class LoyaltyParams:
    cmax: float = 1.5
    a: float = 1.0
    d: float = 1.5
    emission_floor_ratio: float = 0.2

    def __post_init__(self) -> None:
        if self.cmax < 1.0:
            raise ValueError("cmax must be >= 1")
        if self.a <= 0:
            raise ValueError("a must be > 0")
        if self.d <= 0:
            raise ValueError("d must be > 0")
        if self.emission_floor_ratio < 0:
            raise ValueError("emission_floor_ratio must be >= 0")


@dataclass(frozen=True)
class LoyaltyConfig:
    """Runtime config for miner score × C (always on when resolved)."""

    params: LoyaltyParams = LoyaltyParams()
    window_blocks: int = 50400
    version: int = 1


@dataclass(frozen=True)
class LoyaltySample:
    coldkey: str
    f: float
    e7: float
    e7_used: float
    x: float | None
    c: float
    cold_start: bool


def default_loyalty_config() -> LoyaltyConfig:
    """Default params used when proxy is unreachable (caller skips ×C)."""
    return LoyaltyConfig()


# Back-compat alias
def disabled_loyalty_config() -> LoyaltyConfig:
    return default_loyalty_config()


def loyalty_config_from_dict(data: Mapping[str, Any] | None) -> LoyaltyConfig:
    """Parse proxy JSON into LoyaltyConfig."""
    if not data:
        return default_loyalty_config()
    params = LoyaltyParams(
        cmax=float(data.get("cmax", 1.5)),
        a=float(data.get("a", 1.0)),
        d=float(data.get("d", 1.5)),
        emission_floor_ratio=float(data.get("emission_floor_ratio", 0.2)),
    )
    return LoyaltyConfig(
        params=params,
        window_blocks=int(data.get("window_blocks", 50400)),
        version=int(data.get("version", 1)),
    )


def compute_loyalty_coefficient(x: float, params: LoyaltyParams | None = None) -> float:
    """Map normalized flow x to coefficient C."""
    p = params or LoyaltyParams()
    if x >= 0:
        return 1.0 + (p.cmax - 1.0) * (1.0 - math.exp(-x / p.a))
    return max(0.0, 1.0 + x / p.d)


def normalize_emission(
    e7: float,
    median_e7: float,
    floor_ratio: float,
) -> float:
    """Apply small-miner emission floor: E' = max(E, median * ratio)."""
    floor = max(0.0, median_e7) * max(0.0, floor_ratio)
    return max(float(e7), floor)


def compute_x(
    f: float,
    e7: float,
    *,
    median_e7: float = 0.0,
    params: LoyaltyParams | None = None,
) -> tuple[float | None, float, bool]:
    """Return (x, e7_used, cold_start)."""
    p = params or LoyaltyParams()
    e7_used = normalize_emission(e7, median_e7, p.emission_floor_ratio)
    if e7_used <= 0:
        return None, e7_used, True
    return float(f) / e7_used, e7_used, False


def coefficient_for_flow(
    f: float,
    e7: float,
    *,
    median_e7: float = 0.0,
    params: LoyaltyParams | None = None,
) -> LoyaltySample:
    """Full F/E7 → C for one coldkey (coldkey filled by caller)."""
    p = params or LoyaltyParams()
    x, e7_used, cold_start = compute_x(f, e7, median_e7=median_e7, params=p)
    c = 1.0 if cold_start or x is None else compute_loyalty_coefficient(x, p)
    return LoyaltySample(
        coldkey="",
        f=float(f),
        e7=float(e7),
        e7_used=e7_used,
        x=x,
        c=c,
        cold_start=cold_start,
    )


def apply_loyalty_to_scores(
    scores: Sequence[float],
    coefficients: Sequence[float],
    *,
    apply: bool,
) -> list[float]:
    """Multiply scores by C when apply=True; otherwise return a copy."""
    if len(scores) != len(coefficients):
        raise ValueError(
            f"scores/coefficients length mismatch: {len(scores)} vs {len(coefficients)}"
        )
    if not apply:
        return [float(s) for s in scores]
    return [float(s) * float(c) for s, c in zip(scores, coefficients)]


class LoyaltyFlowProvider(Protocol):
    """Supplies 7d active net flow F and emission E7 per coldkey (alpha units)."""

    def get_flow_and_emission(
        self,
        coldkeys: Sequence[str],
    ) -> tuple[Mapping[str, float], Mapping[str, float], float]:
        """Return (F_by_coldkey, E7_by_coldkey, median_E7)."""


class NeutralLoyaltyFlowProvider:
    """No F/E₇ data → everyone C=1 (x=0 / cold start)."""

    def get_flow_and_emission(
        self,
        coldkeys: Sequence[str],
    ) -> tuple[Mapping[str, float], Mapping[str, float], float]:
        return {}, {}, 0.0


class DictLoyaltyFlowProvider:
    """Test/helper provider with explicit F and E7 maps."""

    def __init__(
        self,
        f_by_coldkey: Mapping[str, float] | None = None,
        e7_by_coldkey: Mapping[str, float] | None = None,
        median_e7: float = 0.0,
    ) -> None:
        self._f = dict(f_by_coldkey or {})
        self._e = dict(e7_by_coldkey or {})
        self._median = float(median_e7)

    def get_flow_and_emission(
        self,
        coldkeys: Sequence[str],
    ) -> tuple[Mapping[str, float], Mapping[str, float], float]:
        return self._f, self._e, self._median


class ProxyLoyaltyFlowProvider:
    """Fetch shared F/E₇ from proxy ``GET /api/loyalty/flows``.

    Raises on transport/HTTP errors so the weight path can leave scores
    unchanged (same consensus fallback as config fetch failure).
    """

    def __init__(self, api: Any) -> None:
        self._api = api
        self.last_meta: dict[str, Any] = {}

    def get_flow_and_emission(
        self,
        coldkeys: Sequence[str],
    ) -> tuple[Mapping[str, float], Mapping[str, float], float]:
        if not hasattr(self._api, "get_loyalty_flows"):
            raise RuntimeError("proxy API missing get_loyalty_flows")
        unique = sorted({ck for ck in coldkeys if ck})
        payload = self._api.get_loyalty_flows(coldkeys=unique or None)
        if not isinstance(payload, dict):
            raise ValueError("loyalty flows response must be an object")
        if payload.get("available") is False:
            raise RuntimeError("loyalty flows unavailable")
        f_map: dict[str, float] = {}
        e_map: dict[str, float] = {}
        for row in payload.get("flows") or []:
            if not isinstance(row, Mapping):
                continue
            ck = str(row.get("coldkey") or "")
            if not ck:
                continue
            f_map[ck] = float(row.get("f", 0.0))
            e_map[ck] = float(row.get("e7", 0.0))
        median = float(payload.get("median_e7", 0.0))
        self.last_meta = {
            "end_block": int(payload.get("end_block", 0) or 0),
            "start_block": int(payload.get("start_block", 0) or 0),
            "window_blocks": int(payload.get("window_blocks", 0) or 0),
            "netuid": int(payload.get("netuid", 0) or 0),
            "median_e7": median,
            "f_source": str(payload.get("f_source") or "unknown"),
            "as_of_ts": float(payload.get("as_of_ts", 0.0) or 0.0),
            "flow_rows": len(f_map),
            "requested_coldkeys": len(unique),
        }
        return f_map, e_map, median


def build_coefficients_for_coldkeys(
    coldkeys: Sequence[str],
    provider: LoyaltyFlowProvider,
    params: LoyaltyParams | None = None,
) -> list[LoyaltySample]:
    """Compute per-uid LoyaltySample aligned with coldkeys order."""
    p = params or LoyaltyParams()
    f_map, e_map, median_e7 = provider.get_flow_and_emission(coldkeys)
    samples: list[LoyaltySample] = []
    for ck in coldkeys:
        key = ck or ""
        sample = coefficient_for_flow(
            float(f_map.get(key, 0.0)),
            float(e_map.get(key, 0.0)),
            median_e7=median_e7,
            params=p,
        )
        samples.append(
            LoyaltySample(
                coldkey=key,
                f=sample.f,
                e7=sample.e7,
                e7_used=sample.e7_used,
                x=sample.x,
                c=sample.c,
                cold_start=sample.cold_start,
            )
        )
    return samples
