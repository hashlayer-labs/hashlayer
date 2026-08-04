<div align="center">

# **HashLayer** ![BTC Subnet](https://img.shields.io/badge/Algorithm-SHA256d-orange)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Bittensor](https://img.shields.io/badge/bittensor-10.5.0-blue.svg)](https://github.com/opentensor/bittensor)

</div>

## Introduction

Bittensor is a decentralized platform that incentivizes production of best-in-class digital commodities. HashLayer is a Bittensor subnet designed around production of proof-of-work (PoW) mining hashrate for the **SHA256d algorithm (BTC)**.

It is possible to contribute as a **miner** or a **validator**.

**Miners** contribute SHA256d (BTC) mining hashrate and earn rewards through two independent systems:
1. **Mining Rewards (BTC)**: Upstream mining revenue is secondarily distributed to **miners** (by share) and the **platform** (residual / buyback). Validators do **not** receive BTC from this path.
2. **Alpha tokens**: Subnet-specific tokens for Bittensor-registered miners, based on hashpower contribution and validator weights

**Validators** evaluate miners and set on-chain weights (including the loyalty coefficient). Validators earn **Alpha / TAO via the Bittensor protocol only** — they do **not** receive BTC from secondary distribution.

**Related Bittensor Documentation**:
- [Introduction to Bittensor](https://docs.learnbittensor.org/learn/introduction)
- [Mining in Bittensor](https://docs.learnbittensor.org/miners/)
- [Frequently asked questions (FAQ)](https://docs-git-permissions-list-bittensor.vercel.app/questions-and-answers)

**Page Contents**:
- [Reward System](#reward-system)
- [Requirements](#requirements)
  - [Miner Requirements](#miner-requirements)
  - [Validator Requirements](#validator-requirements)
- [Installation](#installation)
  - [Common Setup](#common-setup)
  - [Miner Specific Setup](#miner-specific-setup)
  - [Validator Specific Setup](#validator-specific-setup)
- [Subnet Information](#subnet-information)

---

# Reward System

HashLayer separates BTC mining payouts from Bittensor Alpha emissions:

## 1. Mining Rewards (BTC) — miners + platform (not validators)
SHA256d mining revenue with **secondary distribution**:
- **Mining Revenue**: BTC from contributing hashpower
- **Platform Collection**: Upstream pool revenue is collected by the platform
- **Secondary Distribution**: Net BTC is split between **registered miners** (default ~90% of net, by share contribution) and the **platform** (residual, e.g. buyback). **Validators are not in this split.**
- **Manual Withdrawal (miners)**: Miners log in to the HashLayer website, set a BTC withdrawal address, and submit claims
- **Processing Time**: Typically 1-3 business days after a claim is submitted

## 2. Alpha Token Rewards (Bittensor)
- **Miners (registered)**: Alpha from subnet emissions according to validator weights (`hashrate_score × loyalty C`, then normalized)
- **Validators**: Alpha / TAO from the Bittensor validator emission path (stake / consensus) — **no BTC secondary-distribution share**
- Alpha can be unstaked to TAO per Bittensor rules

---

# Requirements

## Miner Requirements

To run a miner with HashLayer rewards, you will need:

- A Bittensor wallet with coldkey and hotkey (for Alpha rewards)
- SHA256d (BTC) mining hardware (ASICs) OR access to remote hashrate
- Python 3.9 or higher
- The most recent release of [Bittensor SDK](https://pypi.org/project/bittensor/)

**Related Bittensor Documentation**:
- [Wallets, Coldkeys and Hotkeys in Bittensor](https://docs.learnbittensor.org/getting-started/wallets)
- [Miner registration](https://docs.learnbittensor.org/miners/index.md#miner-registration)

## Validator Requirements

To run a HashLayer validator, you will need:

- A Bittensor wallet with coldkey and hotkey
- Subnet proxy credentials (provided by subnet maintainers)
- Sufficient TAO stake (minimum ~0.5 TAO, recommended 5-10 TAO)
- Python 3.9 or higher environment
- The most recent release of [Bittensor SDK](https://pypi.org/project/bittensor/)
- Docker & Docker Compose (for containerized deployment)

**Related Bittensor Documentation**:
- [Wallets, Coldkeys and Hotkeys in Bittensor](https://docs.learnbittensor.org/getting-started/wallets)
- [Validator registration](https://docs.learnbittensor.org/validators/index.md#validator-registration)

---

# Installation

## Common Setup

These steps apply to both miners and validators:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/hashlayer-labs/hashlayer.git
   cd hashlayer
   ```

2. **Set up and activate a Python virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Upgrade pip:**
   ```bash
   pip install --upgrade pip
   ```

4. **Install the HashLayer package:**
   ```bash
   pip install -e .
   ```

---

## Miner Specific Setup

After completing the common setup:

### 1. Create a Bittensor Wallet

```bash
# Create coldkey (stores your funds)
btcli wallet new_coldkey --wallet.name my_miner

# Create hotkey (used for mining operations)
btcli wallet new_hotkey --wallet.name my_miner --wallet.hotkey default
```

### 2. Register to the HashLayer Subnet

Replace `NETUID` with the subnet ID from your deployment environment (see [Subnet Information](#subnet-information)):

```bash
# Production (Finney mainnet)
btcli subnet register \
  --wallet.name my_miner \
  --wallet.hotkey default \
  --netuid $NETUID \
  --subtensor.network finney
```

### 3. Connect Your Mining Hardware

Use your **48-character hotkey** as the miner username to connect to the mining pool:

**Production Environment (Mainnet)**:
- Pool: `stratum+tcp://stratum.hashlayer.ai:3331`
- Username: `5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY` (your full hotkey)
- Password: `x`

Alternatively, use the `{btc_address}.{hotkey}` worker format if your deployment requires a BTC payout address in the worker name.

### 4. Start Mining

Once connected, your mining hardware will:
- Automatically contribute hashrate to the pool
- Have contributions recorded by validators
- Earn Alpha rewards sent to your hotkey (if registered on Bittensor)
- Accumulate BTC rewards for withdrawal via secondary distribution

### 5. Monitor Your Rewards

**Alpha / TAO Rewards** (automatic, requires Bittensor registration):
```bash
btcli wallet balance --wallet.name my_miner
```

**BTC Rewards** (manual withdrawal):
1. Login to HashLayer website with your Bittensor wallet
2. Set your BTC withdrawal address
3. View earnings and request withdrawals
4. Processing time: 1-3 business days

**For complete step-by-step instructions**, see the [Miner Setup Guide](./docs/running_miner.md).

---

## Validator Specific Setup

After completing the common setup:

### 1. Create a Bittensor Wallet

```bash
# Create coldkey (stores your funds)
btcli wallet new_coldkey --wallet.name my_validator

# Create hotkey (used for validator operations)
btcli wallet new_hotkey --wallet.name my_validator --wallet.hotkey default
```

### 2. Register to the HashLayer Subnet

```bash
# Production (Finney mainnet)
btcli subnet register \
  --wallet.name my_validator \
  --wallet.hotkey default \
  --netuid $NETUID \
  --subtensor.network finney
```

### 3. Stake TAO (Required)

Validators need sufficient stake to set weights:

```bash
# Stake TAO to your validator
btcli stake add \
  --wallet.name my_validator \
  --wallet.hotkey default \
  --amount 10.0 \
  --subtensor.network finney

# Check stake status
btcli wallet overview \
  --wallet.name my_validator \
  --netuid $NETUID \
  --subtensor.network finney
```

**Stake Requirements**:
- Minimum: ~0.5 TAO (to meet minimum weight threshold)
- Recommended: 5-10 TAO (for stable operation)
- Validator Permit: May require more depending on competition

### 4. Clone Repository

```bash
# Clone the repository
git clone https://github.com/hashlayer-labs/hashlayer.git
cd hashlayer
```

### 5. Configure Environment

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

### 6. Run Validator

**Using Docker Compose (Recommended)**:

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

**Common Commands**:

```bash
# View logs
docker compose logs -f

# Stop validator
docker compose down
```

**For complete step-by-step instructions**, see the [Validator Setup Guide](./docs/running_validator.md).


---

## 🏗️ Architecture

```
┌─────────────┐
│   Miners    │ ← BTC ASICs / mining software
└──────┬──────┘
       │ Submit work & metrics
       ↓
┌─────────────────┐
│ HashLayer Proxy │ ← Metrics aggregation (F2Pool BTC upstream)
└──────┬──────────┘
       │ Query metrics
       ↓
┌─────────────┐
│ Validators  │ ← Calculate weights (share value)
└──────┬──────┘
       │ Set weights
       ↓
┌──────────────────┐
│ Bittensor Chain  │ ← Alpha rewards
└──────────────────┘
```

### Components

#### Core Module (`hashlayer/core`)
- **Constants**: Network and protocol constants
- **Storage**: Pluggable storage backends (JSON, Redis)
- **Pricing**: Cryptocurrency price APIs (BTC)
- **Chain Data**: Blockchain data processing
- **Utils**: Common utilities
- **Loyalty**: Coefficient C helpers used when submitting weights

#### Validator Module (`hashlayer/validator`)
- **Validator**: Main validator logic
- **Storage**: State persistence
- **Connection Manager**: Subtensor connection handling
- **Metrics**: Performance tracking

> **Note:** Miners do not run a Python process from this repository. Point ASIC /
> mining software at the HashLayer stratum endpoint using your Bittensor hotkey
> as the username (see [Miner Setup Guide](./docs/running_miner.md)).

---

## 📚 Documentation

### Complete Guides
- [Miner Setup Guide](./docs/running_miner.md) - Complete guide for setting up and running a HashLayer miner
- [Validator Setup Guide](./docs/running_validator.md) - Complete guide for setting up and running a HashLayer validator
- [Loyalty Coefficient](./docs/loyalty_coefficient.md) - How C adjusts validator weights (`score × C`)

---

# Subnet Information

## Production Environment (Finney Mainnet)
- **Subnet ID (netuid)**: To be announced — set `NETUID` in your validator `.env` when assigned
- **Network**: Finney (mainnet)
- **Network Parameter**: `--subtensor.network finney`
- **Algorithm**: SHA256d (BTC)
- **Upstream Pool**: F2Pool BTC (`btc.f2pool.com`)
- **Pool Address**: `stratum+tcp://stratum.hashlayer.ai:3331`
- **Emission**: Dynamic based on contribution

---

## ⚠️ Disclaimer

This software is provided "as is" without warranty of any kind. Use at your own risk.

- Mining involves financial risk
- Always secure your wallets
- Verify all transactions
- Do your own research

---

# Get Involved

- Join the discussion on the [Bittensor Discord](https://discord.com/invite/bittensor).
- Check out the [Bittensor Documentation](https://docs.learnbittensor.org/) for general information about running subnets and nodes.

---

**Full Guides:**
- [HashLayer Miner Setup Guide](docs/running_miner.md)
- [HashLayer Validator Setup Guide](docs/running_validator.md)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
