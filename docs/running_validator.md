# HashLayer Validator Setup

This guide will walk you through setting up and running a HashLayer validator on the Bittensor network.

HashLayer enables SHA256d miners (BTC) to contribute hashpower to a collective mining pool. All miners direct their hashpower to a single subnet pool, where validators evaluate and rank miners based on the share value they generate.

Validators are rewarded in HashLayer's subnet-specific (alpha) token on the Bittensor blockchain, which represents *stake* in the subnet. This alpha stake can be exited from the subnet by unstaking it to TAO (Bittensor's primary currency).

**Share value** is the difficulty at which the miner solved a blockhash. The higher the difficulty solved, the more incentive a miner gets during *emissions*, the process by which Bittensor periodically distributes tokens to participants based on the Yuma Consensus algorithm. In general, the higher the hashpower, the higher the share value submitted.

See also:

- [Introduction to HashLayer](../README.md)
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

1. Validators fetch miner statistics from the subnet proxy every evaluation interval
2. They calculate share values based on miner contributions (BTC SHA256d mining)
3. **Loyalty coefficient C** is applied: `effective_score = hashrate_score × C` (see [Loyalty Coefficient](./loyalty_coefficient.md))
4. Weights are set every `tempo` blocks (every epoch) from those effective scores (normalized)
5. All validators use the same proxy endpoint (and the same loyalty config/flows) for consistent evaluation

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

Validators earn two types of rewards:

### 1. Alpha / TAO Rewards (Bittensor Protocol - Automatic)
- Automatically distributed to your hotkey
- Based on your validator performance and stake
- Check balance: `btcli wallet balance --wallet.name YOUR_WALLET`

### 2. BTC Mining Revenue Share (Manual Withdrawal - Secondary Distribution)

**Important**: BTC mining rewards go through **secondary distribution**. The platform collects all mining revenue from F2Pool and redistributes it to both miners and validators based on their contributions.

#### Withdrawal Process for Validators

1. **Login to HashLayer Website**
   - Visit the HashLayer platform: https://hashlayer.online/
   - Connect using your Bittensor coldkey wallet (use the same coldkey that corresponds to your validator hotkey)
   - Ensure you're using the correct validator wallet

2. **Set Withdrawal Address**
   - Navigate to account settings or wallet management
   - Add your BTC address (starts with `1`, `3`, or `bc1`)
   - **Verify addresses carefully** to avoid loss of funds

3. **View Your Balance**
   - Check your accumulated BTC earnings from validation
   - View distribution history
   - Monitor pending withdrawals

4. **Submit Withdrawal Request**
   - Select BTC
   - Enter withdrawal amount (minimum per `MIN_CLAIM_BTC` deployment config)
   - Review withdrawal address and network fees
   - Submit withdrawal request (creates a withdrawal ticket)
   - Wait for processing: 1-3 business days

**Important Notes**:
- Mining rewards are collected by the platform and redistributed (secondary distribution)
- **Both validators and miners** must set withdrawal addresses on the website
- Withdrawals require manual submission, not automatic
- Large withdrawals may require additional verification
- First withdrawal may take longer for security review
- Keep transaction records for your reference

## Support

- GitHub Issues: https://github.com/hashlayer-labs/hashlayer/issues
- Bittensor Discord: HashLayer subnet channel

Happy validating!
