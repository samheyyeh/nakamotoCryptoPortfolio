#!/usr/bin/env python3

import requests
import time
from dotenv import load_dotenv
import os
from moralis import evm_api

load_dotenv()

CHAINBASE_API_KEY = os.getenv("CHAINBASE_API_KEY")
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
CHAINBASE_PRICE_URL = "https://api.chainbase.online/v1/token/price"
COINGECKO_ETH_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"

DUST_THRESHOLD = 1.00


def is_valid_eth_address(address):
    return isinstance(address, str) and address.startswith("0x") and len(address) == 42


def get_live_eth_price():
    try:
        resp = requests.get(f"{COINGECKO_ETH_URL}&include_24hr_change=true")
        resp.raise_for_status()
        data = resp.json()["ethereum"]
        return data["usd"], data.get("usd_24h_change")
    except Exception as e:
        print("Could not fetch ETH price:", e)
        return 0.0, None


def get_eth_balance_from_moralis(address):
    # Fetch ETH balance from Moralis (native token)
    try:
        result = evm_api.balance.get_native_balance(
            api_key=MORALIS_API_KEY,
            params={"chain": "eth", "address": address}
        )
        balance_wei = int(result.get("balance", 0))
        return balance_wei / 1e18  # Convert from Wei to ETH
    except Exception as e:
        print("Could not fetch native ETH balance from Moralis:", e)
        return 0.0


def get_erc20_tokens_moralis(address):
    try:
        result = evm_api.wallets.get_wallet_token_balances_price(
            api_key=MORALIS_API_KEY,
            params={
                "chain": "eth",
                "address": address,
                "exclude_spam": True,
                "exclude_unverified_contracts": True,
                "exclude_native": True
            }
        )

        filtered_tokens = []

        for token in result["result"]:
            usd_value = token.get("usd_value", 0.0)
            if usd_value >= DUST_THRESHOLD:
                filtered_tokens.append({
                    "symbol": token.get("symbol", "UNKNOWN"),
                    "amount": float(token.get("balance_formatted", 0.0)),
                    "usd_value": usd_value,
                    "contract": token.get("token_address"),
                    "decimals": token.get("decimals"),
                    "change_24h_percent": token.get("usd_price_24hr_percent_change"),
                })

        return filtered_tokens

    except Exception as e:
        print("Error fetching ERC-20 tokens from Moralis:", e)
        return []


def get_eth_holdings(address):
    eth_price, eth_change = get_live_eth_price()
    eth_balance = get_eth_balance_from_moralis(address)
    eth_usd_value = eth_balance * eth_price

    native = {
        "symbol": "ETH",
        "balance": eth_balance,
        "usd_value": eth_usd_value,
        "change_24h": eth_change
    } if eth_usd_value >= DUST_THRESHOLD else None

    tokens = get_erc20_tokens_moralis(address)

    return {
        "native": native,
        "tokens": tokens
    }


if __name__ == "__main__":
    address = input("Enter Ethereum wallet address: ").strip()
    if not address:
        print("No address entered. Exiting.")
    else:
        data = get_eth_holdings(address)
        print(data)
