#!/usr/bin/env python3

import requests
from dotenv import load_dotenv
import os

load_dotenv()

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
HELIUS_ENDPOINT = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
COINGECKO_SOL_URL = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd&include_24hr_change=true"

DUST_THRESHOLD = 1.00


def get_live_sol_price():
    """Fetches live SOL/USD price and 24h change from CoinGecko"""
    try:
        resp = requests.get(COINGECKO_SOL_URL)
        resp.raise_for_status()
        data = resp.json()["solana"]
        price = data.get("usd", 0.0)
        change = data.get("usd_24h_change", None)
        return price, change
    except Exception as e:
        print("Could not fetch SOL price:", e)
        return 0.0, None


def get_sol_balance(owner_address):
    """Fetches native SOL balance via getBalance RPC method"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [owner_address]
    }
    resp = requests.post(HELIUS_ENDPOINT, headers={"Content-Type": "application/json"}, json=payload)
    resp.raise_for_status()
    result = resp.json().get("result", {})
    lamports = result.get("value", 0)
    sol = lamports / 1e9
    return sol


def fetch_assets(owner_address):
    """Fetches SPL tokens using searchAssets RPC method"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "searchAssets",
        "params": {
            "ownerAddress": owner_address,
            "tokenType": "fungible"
        }
    }
    resp = requests.post(HELIUS_ENDPOINT, headers={"Content-Type": "application/json"}, json=payload)
    resp.raise_for_status()
    return resp.json().get("result", {}).get("items", [])


def get_sol_holdings(owner_address):
    sol_price, sol_change = get_live_sol_price()
    sol_balance = get_sol_balance(owner_address)
    sol_usd_value = sol_balance * sol_price

    native = {
        "symbol": "SOL",
        "balance": sol_balance,
        "usd_value": sol_usd_value,
        "change_24h": sol_change
    } if sol_usd_value >= DUST_THRESHOLD else None

    tokens_raw = fetch_assets(owner_address)
    filtered = []

    for token in tokens_raw:
        info = token.get("token_info", {})
        symbol = info.get("symbol", token.get("id", "")[:8])
        decimals = info.get("decimals", 0)
        raw_balance = info.get("balance", 0)

        try:
            amount = raw_balance / (10 ** decimals)
        except (TypeError, ZeroDivisionError):
            continue

        usd_price = info.get("price_info", {}).get("price_per_token", 0)
        usd_value = amount * usd_price

        price_change_24h = info.get("price_info", {}).get("price_24h_change", None)

        if usd_value >= DUST_THRESHOLD:
            filtered.append({
                "symbol": symbol,
                "amount": amount,
                "usd_value": usd_value,
                "decimals": decimals,
                "change_24h": price_change_24h
            })

    return {"native": native, "tokens": filtered}


if __name__ == "__main__":
    address = input("Enter Solana wallet address: ").strip()
    if not address:
        print("No address entered. Exiting.")
    else:
        data = get_sol_holdings(address)
        print(data)
