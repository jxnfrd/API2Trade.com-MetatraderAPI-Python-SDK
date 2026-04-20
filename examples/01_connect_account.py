"""
Example 01 — Register & verify an MT4/MT5 account
==================================================
API2Trade Python SDK  |  https://www.api2trade.com/
Docs: https://docs.metatraderapi.dev/docs

This script:
  1. Registers your MetaTrader account with the API2Trade bridge
  2. Verifies the connection is live
  3. Prints the Account UUID — save it for all subsequent calls

Requirements:
    pip install api2trade-sdk python-dotenv

Usage:
    cp .env.example .env       # fill in your API key + broker credentials
    python examples/01_connect_account.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# --- pip install api2trade-sdk ---
from api2trade_sdk import Api2TradeClient
from api2trade_sdk.exceptions import AuthenticationError, Api2TradeError

# ── Config ──────────────────────────────────────────────────────────────────
API_KEY   = os.getenv("API2TRADE_API_KEY")
MT_LOGIN  = os.getenv("MT_LOGIN",  "123456")          # your MT account number
MT_PASS   = os.getenv("MT_PASS",   "YourBrokerPass")  # main trading password
MT_SERVER = os.getenv("MT_SERVER", "ICMarkets-Live01") # exact server from MT terminal
# ────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  API2Trade SDK — Connect & Verify Account")
    print("=" * 60)

    try:
        client = Api2TradeClient(api_key=API_KEY)
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("   Set API2TRADE_API_KEY in your .env file.")
        sys.exit(1)

    # Step 1: Register the account
    print(f"\n▶ Registering account login={MT_LOGIN} server={MT_SERVER}…")
    try:
        account_id = client.accounts.register(
            login=MT_LOGIN,
            password=MT_PASS,
            server=MT_SERVER,
        )
    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)
    except Api2TradeError as e:
        print(f"❌ Registration failed: {e}")
        sys.exit(1)

    print(f"  ✅ Account UUID: {account_id}")

    # Step 2: Verify connection
    print("\n▶ Checking connection status…")
    status = client.accounts.check_connect(account_id)
    if status.connected:
        print(f"  ✅ Bridge is CONNECTED ({status})")
    else:
        print(f"  ⚠  Bridge is RECONNECTING — try again in a few seconds.")
        print(f"     Status: {status}")

    # Done
    print("\n" + "=" * 60)
    print(f"  Save your Account UUID for all subsequent SDK calls:")
    print(f"  account_id = \"{account_id}\"")
    print("=" * 60)

    client.close()
    return account_id


if __name__ == "__main__":
    main()
