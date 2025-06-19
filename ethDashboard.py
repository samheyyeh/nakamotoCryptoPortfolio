#!/usr/bin/env python3

import requests
import time
from dotenv import load_dotenv
import os

load_dotenv()

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ETHERSCAN_URL = "https://api.etherscan.io/api"
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/token_price/ethereum"
COINGECKO_ETH_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"

DUST_THRESHOLD = 1.00


def get_eth_balance(address):
    params = {
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest",
        "apikey": ETHERSCAN_API_KEY
    }
    resp = requests.get(ETHERSCAN_URL, params=params)
    resp.raise_for_status()
    wei = int(resp.json()["result"])
    return wei / 1e18


def get_erc20_tokens(address):
    params = {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }
    resp = requests.get(ETHERSCAN_URL, params=params)
    resp.raise_for_status()
    txs = resp.json().get("result", [])

    tokens = {}
    for tx in txs:
        token_symbol = tx["tokenSymbol"]
        token_contract = tx["contractAddress"]
        decimals = int(tx["tokenDecimal"])
        to = tx["to"].lower()
        from_addr = tx["from"].lower()
        value = int(tx["value"])

        if to == address.lower():
            tokens[token_contract] = tokens.get(token_contract, {"symbol": token_symbol, "decimals": decimals, "balance": 0})
            tokens[token_contract]["balance"] += value
        elif from_addr == address.lower():
            tokens[token_contract] = tokens.get(token_contract, {"symbol": token_symbol, "decimals": decimals, "balance": 0})
            tokens[token_contract]["balance"] -= value

    return tokens


def is_valid_eth_address(address):
    return isinstance(address, str) and address.startswith("0x") and len(address) == 42


def get_token_prices(contract_addresses, batch_size=50):
    if not contract_addresses:
        return {}

    contract_addresses = [addr.lower() for addr in contract_addresses if is_valid_eth_address(addr)]
    prices = {}

    for i in range(0, len(contract_addresses), batch_size):
        chunk = contract_addresses[i:i + batch_size]
        joined = ",".join(chunk)
        params = {
            "contract_addresses": joined,
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }

        try:
            resp = requests.get(COINGECKO_PRICE_URL, params=params)
            resp.raise_for_status()
            prices.update(resp.json())
        except requests.HTTPError:
            print(f"Failed to fetch prices for chunk {i // batch_size + 1}")
        time.sleep(1)

    return prices


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
    eth_balance = get_eth_balance(address)
    eth_usd_value = eth_balance * eth_price

    native = {
        "symbol": "ETH",
        "balance": eth_balance,
        "usd_value": eth_usd_value,
        "change_24h": eth_change
    } if eth_usd_value >= DUST_THRESHOLD else None

    tokens = get_erc20_tokens(address)
    if not tokens:
        return {"native": native, "tokens": []}

    prices = get_token_prices(tokens.keys())
    filtered = []

    for contract, info in tokens.items():
        amount = info["balance"] / (10 ** info["decimals"])
        token_data = prices.get(contract.lower(), {})
        usd = token_data.get("usd", 0.0)
        change = token_data.get("usd_24h_change")
        total_value = amount * usd

        if total_value >= DUST_THRESHOLD:
            filtered.append({
                "symbol": info["symbol"],
                "amount": amount,
                "usd_value": total_value,
                "decimals": info["decimals"],
                "change_24h": change
            })

    return {"native": native, "tokens": filtered}


if __name__ == "__main__":
    address = input("Enter Ethereum wallet address: ").strip()
    if not address:
        print("No address entered. Exiting.")
    else:
        data = get_eth_holdings(address)
        print(data)
