"""
Example 03 — Full trade lifecycle: quote → open → list → modify → close
=======================================================================
API2Trade Python SDK  |  https://www.api2trade.com/

Demonstrates:
  - Fetching a live quote
  - Opening a Buy Market order with SL and TP
  - Listing all open positions
  - Modifying SL/TP on the open position
  - Closing the position

Requirements:
    pip install api2trade-sdk python-dotenv

Usage:
    python examples/03_place_trade.py

⚠  This example executes REAL trades on your connected account.
   Use a demo account unless you intend to trade live.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from api2trade_sdk import Api2TradeClient
from api2trade_sdk import OrderType
from api2trade_sdk.exceptions import BrokerRejectionError, Api2TradeError

API_KEY    = os.getenv("API2TRADE_API_KEY")
ACCOUNT_ID = os.getenv("API2TRADE_ACCOUNT_ID")

SYMBOL = "EURUSD"
VOLUME = 0.01      # 1 micro lot — adjust to your broker's minimum


def main():
    if not ACCOUNT_ID:
        print("❌ Set API2TRADE_ACCOUNT_ID in your .env (run example 01 first)")
        sys.exit(1)

    with Api2TradeClient(api_key=API_KEY) as client:

        # ── Step 1: Get live quote ────────────────────────────────────────
        print(f"▶ Getting live quote for {SYMBOL}…")
        quote = client.market.quote(ACCOUNT_ID, SYMBOL)
        print(f"  {quote}")

        ask = quote.ask
        bid = quote.bid

        # SL/TP: 20-pip stop loss, 40-pip take profit (adjust per instrument)
        sl = round(ask - 0.0020, 5)
        tp = round(ask + 0.0040, 5)

        # ── Step 2: Open a Buy Market order ──────────────────────────────
        print(f"\n▶ Opening BUY MARKET {VOLUME} lot {SYMBOL}  SL={sl}  TP={tp}…")
        try:
            result = client.orders.send(
                account_id=ACCOUNT_ID,
                symbol=SYMBOL,
                order_type=OrderType.BUY_MARKET,
                volume=VOLUME,
                stop_loss=sl,
                take_profit=tp,
                comment="sdk-example-03",
            )
        except BrokerRejectionError as e:
            print(f"  ❌ Broker rejected order: {e}")
            print(f"     retcode={e.retcode}  retryable={e.is_retryable}")
            sys.exit(1)

        ticket = result.ticket
        print(f"  ✅ Order opened — ticket #{ticket}")

        # ── Step 3: List open positions ───────────────────────────────────
        print("\n▶ Open positions:")
        positions = client.orders.positions(ACCOUNT_ID)
        if not positions:
            print("  (none)")
        for pos in positions:
            print(f"  {pos}")

        # ── Step 4: Modify SL/TP ──────────────────────────────────────────
        new_sl = round(ask - 0.0015, 5)
        new_tp = round(ask + 0.0060, 5)
        print(f"\n▶ Modifying ticket #{ticket}: new SL={new_sl}  new TP={new_tp}…")
        try:
            mod = client.orders.modify(
                account_id=ACCOUNT_ID,
                ticket=ticket,
                stop_loss=new_sl,
                take_profit=new_tp,
            )
            print(f"  ✅ Modified: {mod}")
        except BrokerRejectionError as e:
            print(f"  ⚠  Modify rejected (retcode={e.retcode}): {e}")

        # ── Step 5: Close position ────────────────────────────────────────
        print(f"\n▶ Closing ticket #{ticket}…")
        try:
            close = client.orders.close(ACCOUNT_ID, ticket=ticket, volume=VOLUME)
            print(f"  ✅ Closed: {close}")
        except BrokerRejectionError as e:
            print(f"  ❌ Close rejected: {e}")
            sys.exit(1)

        print("\n✅ Trade lifecycle complete.")


if __name__ == "__main__":
    main()
