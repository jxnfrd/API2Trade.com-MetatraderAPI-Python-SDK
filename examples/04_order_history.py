"""
Example 04 — Fetch trade history & compute P&L statistics
==========================================================
API2Trade Python SDK  |  https://www.api2trade.com/

Demonstrates:
  - Fetching all closed trades in a 30-day window
  - Paginated history for large accounts
  - Using the built-in summary_stats() helper
  - Iterating all pages with iter_all()

Requirements:
    pip install api2trade-sdk python-dotenv

Usage:
    python examples/04_order_history.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

from api2trade_sdk import Api2TradeClient
from api2trade_sdk.exceptions import Api2TradeError

API_KEY    = os.getenv("API2TRADE_API_KEY")
ACCOUNT_ID = os.getenv("API2TRADE_ACCOUNT_ID")


def print_stats(stats: dict) -> None:
    w = 46
    win_pct = stats["win_rate"] * 100
    pf      = stats["profit_factor"]

    print("┌" + "─" * w + "┐")
    print(f"│  {'Strategy P&L Summary':^{w-2}}│")
    print("├" + "─" * w + "┤")
    print(f"│  {'Total trades':.<22} {stats['total_trades']:>8}          │")
    print(f"│  {'Winning trades':.<22} {stats['winning_trades']:>8}          │")
    print(f"│  {'Losing trades':.<22} {stats['losing_trades']:>8}          │")
    print(f"│  {'Win rate':.<22} {win_pct:>7.1f}%          │")
    print(f"│  {'Gross profit':.<22} {stats['gross_profit']:>10.2f}        │")
    print(f"│  {'Gross loss':.<22} {stats['gross_loss']:>10.2f}        │")
    print(f"│  {'Net profit':.<22} {stats['net_profit']:>10.2f}        │")
    pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"
    print(f"│  {'Profit factor':.<22} {pf_str:>10}        │")
    print(f"│  {'Avg winning trade':.<22} {stats['avg_win']:>10.2f}        │")
    print(f"│  {'Avg losing trade':.<22} {stats['avg_loss']:>10.2f}        │")
    print("└" + "─" * w + "┘")


def main():
    if not ACCOUNT_ID:
        print("❌ Set API2TRADE_ACCOUNT_ID in your .env (run example 01 first)")
        sys.exit(1)

    now       = datetime.now(tz=timezone.utc)
    date_from = now - timedelta(days=30)
    date_to   = now

    with Api2TradeClient(api_key=API_KEY) as client:

        # ── Option A: Simple get (all results in one call) ─────────────────
        print(f"▶ Fetching closed trades (last 30 days)…\n")
        try:
            history = client.history.get(ACCOUNT_ID, date_from=date_from, date_to=date_to)
        except Api2TradeError as e:
            print(f"❌ {e}")
            sys.exit(1)

        if not history:
            print("  (no closed trades in this period)")
        else:
            print(f"  Found {len(history)} closed trade(s)\n")
            print(f"  {'#Ticket':>10}  {'Symbol':<8}  {'Type':<5}  {'Vol':>6}  {'Net P&L':>10}")
            print(f"  {'─'*10}  {'─'*8}  {'─'*5}  {'─'*6}  {'─'*10}")
            for o in history[:10]:   # show first 10 rows
                pnl = f"+{o.net_profit:.2f}" if o.net_profit >= 0 else f"{o.net_profit:.2f}"
                print(f"  #{o.ticket:>9}  {o.symbol:<8}  {o.order_type:<5}  {o.volume:>6.2f}  {pnl:>10}")
            if len(history) > 10:
                print(f"  … and {len(history) - 10} more trades")

        # ── Option B: P&L stats ────────────────────────────────────────────
        print("\n▶ Computing strategy statistics…\n")
        stats = client.history.summary_stats(ACCOUNT_ID, date_from=date_from, date_to=date_to)
        print_stats(stats)

        # ── Option C: Paginated (for large accounts) ───────────────────────
        print("\n▶ Paginated history (page 1 of 50 records)…")
        page = client.history.get_page(
            ACCOUNT_ID, date_from=date_from, date_to=date_to, page=1, page_size=50
        )
        print(f"  {page}")

        # ── Option D: iter_all generator ────────────────────────────────────
        print("\n▶ Iterating all pages (iter_all)…")
        total_net = 0.0
        count = 0
        for order in client.history.iter_all(ACCOUNT_ID, date_from=date_from, date_to=date_to):
            total_net += order.net_profit
            count += 1
        print(f"  Iterated {count} orders  |  Total net P&L: {total_net:.2f}")


if __name__ == "__main__":
    main()
