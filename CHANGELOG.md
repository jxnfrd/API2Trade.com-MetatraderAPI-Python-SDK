# Changelog

All notable changes to the **API2Trade Python SDK** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-04-20

### Added
- `Api2TradeClient` — single entry point for all API operations
- `AccountsResource` — `register()`, `register_full()`, `check_connect()`, `summary()`, `delete()`
- `MarketResource` — `quote()`, `quotes()` (multi-symbol convenience)
- `OrdersResource` — `send()`, `modify()`, `close()`, `close_all()`, `positions()`
  - Automatic retry with exponential back-off on retryable broker rejections (requote, server busy, etc.)
- `HistoryResource` — `get()`, `get_page()`, `iter_all()`, `last_n_days()`, `summary_stats()`
- `StreamingClient` — async WebSocket client with auto-reconnect and ping/pong keepalive
  - Callback style via `client.stream()`
  - Async generator style via `client.stream_iter()`
- Typed models: `AccountSummary`, `Quote`, `Position`, `OrderResult`, `OrderHistoryItem`, `PaginatedHistory`, `ConnectStatus`, `Tick`
- `OrderType` enum (BUY_MARKET, SELL_MARKET, BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP)
- `RetCode` enum with all 37 broker return codes + `is_retryable()` + `description()` helpers
- Exception hierarchy: `Api2TradeError` → `AuthenticationError`, `AccountNotFoundError`, `RateLimitError`, `ServerError`, `ConnectionError`, `BrokerRejectionError`
- HTTP transport: connection pooling, session reuse, configurable timeouts and retries
- Pro plan Basic Auth support alongside Single plan API key auth
- Environment variable configuration (`API2TRADE_API_KEY`, `API2TRADE_ACCOUNT_ID`, etc.)
- Context manager support (`with Api2TradeClient(...) as client:`)
- 6 runnable examples covering every major use case
- Full unit test suite (models, exceptions, all resources) with mocked HTTP
