# HashLayer Mining Guide

This guide will walk you through setting up and running a HashLayer miner on the Bittensor network.

HashLayer enables SHA256d miners (BTC) to contribute hashpower to a collective mining pool. All miners direct their hashpower to a single subnet pool, where validators evaluate and rank miners based on the share value they generate.

HashLayer miners earn from **two independent reward systems**, both designed to fairly and transparently compensate you for your computational contributions.

## Reward Systems

### 1. Mining Rewards (BTC) - All Miners

Direct cryptocurrency earnings from actual SHA256d (BTC) mining with **secondary distribution**:

- **Mining Revenue**: Earn BTC from contributing hashpower
- **Platform Collection**: All mining rewards are first collected by the platform
- **Secondary Distribution**: Platform redistributes rewards to miners and validators based on contributions
- **Manual Withdrawal Required**: Must login to HashLayer website to set your BTC withdrawal address and submit withdrawal requests
- **Processing Time**: 1-3 business days for withdrawal processing

#### How It Works
1. Connect your mining hardware to the HashLayer pool
2. Your shares are recorded and validated
3. Mining revenue (BTC) is collected by the platform from F2Pool
4. Platform performs **secondary distribution** to miners and validators based on their contributions
5. You must login to HashLayer website to set your BTC withdrawal address
6. Submit withdrawal request to receive your earnings
7. Withdrawals are processed within 1-3 business days

---

### 2. Alpha Token Rewards (Bittensor Registered Miners)

Bittensor adds a second layer of incentives for miners who register their wallet and hotkey on the HashLayer subnet.

- **Value-Based Rewards**: Alpha tokens based on the hashpower value you provide
- **Value Calculation**: Based on hashprice index and current BTC exchange rates
- **Eligibility**: Requires registration on the **HashLayer Bittensor subnet** (`NETUID` from deployment)
- **Continuous Accumulation**: Tokens accrue automatically as you mine
- **Convertibility**: Alpha tokens can be unstaked to TAO for liquidity

This mechanism ties your physical mining to the decentralized compute economy of Bittensor — rewarding both immediate work (BTC) and long-term network participation (Alpha).

Alpha rewards are disbursed through Bittensor's incentive mechanism every tempo. These rewards are independent of whether the pool found a block or not.

---

See also:

- [Introduction to HashLayer](../README.md)
- [Introduction to Bittensor](https://docs.learnbittensor.org/learn/introduction)
- [Yuma Consensus](https://docs.learnbittensor.org/yuma-consensus/)
- [Emissions](https://docs.learnbittensor.org/emissions/)

## Prerequisites

To run a HashLayer miner, you will need:

- A Bittensor wallet with coldkey and hotkey (for Alpha rewards)
- SHA256d (BTC) mining hardware (ASICs) OR access to remote hashrate
- Python 3.9 or higher (for registration only)
- The most recent release of [Bittensor SDK](https://pypi.org/project/bittensor/)

Bittensor Docs:

- [Wallets, Coldkeys and Hotkeys in Bittensor](https://docs.learnbittensor.org/getting-started/wallets)
- [Miner registration](https://docs.learnbittensor.org/miners/index.md#miner-registration)

## Quick Start

### Step 1: Wallet Setup

Check your wallet, or create one if you have not already.

Bittensor Documentation: [Creating/Importing a Bittensor Wallet](https://docs.learnbittensor.org/working-with-keys)

#### List wallets
```bash
btcli wallet list
```
```console
Wallets
├── Coldkey YourColdkey  ss58_address 5F...
│   ├── Hotkey YourHotkey  ss58_address
│   │   5E...
```

#### Check wallet balance
```bash
btcli wallet balance \
  --wallet.name <your wallet name> \
  --subtensor.network finney
```

### Step 2: Register on the HashLayer Subnet (Mainnet)

Replace `NETUID` with your deployment subnet ID:

#### Check registration status

```bash
btcli wallet overview \
  --wallet.name YOUR_WALLET \
  --netuid $NETUID \
  --subtensor.network finney
```

#### Register to subnet

```bash
btcli subnet register \
  --netuid $NETUID \
  --wallet.name YOUR_WALLET \
  --wallet.hotkey YOUR_HOTKEY \
  --subtensor.network finney
```

### Step 3: Get Your Hotkey

Your hotkey is your miner username. Get your full 48-character hotkey:

```bash
btcli wallet overview \
  --wallet.name YOUR_WALLET \
  --wallet.hotkey YOUR_HOTKEY
```

The hotkey will look like: `5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY`

### Step 4: Configure Your Mining Hardware

Use your **full 48-character hotkey** as the miner username to connect to the HashLayer pool:

**Production Pool (Mainnet)**:
- **Stratum URL**: `stratum+tcp://stratum.hashlayer.ai:3331`
- **Worker Name**: `5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY` (your full hotkey)
- **Password**: `x`

Some deployments use `{btc_address}.{hotkey}` as the worker name when a BTC payout address is required in the Stratum username.

#### Example Configuration

**For ASIC Miners** (Antminer, Whatsminer, etc.):
1. Access your miner's web interface
2. Navigate to pool configuration
3. Enter the pool details:
   - URL: `stratum+tcp://stratum.hashlayer.ai:3331`
   - Worker: Your full 48-character hotkey (or `{btc_address}.{hotkey}`)
   - Password: `x`

**For Mining Software** (cgminer, bfgminer, etc.):
```bash
./cgminer \
  --sha256d \
  -o stratum+tcp://stratum.hashlayer.ai:3331 \
  -u 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY \
  -p x
```

### Step 5: Start Mining

Once configured and connected:
- Your mining hardware will automatically contribute hashrate
- Shares will be recorded and validated
- You'll earn BTC mining rewards (via secondary distribution)
- If registered on Bittensor, you'll also accumulate Alpha tokens

## Monitor Performance

### Check Mining Status

You can monitor your mining performance through:

1. **Your ASIC/Mining Software Dashboard**
   - Check accepted shares
   - Monitor hashrate
   - Verify connection status

2. **HashLayer Website**: https://hashlayer.online/
   - View your contribution
   - Check earnings
   - Monitor ranking

3. **Bittensor Network**
   ```bash
   btcli subnet metagraph \
     --netuid $NETUID \
     --subtensor.network finney | grep YOUR_HOTKEY
   ```

## Withdrawing Rewards

### Alpha / TAO Rewards (Automatic)

Alpha tokens are automatically sent to your hotkey when registered on the subnet:

```bash
# Check TAO balance
btcli wallet balance \
  --wallet.name YOUR_WALLET \
  --subtensor.network finney
```

### BTC Rewards (Manual Withdrawal - Secondary Distribution)

**Important**: BTC mining rewards go through **secondary distribution**. The platform collects all mining revenue and redistributes it to miners and validators. You must manually set up your BTC withdrawal address and submit withdrawal requests.

#### Step-by-Step Withdrawal Process

1. **Login to HashLayer Website**
   - Visit the HashLayer platform: https://hashlayer.online/
   - Connect using your Bittensor coldkey wallet (use the same coldkey that corresponds to your miner hotkey)
   - Ensure you're using the correct wallet that's registered for mining

2. **Set Withdrawal Address**
   - Navigate to account settings or wallet management
   - Add your BTC address:
     - Legacy format: starts with `1` or `3`
     - SegWit format: starts with `bc1`
   - **Verify addresses carefully** — incorrect addresses may result in loss of funds

3. **View Your Balance**
   - Check your accumulated BTC earnings
   - View distribution history
   - Monitor pending withdrawals

4. **Submit Withdrawal Request**
   - Select BTC
   - Enter withdrawal amount (must meet minimum, see `MIN_CLAIM_BTC` in deployment config)
   - Review withdrawal address
   - Confirm network fees
   - Submit withdrawal request (creates a withdrawal ticket)
   - Wait for processing: 1-3 business days

**Withdrawal Requirements**:
- **Minimum amount**: Configured per deployment (e.g. `MIN_CLAIM_BTC=0.0001`)
- **Processing time**: 1-3 business days
- **Network fees**: Deducted from withdrawal amount
- **Verification**: Large withdrawals may require additional verification
- **First withdrawal**: May take longer for security review

**Important Notes**:
- Mining rewards are distributed by the platform (secondary distribution)
- Both miners and validators must set withdrawal addresses on the website
- Withdrawals are processed manually, not automatically
- Keep your withdrawal address up to date
- Save transaction records for your reference

## Maximizing Your Rewards

### For Mining Rewards (BTC)
1. **Maintain Consistent Hashrate**: Stable mining earns more consistent rewards
2. **Submit High-Difficulty Shares**: Better hardware = higher share value
3. **Minimize Downtime**: Every valid share counts toward your earnings
4. **Monitor Share Acceptance**: Check logs to ensure shares are accepted

### For Bittensor Participants (Alpha Tokens)
1. **Register on the HashLayer subnet**: Required for Alpha rewards eligibility
2. **Keep Your Hotkey Active**: Inactive hotkeys won't earn Alpha emissions
3. **Monitor Accumulation**: Track token balances via your wallet
4. **Think Long-Term**: Alpha represents network stake — value compounds as subnet grows

---

## Total Value Proposition

| Miner Type | BTC Rewards | Alpha Tokens | Total Return |
|-------------|-------------|--------------|--------------|
| **Non-Bittensor Miner** | ✅ Mining rewards proportional to hashpower | ❌ Not available | Mining revenue only |
| **Bittensor-Registered Miner** | ✅ Mining rewards | ✅ Alpha Token value | Mining + Alpha yield |
| **Key Benefit** | Direct cryptocurrency earnings | Long-term ecosystem stake | **Enhanced total returns** |

---

## Setting Minimum Difficulty

High-performance ASICs may require minimum difficulty settings. Append the minimum difficulty to your password:

```
x;md=100000;
```

Example:
- Worker: `5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY`
- Password: `x;md=100000;`

Note: Follow the exact format for setting difficulty.

## Troubleshooting

### Connection Issues

**Cannot connect to pool**
- Verify the pool URL: `stratum+tcp://stratum.hashlayer.ai:3331`
- Check your internet connection
- Ensure firewall isn't blocking port 3331
- Try pinging the pool server

**Shares rejected**
- Verify you're using the correct hotkey as username
- Check that your hardware supports SHA256d algorithm
- Ensure difficulty settings are appropriate
- Monitor for hardware errors

### Registration Issues

**Registration failed**
- Check wallet balance (need TAO for registration fee)
- Verify network connectivity
- Ensure using correct network (finney)
- Check subnet status

**Not receiving Alpha rewards**
- Confirm registration on the HashLayer subnet
- Verify hotkey is active and mining
- Check emission schedule
- Monitor wallet balance

### Withdrawal Issues

**Cannot set withdrawal address**
- Verify you're logged in with correct wallet
- Check address format (BTC: `1`, `3`, or `bc1` prefix)
- Ensure address is valid
- Try test transaction first

**Withdrawal delayed**
- Normal processing: 1-3 business days
- Large amounts may require additional verification
- Check withdrawal history for status
- Contact support if delayed beyond 3 days

## Support

- GitHub Issues: https://github.com/hashlayer-labs/hashlayer/issues
- Bittensor Discord: HashLayer subnet channel
- Documentation: https://github.com/hashlayer-labs/hashlayer/tree/main/docs

Happy mining!
