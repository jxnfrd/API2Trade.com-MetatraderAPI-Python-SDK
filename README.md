# API2Trade Python SDK

> **Official Python SDK for the <a href="https://api2trade.com" rel="dofollow">API2Trade</a> Metatrader API.**  
> A robust **API for Metatrader** that lets you control your trading accounts programmatically.  
> Build integrations, trading bots, and dashboards using this high-performance **MT4 API** and **MT5 API** — no MetaTrader terminal required.

[![PyPI version](https://img.shields.io/badge/PyPI-api2trade--sdk-blue)](https://pypi.org/project/api2trade-sdk/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)
[![API Status](https://img.shields.io/badge/API_Status-99.95%25_Uptime-brightgreen)](https://status.metatraderapi.dev/)
[![Docs](https://img.shields.io/badge/Docs-docs.metatraderapi.dev-informational)](https://docs.metatraderapi.dev/docs)

---

## Features

| Feature | Detail |
|---------|--------|
| **Full API coverage** | All 11 REST endpoints + WebSocket streaming |
| **Typed models** | Dataclass responses — no raw dict parsing |
| **Auto-retry** | Exponential back-off on requotes, timeouts, server busy |
| **WebSocket streaming** | Callback and async-generator styles with auto-reconnect |
| **Both auth modes** | API key (Single plan) + HTTP Basic Auth (Pro plans) |
| **Exception hierarchy** | Specific exceptions for auth, 404, rate limit, broker rejection |
| **P&L statistics** | Built-in `summary_stats()` — win rate, profit factor, etc. |
| **Paginated history** | `iter_all()` generator — handles any account size |
| **Context manager** | `with Api2TradeClient(...) as client:` — auto-closes session |
| **Env-var config** | `API2TRADE_API_KEY` and friends — 12-factor ready |
| **Python 3.8 – 3.12** | Fully tested |

---

## Installation

```bash
# Core SDK (REST only)
pip install api2trade-sdk

# Core + WebSocket streaming
pip install "api2trade-sdk[streaming]"

# Development (tests, streaming, dotenv)
pip install "api2trade-sdk[dev]"
```

> **No MetaTrader installation required.** The SDK communicates directly with
> the API2Trade cloud bridge over standard HTTPS and WSS.

---

## 60-Second Quickstart

```python
from api2trade_sdk import Api2TradeClient, OrderType

client = Api2TradeClient(api_key="YOUR_API_KEY")

# 1. Register your MT4/MT5 account
account_id = client.accounts.register(
    login="123456",
    password="BrokerPass",
    server="ICMarkets-Live01",
)
print(f"Account UUID: {account_id}")   # save this!

# 2. Check live balance
summary = client.accounts.summary(account_id)
print(f"Balance: {summary.balance} {summary.currency}")
print(f"Equity:  {summary.equity} {summary.currency}")

# 3. Get a live quote
quote = client.market.quote(account_id, "EURUSD")
print(quote)   # Quote(EURUSD: bid=1.08500, ask=1.08510, spread=1.0 pips)

# 4. Place a trade
result = client.orders.send(
    account_id,
    symbol="EURUSD",
    order_type=OrderType.BUY_MARKET,
    volume=0.01,
    stop_loss=round(quote.ask - 0.0020, 5),
    take_profit=round(quote.ask + 0.0040, 5),
)
print(f"Ticket: {result.ticket}")   # ✅ OrderResult

# 5. Close it
client.orders.close(account_id, ticket=result.ticket)
```

---

## Authentication

### Single Account Plan (€12/mo)

```python
client = Api2TradeClient(api_key="YOUR_API_KEY")
# or via environment variable:
# export API2TRADE_API_KEY=your_key
client = Api2TradeClient()
```

### Pro Plans (Basic Auth + dedicated URL)

```python
client = Api2TradeClient(
    pro_username="your_username",
    pro_password="your_password",
    base_url="https://your-dedicated-url.api2trade.com",
)
```

Find your API key at [app.metatraderapi.dev → Settings](https://app.metatraderapi.dev).

---

## Configuration via Environment Variables

```bash
# .env
API2TRADE_API_KEY=sk-...
API2TRADE_ACCOUNT_ID=a1b2c3d4-...
API2TRADE_BASE_URL=https://api.metatraderapi.dev    # optional
API2TRADE_WS_URL=wss://api.metatraderapi.dev/stream # optional
```

```python
from dotenv import load_dotenv
load_dotenv()

client = Api2TradeClient()   # reads API2TRADE_API_KEY automatically
```

---

## API Reference

### `client.accounts`

```python
# Register MT4/MT5 account → returns UUID string
account_id = client.accounts.register(login, password, server)

# Check bridge connection status
status: ConnectStatus = client.accounts.check_connect(account_id)
# status.connected → bool

# Live balance / equity / margin
s: AccountSummary = client.accounts.summary(account_id)
s.balance       # float
s.equity        # float
s.free_margin   # float
s.margin_level  # float (%)
s.currency      # str
s.is_margin_call_risk  # True when margin_level < 150%

# Remove account from bridge
client.accounts.delete(account_id)
```

### `client.market`

```python
# Single symbol quote
q: Quote = client.market.quote(account_id, "EURUSD")
q.bid           # float
q.ask           # float
q.spread        # float (price units)
q.spread_pips   # float (pip units)
q.mid           # float (midpoint)

# Multiple symbols at once
quotes: list[Quote] = client.market.quotes(account_id, ["EURUSD", "GBPUSD", "XAUUSD"])
```

### `client.orders`

```python
from api2trade_sdk import OrderType

# Open a market or pending order
result: OrderResult = client.orders.send(
    account_id,
    symbol="EURUSD",
    order_type=OrderType.BUY_MARKET,  # or SELL_MARKET, BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP
    volume=0.01,
    stop_loss=1.0800,
    take_profit=1.1000,
    comment="my-bot",
    auto_retry=True,     # retry on requote/timeout (default: True)
    max_retries=2,
)
result.ticket   # int  — MetaTrader ticket number
result.success  # bool — True when retcode == 0

# Modify SL/TP
client.orders.modify(account_id, ticket=12345678, stop_loss=1.07, take_profit=1.11)

# Close position (partial or full)
client.orders.close(account_id, ticket=12345678)              # full close
client.orders.close(account_id, ticket=12345678, volume=0.005) # partial close

# Close ALL open positions
client.orders.close_all(account_id)

# List open positions
positions: list[Position] = client.orders.positions(account_id)
for p in positions:
    print(p.ticket, p.symbol, p.order_type, p.volume, p.total_pnl)
```

### `client.history`

```python
from datetime import datetime, timedelta, timezone

now       = datetime.now(tz=timezone.utc)
date_from = now - timedelta(days=30)

# All closed trades in date range
history: list[OrderHistoryItem] = client.history.get(account_id, date_from, now)

# Single page (for large accounts)
page: PaginatedHistory = client.history.get_page(account_id, date_from, now, page=1, page_size=50)
page.total       # int
page.total_pages # int
page.has_next    # bool

# Iterate all pages as a generator (memory-efficient)
for order in client.history.iter_all(account_id, date_from, now):
    print(order.net_profit)

# Last N days shortcut
history = client.history.last_n_days(account_id, days=7)

# Built-in statistics
stats = client.history.summary_stats(account_id, date_from, now)
print(stats["win_rate"])        # e.g. 0.6234
print(stats["profit_factor"])   # e.g. 2.15
print(stats["net_profit"])      # e.g. 934.50
```

### WebSocket Streaming

```python
import asyncio
from api2trade_sdk import Api2TradeClient

client = Api2TradeClient(api_key="...")

# Style A: callback (runs forever, auto-reconnects)
def on_tick(tick):
    print(f"{tick.symbol}: {tick.bid:.5f} / {tick.ask:.5f}  ({tick.spread_pips:.1f} pips)")

asyncio.run(client.stream(account_id, symbols=["EURUSD", "XAUUSD"], on_tick=on_tick))

# Style B: async generator (fine-grained control)
async def main():
    async for tick in client.stream_iter(account_id, ["EURUSD"]):
        print(tick)
        if tick.ask > 1.10:
            break

asyncio.run(main())
```

---

## Error Handling

```python
from api2trade_sdk.exceptions import (
    AuthenticationError,    # HTTP 401 — invalid API key
    AccountNotFoundError,   # HTTP 404 — account not registered
    RateLimitError,         # HTTP 429 — too many requests (Single plan)
    BrokerRejectionError,   # HTTP 200 but retcode != 0
    Api2TradeConnectionError,  # Network error (timeout, DNS, etc.)
    Api2TradeError,         # Base exception — catch-all
)

try:
    result = client.orders.send(account_id, symbol="EURUSD",
                                order_type=0, volume=0.01)
except BrokerRejectionError as e:
    print(f"Broker rejected: retcode={e.retcode}  retryable={e.is_retryable}")
    # e.g. retcode=10019 → "Insufficient margin"
except AuthenticationError:
    print("Check your API key at app.metatraderapi.dev → Settings")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except Api2TradeError as e:
    print(f"API error {e.status_code}: {e}")
```

### OrderType Enum

```python
from api2trade_sdk import OrderType

OrderType.BUY_MARKET   # 0
OrderType.SELL_MARKET  # 1
OrderType.BUY_LIMIT    # 2
OrderType.SELL_LIMIT   # 3
OrderType.BUY_STOP     # 4
OrderType.SELL_STOP    # 5

OrderType.BUY_MARKET.is_market()  # True
OrderType.BUY_LIMIT.is_pending()  # True
```

### RetCode Enum

```python
from api2trade_sdk import RetCode

RetCode.description(10019)     # "Insufficient margin"
RetCode.is_retryable(10004)    # True  (requote)
RetCode.is_retryable(10019)    # False (insufficient funds)
```

---

## Running the Examples

```bash
cd examples/
cp ../.env.example .env
# Edit .env: add API2TRADE_API_KEY and broker credentials

python 01_connect_account.py    # Register account → prints UUID
python 02_account_summary.py    # Live balance table
python 03_place_trade.py        # Open → list → modify → close
python 04_order_history.py      # History + P&L stats
python 05_websocket_stream.py   # Real-time ticks (requires websockets)
python 06_prop_firm_monitor.py  # Drawdown monitor with auto close-out
```

---

## Running Tests

```bash
pip install ".[dev]"
pytest tests/ -v
```

All tests use mocked HTTP — no real API calls or network required.

---

## Project Structure

```
api2trade_sdk/
├── api2trade_sdk/
│   ├── __init__.py          # Public API surface
│   ├── client.py            # Api2TradeClient — main entry point
│   ├── http.py              # HTTP transport (auth, retry, error mapping)
│   ├── streaming.py         # WebSocket client (auto-reconnect)
│   ├── models.py            # Typed dataclass response models
│   ├── enums.py             # OrderType, RetCode
│   ├── exceptions.py        # Exception hierarchy
│   └── resources/
│       ├── accounts.py      # /RegisterAccount /CheckConnect /AccountSummary /DeleteAccount
│       ├── market.py        # /GetQuote
│       ├── orders.py        # /OrderSend /OrderModify /OrderClose /Positions
│       └── history.py       # /OrderHistory /OrderHistoryPagination
├── examples/
│   ├── 01_connect_account.py
│   ├── 02_account_summary.py
│   ├── 03_place_trade.py
│   ├── 04_order_history.py
│   ├── 05_websocket_stream.py
│   └── 06_prop_firm_monitor.py
├── tests/
│   ├── test_models.py
│   ├── test_exceptions.py
│   └── test_resources.py
├── pyproject.toml
├── CHANGELOG.md
├── LICENSE
└── README.md
```

---

## Supported Endpoints

| Endpoint | Method | SDK method |
|----------|--------|------------|
| `/RegisterAccount` | POST | `client.accounts.register()` |
| `/CheckConnect` | GET | `client.accounts.check_connect()` |
| `/AccountSummary` | GET | `client.accounts.summary()` |
| `/DeleteAccount` | DELETE | `client.accounts.delete()` |
| `/GetQuote` | GET | `client.market.quote()` |
| `/OrderSend` | POST | `client.orders.send()` |
| `/OrderModify` | POST | `client.orders.modify()` |
| `/OrderClose` | POST | `client.orders.close()` |
| `/Positions` | GET | `client.orders.positions()` |
| `/OrderHistory` | GET | `client.history.get()` |
| `/OrderHistoryPagination` | GET | `client.history.get_page()` / `iter_all()` |
| `wss://.../stream` | WS | `client.stream()` / `stream_iter()` |

---

## Support

| Channel | Link |
|---------|------|
| 📧 Email | [support@api2trade.com](mailto:support@api2trade.com) |
| 💬 Telegram | [t.me/apisupport_en](https://t.me/apisupport_en) |
| 📖 Docs | [docs.metatraderapi.dev](https://docs.metatraderapi.dev/docs) |
| 🌐 Website | [api2trade.com](https://www.api2trade.com/) |
| 🟢 Status | [status.metatraderapi.dev](https://status.metatraderapi.dev/) |

---

## License

MIT — see [LICENSE](LICENSE).

---

*MetaTrader®, MT4®, and MT5® are trademarks of MetaQuotes Ltd. API2Trade is an independent service and is not affiliated with MetaQuotes Ltd.*
