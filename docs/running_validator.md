# HashLayer Validator Setup

This guide will walk you through setting up and running a HashLayer validator on the Bittensor network.

HashLayer enables SHA256d miners (BTC) to contribute hashpower to a collective mining pool. All miners direct their hashpower to a single subnet pool, where validators evaluate and rank miners based on the **share work** they contribute (Stratum `pool_difficulty` summed over the evaluation window).

Validators are rewarded in HashLayer's subnet-specific (alpha) token on the Bittensor blockchain, which represents *stake* in the subnet. This alpha stake can be exited from the subnet by unstaking it to TAO (Bittensor's primary currency). Validators do **not** receive BTC from secondary distribution.

**How share work becomes a score (summary):** for each registered miner hotkey, the validator asks the subnet proxy for timerange metrics, converts summed `pool_difficulty` into an estimated USD share value using Bitcoin network difficulty, the current BTC block subsidy (`3.125`), and BTC price, then applies the loyalty coefficient **C** before normalizing weights for `set_weights`.

See also:

- [Introduction to HashLayer](../README.md)
- [Loyalty Coefficient](./loyalty_coefficient.md)
- [Introduction to Bittensor](https://docs.learnbittensor.org/learn/introduction)
- [Yuma Consensus](https://docs.learnbittensor.org/yuma-consensus/)
- [Emissions](https://docs.learnbittensor.org/emissions/)

> **Deployment note:** We recommend using Docker + Docker Compose for validators. This ensures your validator code is always up-to-date and simplifies deployment.

## Prerequisites

- A Bittensor wallet with coldkey and hotkey, registered on the HashLayer subnet
- Sufficient TAO stake (minimum ~0.5 TAO, recommended 5-10 TAO)
- Subnet proxy configuration (pre-configured, no setup needed)
- Docker Engine 24+ and Docker Compose

Bittensor Docs:

- [Requirements for Validation](https://docs.learnbittensor.org/validators/#requirements-for-validation)
- [Validator registration](https://docs.learnbittensor.org/validators/index.md#validator-registration)
- [Wallets, Coldkeys and Hotkeys in Bittensor](https://docs.learnbittensor.org/getting-started/wallets)

## Setup Steps

### 1. Bittensor Wallet Setup

Check your wallet, or create one if you have not already.

Bittensor Documentation: [Creating/Importing a Bittensor Wallet](https://docs.learnbittensor.org/working-with-keys)

#### List wallet
```bash
btcli wallet list
```

#### Check your wallet's balance

```bash
btcli wallet balance \
  --wallet.name <your wallet name> \
  --subtensor.network finney
```

### 2. Register on the HashLayer Subnet

Replace `NETUID` with your deployment subnet ID:

```bash
btcli subnet register \
  --netuid $NETUID \
  --wallet.name YOUR_WALLET \
  --wallet.hotkey YOUR_HOTKEY \
  --subtensor.network finney
```

### 3. Stake TAO (Required)

Validators need sufficient stake to set weights:

```bash
# Stake TAO to your validator
btcli stake add \
  --wallet.name YOUR_WALLET \
  --wallet.hotkey YOUR_HOTKEY \
  --amount 10.0 \
  --subtensor.network finney

# Check stake status
btcli wallet overview \
  --wallet.name YOUR_WALLET \
  --netuid $NETUID \
  --subtensor.network finney
```

**Stake Requirements**:
- **Minimum**: ~0.5 TAO (to meet minimum weight threshold of 0.0005 TAO)
- **Recommended**: 5-10 TAO (for stable operation)
- **Validator Permit**: May require more depending on competition

### 4. Clone Repository

```bash
git clone https://github.com/hashlayer-labs/hashlayer.git
cd hashlayer
```

### 5. Configuration

Navigate to the validator directory and create a `.env` file:

```bash
cd hashlayer/validator
cp env.example .env
nano .env
```

Update the `.env` file with your wallet information:

```env
# Bittensor Configuration
NETUID=<your_subnet_netuid>
SUBTENSOR_NETWORK=finney
BT_WALLET_NAME=your_wallet_name
BT_WALLET_HOTKEY=your_hotkey_name

# Subnet Proxy Configuration (provided by subnet maintainers)
SUBNET_PROXY_API_URL="http://your-proxy-host:8888"
SUBNET_PROXY_API_TOKEN="your_api_token"

# Optional: Database submission
SUBMIT_VALIDATOR_INFO=true
DB_SUBMIT_INTERVAL_SECONDS=300
LOGGING_LEVEL=info
```

**Note for Subnet Owner**: If you are the subnet owner, you need to additionally configure pool parameters to publish pool information to the chain. Regular validators should NOT set these:

```env
# Subnet Owner ONLY - Uncomment if you are the subnet owner
# PROXY_DOMAIN="stratum.hashlayer.ai"
# PROXY_PORT="3331"
# PROXY_HIGH_DIFF_PORT="3332"
# PROXY_API_PORT="8888"
# PROXY_USERNAME="your_pool_user"
# PROXY_PASSWORD="x"
# PROXY_API_TOKEN="your_api_token"
```

### 6. Running the Validator

#### Using Docker Compose (Recommended)

1. **Ensure Docker is installed**  
   Get more details here: https://docs.docker.com/engine/install/

2. **Ensure your wallet is accessible**  
   Make sure your Bittensor wallet is in `~/.bittensor/wallets/`

3. **Start the validator**
   ```bash
   docker compose down && docker compose pull && docker compose up -d && docker compose logs -f
   ```

4. **Verify it's running**  
   The validator should start and you should see info logs showing it's scoring miners.

## Important Parameters

- `netuid`: HashLayer subnet ID (from `NETUID` env)
- `subtensor.network`: Set to `finney` for mainnet
- `wallet.name`: Your Bittensor wallet name
- `wallet.hotkey`: Your wallet's hotkey

## Validator Evaluation Process

All honest validators follow the **same** pipeline (same proxy APIs, same loyalty config/flows):

```text
Miner shares (Stratum) → subnet proxy / ClickHouse
        ↓
GET timerange metrics (sum pool_difficulty per hotkey / hotkey.*)
        ↓
USD score = (Σ pool_diff / BTC_net_difficulty) × 3.125 × BTC_price
        ↓
effective_score = USD_score × loyalty C     (per miner coldkey)
        ↓
normalize → set_weights on chain
        ↓
residual weight (if any) → burn_uid (subnet owner)
```

1. **Fetch metrics** from the subnet proxy every evaluation interval (`eval_interval`), for every metagraph hotkey. Workers named `hotkey` or `hotkey.<rig>` are aggregated to the same miner.
2. **Score in USD** using Bitcoin network difficulty, block subsidy **3.125 BTC**, and live BTC price (CoinGecko; fallback price if the API fails).
3. **Apply loyalty coefficient C**: `effective_score = hashrate_score × C` (see [Loyalty Coefficient](./loyalty_coefficient.md)). Config and F/E7 flows come from the proxy so every validator agrees. If config/flows cannot be fetched, that round skips ×C.
4. **Set weights** each epoch (`tempo` blocks) from those effective scores. Excess budget relative to miner USD scores is burned to the subnet owner hotkey (`burn_uid`).
5. **Consensus**: Yuma Consensus uses the submitted weight vectors; miners earn Alpha from subnet emissions according to consensus weights. Validators earn Alpha/TAO from the validator emission path only — **not** from BTC secondary distribution.

This behaviour is identical in the public package (`hashlayer-labs`) and the monorepo validator under `hash/hashlayer/validator`.

## Managing Your Validator

### View Logs
```bash
docker compose logs -f
```

### Stop Validator
```bash
docker compose down
```

### Restart Validator
```bash
docker compose restart
```

### Update Validator
```bash
docker compose down
docker compose pull
docker compose up -d
```

## Monitoring

### Check Validator Status
```bash
# Check if container is running
docker compose ps

# View recent logs
docker compose logs --tail=100

# Check resource usage
docker stats hashlayer-validator
```

### Check Weights on Chain
```bash
btcli subnet metagraph \
  --netuid $NETUID \
  --subtensor.network finney
```

## Troubleshooting

**Cannot connect to subnet proxy**
- Verify the `SUBNET_PROXY_API_URL` is correct
- Check that your API token is valid
- Ensure network connectivity to the proxy

**No miner data received**
- Confirm miners are actively mining
- Check proxy logs for any issues with data collection
- Verify network connectivity between validators and the subnet proxy

**Wallet issues**
- Ensure wallet is properly created and registered
- Check that wallet path is correct (`~/.bittensor/wallets/`)
- Verify you're using the correct network (finney)
- Ensure wallet files have correct permissions (600)

**Insufficient stake error (Custom Error 1)**
- Your stake is below the minimum threshold
- Stake more TAO to your validator hotkey
- Minimum: ~0.5 TAO, Recommended: 5-10 TAO

**Docker issues**
- Ensure Docker daemon is running
- Check Docker Compose version (24+)
- Verify wallet volume mount is correct
- Check container logs for specific errors

## Rewards

Validators earn **Alpha / TAO through the Bittensor protocol only**.

### Alpha / TAO Rewards (Automatic)
- Distributed by Bittensor according to validator stake and consensus performance
- Check balance: `btcli wallet balance --wallet.name YOUR_WALLET`
- Unstake Alpha to TAO using standard Bittensor wallet flows when you want liquidity

### BTC secondary distribution — not for validators
HashLayer’s BTC secondary distribution credits **miners** (by mining share) and the **platform** (residual / buyback).  
Validators do **not** receive a BTC share, do **not** set a BTC withdrawal address for validation rewards, and have no BTC claim flow on the validator path.

Miner BTC withdrawal is documented in [Running a miner](./running_miner.md).

---

## Support

- GitHub Issues: https://github.com/hashlayer-labs/hashlayer/issues
- Documentation: https://github.com/hashlayer-labs/hashlayer/tree/main/docs
- Bittensor Discord: https://discord.com/invite/bittensor

Happy validating!
