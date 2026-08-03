# Loyalty Coefficient (Validator Weights)

HashLayer adjusts miner **weights** with a loyalty coefficient **C** before
validators call `set_weights` on chain.

```text
effective_score = hashrate_score × C
weights         = normalize(effective_scores)   # then submit
```

This does **not** change the Bittensor runtime. It only changes the weight vector
validators submit. Hashrate remains the primary signal: **zero hashrate still
yields zero weight**, even if C is high.

## Behaviour summary

| Miner behaviour (≈7d window) | C | Effect on weight |
|------------------------------|---|------------------|
| Hold (no active buy/sell) | ≈ 1 | Neutral |
| Net buy / restake into this subnet | > 1 (capped at `Cmax`) | Mild boost |
| Net sell / unstake / transfer out | < 1 (can reach 0) | Discount |

## How C is computed

Reinvestment rate:

```text
x = F / E7
```

| Symbol | Meaning |
|--------|---------|
| **F** | Active net alpha stake inflow for the miner’s **coldkey** on this subnet over the rolling window (≈7 days). Approximated from stake snapshots: `F ≈ (S_end − S_start) − E7`. Auto-emissions are **not** counted as active inflow. |
| **E7** | Alpha emissions that coldkey received in the **same** window. |
| **x** | Reinvestment rate |

Default curve (proxy-configurable):

```text
x ≥ 0:  C = 1 + (Cmax − 1) · (1 − e^(−x / a))
x <  0:  C = max(0, 1 + x / d)

defaults: Cmax = 1.5, a = 1, d = 1.5
```

Cold start (`E7 = 0` in the observed window) → `C = 1`.  
Very small miners use an emission floor so tiny buys cannot max out C.

## Validator data path

Every weight round, the validator:

1. Pulls shared loyalty **config** from the subnet proxy (`/api/loyalty/config`)
2. Pulls shared **F / E7** flows (`/api/loyalty/flows`)
3. Computes per-coldkey **C**
4. Multiplies hashrate scores by C
5. Normalizes and submits weights

If config or flows cannot be fetched, that round **skips** ×C (all validators that fail the same way stay consistent). Do **not** hard-code loyalty parameters in local env files — they are owned by the proxy so every validator uses the same values.

## What to watch in logs

Successful rounds log loyalty params and a short per-round summary (applied / skipped).  
If you see “skipping ×C”, check proxy reachability and `SUBNET_PROXY_API_*` credentials.

## Observing distribution

Weights are **relative**. With a single miner receiving weight, changing C does not change their share of the miner emission pool (still 100% after normalization). To verify C affects payouts, compare **multiple miners** with different C (ideally similar hashrate scores).

## Related

- [Validator setup](./running_validator.md)
- Code: `hashlayer/core/loyalty.py`, `hashlayer/validator/weights.py`
