"""
Example 06 — Prop firm rule-enforcement monitor
===============================================
API2Trade Python SDK  |  https://www.api2trade.com/

Demonstrates a production-ready pattern for prop firm use cases:
  - Polls account equity every N seconds
  - Enforces a drawdown limit (e.g. 5% max daily loss)
  - Closes ALL positions automatically if limit is breached
  - Runs indefinitely until manually stopped (Ctrl+C)

Requirements:
    pip install api2trade-sdk python-dotenv

Usage:
    python examples/06_prop_firm_monitor.py
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("prop_monitor")

from api2trade_sdk import Api2TradeClient
from api2trade_sdk.exceptions import Api2TradeError, BrokerRejectionError

API_KEY    = os.getenv("API2TRADE_API_KEY")
ACCOUNT_ID = os.getenv("API2TRADE_ACCOUNT_ID")

# ── Configuration ─────────────────────────────────────────────────────────
POLL_INTERVAL_SECONDS = 10          # how often to check account equity
MAX_DAILY_DRAWDOWN_PCT = 5.0        # e.g. 5% of starting balance
MARGIN_CALL_ALERT_PCT  = 150.0      # warn if margin level below this %
# ─────────────────────────────────────────────────────────────────────────


def check_and_enforce(client: Api2TradeClient, start_balance: float) -> bool:
    """
    Fetch account state and enforce drawdown rule.
    Returns True if all is well, False if the rule was breached and handled.
    """
    summary  = client.accounts.summary(ACCOUNT_ID)
    equity   = summary.equity
    drawdown = (start_balance - equity) / start_balance * 100.0

    logger.info(
        "Balance=%.2f  Equity=%.2f  Drawdown=%.2f%%  MarginLevel=%.1f%%  %s",
        summary.balance, equity, drawdown, summary.margin_level, summary.currency,
    )

    # Margin call warning
    if summary.is_margin_call_risk:
        logger.warning("⚠  MARGIN LEVEL LOW (%.1f%%) — monitor closely!", summary.margin_level)

    # Drawdown rule breach
    if drawdown >= MAX_DAILY_DRAWDOWN_PCT:
        logger.error(
            "🚨 DRAWDOWN LIMIT BREACHED (%.2f%% ≥ %.1f%%) — closing all positions!",
            drawdown, MAX_DAILY_DRAWDOWN_PCT,
        )
        positions = client.orders.positions(ACCOUNT_ID)
        if not positions:
            logger.info("   No open positions to close.")
        else:
            logger.info("   Closing %d position(s)…", len(positions))
            try:
                results = client.orders.close_all(ACCOUNT_ID)
                for r in results:
                    logger.info("   Closed: %s", r)
            except BrokerRejectionError as e:
                logger.error("   Failed to close position: %s", e)
        return False   # rule breached

    return True   # all good


def main():
    if not ACCOUNT_ID:
        print("❌ Set API2TRADE_ACCOUNT_ID in your .env (run example 01 first)")
        sys.exit(1)

    client = Api2TradeClient(api_key=API_KEY)

    logger.info("Prop Firm Monitor starting…")
    logger.info("Account: %s", ACCOUNT_ID[:8] + "…")
    logger.info("Max daily drawdown: %.1f%%", MAX_DAILY_DRAWDOWN_PCT)
    logger.info("Poll interval: %ds", POLL_INTERVAL_SECONDS)
    logger.info("─" * 60)

    # Fetch starting balance once at launch
    try:
        initial = client.accounts.summary(ACCOUNT_ID)
    except Api2TradeError as e:
        logger.error("Could not fetch initial balance: %s", e)
        sys.exit(1)

    start_balance = initial.balance
    logger.info("Starting balance: %.2f %s", start_balance, initial.currency)
    logger.info("Drawdown limit:   %.2f %s (%.1f%%)",
                start_balance * MAX_DAILY_DRAWDOWN_PCT / 100,
                initial.currency, MAX_DAILY_DRAWDOWN_PCT)
    logger.info("─" * 60)

    try:
        while True:
            try:
                ok = check_and_enforce(client, start_balance)
                if not ok:
                    logger.warning("Rule breached — monitor taking a 60s pause before resuming.")
                    time.sleep(60)
                    # Refresh start_balance after intervention
                    start_balance = client.accounts.summary(ACCOUNT_ID).balance
                    logger.info("Resuming with adjusted balance: %.2f", start_balance)
            except Api2TradeError as e:
                logger.error("API error during poll: %s", e)

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("Monitor stopped by user.")

    client.close()


if __name__ == "__main__":
    main()
