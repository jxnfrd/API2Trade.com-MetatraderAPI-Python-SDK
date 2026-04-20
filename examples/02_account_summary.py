"""
Example 02 — Fetch live account balance & equity
=================================================
API2Trade Python SDK  |  https://www.api2trade.com/

Requirements:
    pip install api2trade-sdk python-dotenv

Usage:
    python examples/02_account_summary.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from api2trade_sdk import Api2TradeClient
from api2trade_sdk.exceptions import AccountNotFoundError, Api2TradeError

API_KEY    = os.getenv("API2TRADE_API_KEY")
ACCOUNT_ID = os.getenv("API2TRADE_ACCOUNT_ID")   # UUID from example 01


def print_summary(s):
    width = 46
    print("┌" + "─" * width + "┐")
    print(f"│  {'Account Summary':^{width-2}}│")
    print("├" + "─" * width + "┤")
    print(f"│  {'Balance':.<20} {s.balance:>10.2f} {s.currency:<10}│")
    print(f"│  {'Equity':.<20} {s.equity:>10.2f} {s.currency:<10}│")
    print(f"│  {'Margin used':.<20} {s.margin:>10.2f} {s.currency:<10}│")
    print(f"│  {'Free margin':.<20} {s.free_margin:>10.2f} {s.currency:<10}│")
    print(f"│  {'Margin level':.<20} {s.margin_level:>9.1f}%{' ':<10}│")
    print("└" + "─" * width + "┘")
    if s.is_margin_call_risk:
        print("  ⚠  MARGIN LEVEL BELOW 150% — monitor closely!")


def main():
    if not ACCOUNT_ID:
        print("❌ Set API2TRADE_ACCOUNT_ID in your .env (run example 01 first)")
        sys.exit(1)

    with Api2TradeClient(api_key=API_KEY) as client:
        print(f"▶ Fetching account summary for {ACCOUNT_ID[:8]}…\n")
        try:
            summary = client.accounts.summary(ACCOUNT_ID)
        except AccountNotFoundError:
            print("❌ Account not found — register it first (example 01)")
            sys.exit(1)
        except Api2TradeError as e:
            print(f"❌ API error: {e}")
            sys.exit(1)

        print_summary(summary)


if __name__ == "__main__":
    main()
