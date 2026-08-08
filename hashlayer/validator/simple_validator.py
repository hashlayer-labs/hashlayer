#!/usr/bin/env python3
"""
Simple validator program - Keep subnet active
"""

import argparse
import logging
import time

import bittensor as bt


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simple validator program")
    parser.add_argument(
        "--wallet.name", type=str, default="bob", dest="wallet_name", help="Wallet name"
    )
    parser.add_argument(
        "--wallet.hotkey",
        type=str,
        default="default",
        dest="wallet_hotkey",
        help="Hotkey name",
    )
    parser.add_argument(
        "--subtensor.network",
        type=str,
        default="ws://127.0.0.1:9944",
        dest="subtensor_network",
        help="Network address",
    )
    parser.add_argument("--netuid", type=int, default=2, help="Subnet ID")
    parser.add_argument(
        "--logging.info",
        action="store_true",
        dest="logging_info",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    if args.logging_info:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    print("🚀 Starting simple validator program")
    print(f"  Wallet: {args.wallet_name}")
    print(f"  Hotkey: {args.wallet_hotkey}")
    print(f"  Network: {args.subtensor_network}")
    print(f"  Subnet ID: {args.netuid}")
    print("")

    try:
        # Initialize subtensor
        subtensor = bt.subtensor(network=args.subtensor_network)

        # Initialize wallet
        wallet = bt.wallet(name=args.wallet_name, hotkey=args.wallet_hotkey)

        print("✅ Validator initialization complete")

        # Main loop
        epoch_count = 0
        while True:
            try:
                # Sync metagraph
                metagraph = subtensor.metagraph(netuid=args.netuid)

                # Check if registered
                if wallet.hotkey.ss58_address not in metagraph.hotkeys:
                    print(
                        f"❌ Hotkey {
                            wallet.hotkey.ss58_address
                        } not registered in subnet {args.netuid}"
                    )
                    time.sleep(30)
                    continue

                # Get UID
                uid = metagraph.hotkeys.index(wallet.hotkey.ss58_address)

                # Set weights (simple uniform distribution)
                weights = [1.0 / len(metagraph.hotkeys)] * len(metagraph.hotkeys)
                uids = list(range(len(metagraph.hotkeys)))

                # Submit weights
                subtensor.set_weights(
                    netuid=args.netuid,
                    wallet=wallet,
                    uids=uids,
                    weights=weights,
                    wait_for_inclusion=True,
                    wait_for_finalization=True,
                )

                epoch_count += 1
                print(f"✅ Epoch {epoch_count}: Weights set successfully")
                print(f"   UID: {uid}")
                print(f"   Weight: {weights[uid]:.4f}")
                print(f"   Subnet size: {len(metagraph.hotkeys)}")

                # Wait for next epoch
                time.sleep(12)  # Local network has shorter epoch time

            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(30)

    except KeyboardInterrupt:
        print("\n🛑 Validator program stopped")
    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    main()
