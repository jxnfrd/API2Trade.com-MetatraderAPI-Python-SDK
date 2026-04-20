"""
Main entry point for the API2Trade Python SDK.

Usage::

    from api2trade_sdk import Api2TradeClient

    # Single Account plan (€12/mo)
    client = Api2TradeClient(api_key="YOUR_API_KEY")

    # Pro plans (dedicated URL + Basic Auth)
    client = Api2TradeClient(
        pro_username="your_username",
        pro_password="your_password",
        base_url="https://your-dedicated-url.api2trade.com",
    )

    # Use as a context manager (auto-closes HTTP session)
    with Api2TradeClient(api_key="YOUR_API_KEY") as client:
        summary = client.accounts.summary("ACCOUNT_UUID")
"""

from __future__ import annotations

import logging
import os
from typing import Callable, List, Optional

from .http import HttpClient
from .resources.accounts import AccountsResource
from .resources.market import MarketResource
from .resources.orders import OrdersResource
from .resources.history import HistoryResource
from .streaming import StreamingClient, TickCallback, ErrorCallback, ConnectCallback
from .models import Tick

logger = logging.getLogger("api2trade_sdk")


class Api2TradeClient:
    """
    The top-level API2Trade SDK client.

    All API functionality is accessible through namespaced resource attributes:

    - ``client.accounts``  — :class:`~api2trade_sdk.resources.accounts.AccountsResource`
    - ``client.market``    — :class:`~api2trade_sdk.resources.market.MarketResource`
    - ``client.orders``    — :class:`~api2trade_sdk.resources.orders.OrdersResource`
    - ``client.history``   — :class:`~api2trade_sdk.resources.history.HistoryResource`

    And streaming via ``client.stream()`` / ``client.stream_iter()``.

    Args:
        api_key:        API key for Single Account plan. Can also be supplied
                        via the ``API2TRADE_API_KEY`` environment variable.
        base_url:       REST API base URL. Defaults to
                        ``https://api.metatraderapi.dev``. Pro plan users set
                        this to their dedicated URL.
        ws_url:         WebSocket base URL. Defaults to
                        ``wss://api.metatraderapi.dev/stream``.
        pro_username:   Pro plan Basic Auth username.
        pro_password:   Pro plan Basic Auth password.
        timeout:        ``(connect_timeout, read_timeout)`` tuple in seconds.
                        Default: ``(10, 30)``.
        max_retries:    Number of HTTP retries for transient network errors.
                        Default: ``3``.
        log_level:      Set the SDK logger level (e.g. ``logging.DEBUG``).
                        Default: no change (inherits root logger level).

    Examples::

        # Minimal single-plan usage
        client = Api2TradeClient(api_key="sk-...")

        # From environment variables
        # export API2TRADE_API_KEY=sk-...
        client = Api2TradeClient()

        # Pro plan
        client = Api2TradeClient(
            pro_username="myuser",
            pro_password="mypass",
            base_url="https://dedicated.mybroker.api2trade.com",
        )

        # Context manager
        with Api2TradeClient(api_key="sk-...") as c:
            print(c.accounts.summary("UUID"))
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        ws_url: Optional[str] = None,
        pro_username: Optional[str] = None,
        pro_password: Optional[str] = None,
        timeout: tuple = (10, 30),
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        log_level: Optional[int] = None,
    ) -> None:
        if log_level is not None:
            logging.getLogger("api2trade_sdk").setLevel(log_level)

        # Resolve API key from argument or environment
        resolved_key = api_key or os.environ.get("API2TRADE_API_KEY")
        resolved_base = base_url or os.environ.get("API2TRADE_BASE_URL")
        resolved_ws   = ws_url   or os.environ.get("API2TRADE_WS_URL")

        self._http = HttpClient(
            api_key=resolved_key,
            base_url=resolved_base,
            pro_username=pro_username,
            pro_password=pro_password,
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
        )

        self._streaming = StreamingClient(
            api_key=resolved_key,
            pro_username=pro_username,
            pro_password=pro_password,
            ws_base_url=resolved_ws,
        )

        # Resource namespaces
        self.accounts = AccountsResource(self._http)
        self.market   = MarketResource(self._http)
        self.orders   = OrdersResource(self._http)
        self.history  = HistoryResource(self._http)

        logger.debug("Api2TradeClient initialised (base_url=%s)", self._http.base_url)

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "Api2TradeClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP session and free resources."""
        self._http._session.close()
        logger.debug("Api2TradeClient session closed.")

    # ------------------------------------------------------------------
    # WebSocket streaming helpers (delegate to StreamingClient)
    # ------------------------------------------------------------------

    async def stream(
        self,
        account_id: str,
        symbols: List[str],
        on_tick: TickCallback,
        on_error: Optional[ErrorCallback] = None,
        on_connect: Optional[ConnectCallback] = None,
        on_disconnect: Optional[ConnectCallback] = None,
        max_reconnects: Optional[int] = None,
    ) -> None:
        """
        Stream real-time quotes and invoke ``on_tick`` for every price update.

        Runs indefinitely with automatic reconnect. Must be awaited inside an
        async context (e.g. ``asyncio.run(client.stream(...))``).

        Args:
            account_id:    Account UUID.
            symbols:       List of symbols to subscribe (e.g. ``["EURUSD", "XAUUSD"]``).
            on_tick:       Callable invoked with :class:`~api2trade_sdk.models.Tick`
                           on each price update.
            on_error:      Optional async-safe error handler.
            on_connect:    Optional callback fired on each (re-)connection.
            on_disconnect: Optional callback fired on each disconnect.
            max_reconnects: Override the client-level max reconnect count.

        Example::

            import asyncio
            from api2trade_sdk import Api2TradeClient

            client = Api2TradeClient(api_key="sk-...")

            def on_tick(tick):
                print(tick)

            asyncio.run(client.stream(account_id, ["EURUSD", "XAUUSD"], on_tick=on_tick))
        """
        if max_reconnects is not None:
            self._streaming._max_reconnects = max_reconnects
        await self._streaming.stream(
            account_id=account_id,
            symbols=symbols,
            on_tick=on_tick,
            on_error=on_error,
            on_connect=on_connect,
            on_disconnect=on_disconnect,
        )

    async def stream_iter(self, account_id: str, symbols: List[str]):
        """
        Async generator yielding :class:`~api2trade_sdk.models.Tick` objects.

        Use this inside ``async for`` loops for fine-grained control.

        Example::

            async def main():
                async for tick in client.stream_iter(account_id, ["EURUSD"]):
                    print(tick)
                    if tick.ask > 1.10:
                        break

            asyncio.run(main())
        """
        async for tick in self._streaming.stream_iter(account_id, symbols):
            yield tick

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Api2TradeClient(base_url={self._http.base_url!r})"
