"""
Example 05 — Real-time WebSocket quote streaming
=================================================
API2Trade Python SDK  |  https://www.api2trade.com/

Demonstrates both callback-style and async-generator-style streaming.

Requirements:
    pip install api2trade-sdk websockets python-dotenv

Usage:
    python examples/05_websocket_stream.py
"""

import asyncio
import os
import signal
import sys
from dotenv import load_dotenv

load_dotenv()

from api2trade_sdk import Api2TradeClient
from api2trade_sdk.models import Tick

API_KEY    = os.getenv("API2TRADE_API_KEY")
ACCOUNT_ID = os.getenv("API2TRADE_ACCOUNT_ID")

SYMBOLS = ["EURUSD", "GBPUSD", "XAUUSD"]
MAX_TICKS = 30   # stop after this many ticks for demo purposes


# ── Style A: callback-based streaming ─────────────────────────────────────

tick_count = 0

def on_tick(tick: Tick) -> None:
    global tick_count
    tick_count += 1
    direction = "↑" if tick.ask > tick.bid else "↓"
    print(
        f"  [{tick_count:>3}] {tick.symbol:<8} {direction}  "
        f"bid={tick.bid:.5f}  ask={tick.ask:.5f}  "
        f"spread={tick.spread_pips:.1f}pip"
    )

def on_connect() -> None:
    print("  ✅ WebSocket connected — receiving ticks…\n")

def on_disconnect() -> None:
    print("  ⚠  WebSocket disconnected — auto-reconnecting…")

def on_error(exc: Exception) -> None:
    print(f"  ⚠  Stream error: {exc}")


async def run_callback_stream(client: Api2TradeClient) -> None:
    """Stream ticks via callback. Cancels after MAX_TICKS for demo."""
    global tick_count

    async def check_limit():
        while tick_count < MAX_TICKS:
            await asyncio.sleep(0.1)
        stream_task.cancel()

    stream_task = asyncio.ensure_future(
        client.stream(
            account_id=ACCOUNT_ID,
            symbols=SYMBOLS,
            on_tick=on_tick,
            on_connect=on_connect,
            on_disconnect=on_disconnect,
            on_error=on_error,
            max_reconnects=3,
        )
    )

    await asyncio.gather(stream_task, check_limit(), return_exceptions=True)
    print(f"\n✅ Received {tick_count} ticks. Stream stopped.")


# ── Style B: async generator ──────────────────────────────────────────────

async def run_generator_stream(client: Api2TradeClient) -> None:
    """Stream ticks via async for — useful for clean break conditions."""
    print("  (async generator mode)\n")
    count = 0
    async for tick in client.stream_iter(ACCOUNT_ID, SYMBOLS):
        count += 1
        print(f"  [{count:>3}] {tick}")
        if count >= MAX_TICKS:
            break
    print(f"\n✅ Received {count} ticks from generator. Done.")


# ── Main ──────────────────────────────────────────────────────────────────

async def main():
    if not ACCOUNT_ID:
        print("❌ Set API2TRADE_ACCOUNT_ID in your .env (run example 01 first)")
        sys.exit(1)

    print("=" * 60)
    print("  API2Trade SDK — Real-Time WebSocket Stream")
    print(f"  Symbols: {', '.join(SYMBOLS)}")
    print(f"  Stopping after {MAX_TICKS} ticks (demo)")
    print("=" * 60)

    client = Api2TradeClient(api_key=API_KEY)

    # Choose Style A or Style B:
    MODE = os.getenv("STREAM_MODE", "callback")   # "callback" or "generator"

    if MODE == "generator":
        await run_generator_stream(client)
    else:
        await run_callback_stream(client)

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
