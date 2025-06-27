#!/usr/bin/env python3

import requests
import time
from dotenv import load_dotenv
import os

load_dotenv()

CHAINBASE_API_KEY = os.getenv("CHAINBASE_API_KEY")
CHAINBASE_PRICE_URL = "https://api.chainbase.online/v1/token/price"
ETHPLORER_API_URL = "https://api.ethplorer.io/getAddressInfo"
COINGECKO_ETH_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"

DUST_THRESHOLD = 1.00


def is_valid_eth_address(address):
    return isinstance(address, str) and address.startswith("0x") and len(address) == 42


def get_eth_balance_ethplorer(address):
    url = f"{ETHPLORER_API_URL}/{address}?apiKey=freekey"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        return float(data.get("ETH", {}).get("balance", 0))
    except Exception as e:
        print("Failed to fetch ETH balance from Ethplorer:", e)
        return 0.0


def get_erc20_tokens(address):
    """
    Return a list of tokens with contract, symbol, balance, and decimals
    """
    url = f"{ETHPLORER_API_URL}/{address}?apiKey=freekey"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        tokens = data.get("tokens", [])

        token_list = []
        for token in tokens:
            info = token.get("tokenInfo", {})
            contract = info.get("address", "").lower()

            if not is_valid_eth_address(contract):
                continue

            symbol = info.get("symbol", "UNKNOWN")
            decimals = int(info.get("decimals", "0") or 0)
            raw_balance = int(token.get("rawBalance", "0"))

            token_list.append({
                "contract": contract,
                "symbol": symbol,
                "decimals": decimals,
                "balance_raw": raw_balance
            })

        return token_list
    except requests.RequestException as e:
        print("Error fetching token data from Ethplorer:", e)
        return []


def get_token_price_from_chainbase(contract):
    """
    Gets the USD price for a given token contract using Chainbase.
    """
    headers = {"x-api-key": CHAINBASE_API_KEY}
    params = {
        "chain_id": "1",
        "contract_address": contract
    }

    try:
        resp = requests.get(CHAINBASE_PRICE_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") == 0 and "data" in data:
            return float(data["data"].get("price", 0.0)), int(data["data"].get("decimals", 0))
    except Exception as e:
        print(f"Failed to fetch price for {contract}: {e}")
    return 0.0, 0


def get_live_eth_price():
    try:
        resp = requests.get(f"{COINGECKO_ETH_URL}&include_24hr_change=true")
        resp.raise_for_status()
        data = resp.json()["ethereum"]
        return data["usd"], data.get("usd_24h_change")
    except Exception as e:
        print("Could not fetch ETH price:", e)
        return 0.0, None


def get_eth_holdings(address):
    eth_price, eth_change = get_live_eth_price()
    eth_balance = get_eth_balance_ethplorer(address)
    eth_usd_value = eth_balance * eth_price

    native = {
        "symbol": "ETH",
        "balance": eth_balance,
        "usd_value": eth_usd_value,
        "change_24h": eth_change
    } if eth_usd_value >= DUST_THRESHOLD else None

    token_list = get_erc20_tokens(address)
    if not token_list:
        return {"native": native, "tokens": []}

    filtered = []
    for token in token_list:
        contract = token["contract"]
        symbol = token["symbol"]
        balance_raw = token["balance_raw"]
        decimals = token["decimals"]

        if balance_raw == 0:
            continue

        token_price, _ = get_token_price_from_chainbase(contract)
        amount = balance_raw / (10 ** decimals) if decimals > 0 else balance_raw
        usd_value = amount * token_price

        if usd_value >= DUST_THRESHOLD:
            filtered.append({
                "symbol": symbol,
                "amount": amount,
                "usd_value": usd_value,
                "decimals": decimals,
                "contract": contract
            })

        time.sleep(0.2)  # Chainbase may rate limit

    return {
        "native": native,
        "tokens": filtered
    }


if __name__ == "__main__":
    address = input("Enter Ethereum wallet address: ").strip()
    if not address:
        print("No address entered. Exiting.")
    else:
        data = get_eth_holdings(address)
        print(data)
