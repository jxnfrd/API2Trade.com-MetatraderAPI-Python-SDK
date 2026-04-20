"""
WebSocket streaming client for the API2Trade SDK.

Provides real-time bid/ask tick streaming for one or more symbols via the
``wss://api.metatraderapi.dev/stream`` endpoint.

Usage (simple callback style)::

    import asyncio
    from api2trade_sdk import Api2TradeClient

    client = Api2TradeClient(api_key="YOUR_KEY")

    def on_tick(tick):
        print(f"{tick.symbol}: bid={tick.bid:.5f}  ask={tick.ask:.5f}")

    asyncio.run(
        client.stream(
            account_id="YOUR_UUID",
            symbols=["EURUSD", "GBPUSD", "XAUUSD"],
            on_tick=on_tick,
        )
    )

Usage (async generator style)::

    async def main():
        async for tick in client.stream_iter(account_id, ["EURUSD"]):
            print(tick)

    asyncio.run(main())
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, List, Optional, AsyncIterator

from .models import Tick

# websockets is an optional dependency — imported lazily inside each method.
_WS_AVAILABLE = None  # None = unknown, True/False = checked

logger = logging.getLogger("api2trade_sdk.streaming")

# Seconds between automatic reconnect attempts (doubles each time up to MAX)
_BASE_RECONNECT_DELAY = 1.0
_MAX_RECONNECT_DELAY  = 30.0

TickCallback    = Callable[[Tick], None]
ErrorCallback   = Callable[[Exception], None]
ConnectCallback = Callable[[], None]


def _require_websockets() -> None:
    """
    Lazily import websockets and raise a helpful ImportError if it is missing.
    Called only when a stream method is actually invoked.
    """
    try:
        import websockets  # noqa: F401 — just checking presence
    except ImportError:
        raise ImportError(
            "The 'websockets' package is required for streaming.\n"
            "Install it with:  pip install websockets\n"
            "Or:              pip install \"api2trade-sdk[streaming]\""
        )


class StreamingClient:
    """
    Async WebSocket client for real-time price streaming.

    Not normally instantiated directly — use ``client.stream()`` or
    ``client.stream_iter()`` on the main :class:`~api2trade_sdk.client.Api2TradeClient`.

    Args:
        api_key:       API2Trade API key (Single plan).
        pro_username:  Pro plan username (Basic Auth).
        pro_password:  Pro plan password (Basic Auth).
        ws_base_url:   WebSocket base URL override.
        ping_interval: Seconds between WebSocket ping frames (keeps connection alive).
        ping_timeout:  Seconds to wait for pong before assuming disconnect.
        max_reconnects: Maximum number of reconnect attempts (``None`` = infinite).
    """

    DEFAULT_WS_URL = "wss://api.metatraderapi.dev/stream"

    def __init__(
        self,
        api_key: Optional[str] = None,
        pro_username: Optional[str] = None,
        pro_password: Optional[str] = None,
        ws_base_url: Optional[str] = None,
        ping_interval: int = 20,
        ping_timeout: int = 10,
        max_reconnects: Optional[int] = None,
    ) -> None:
        # NOTE: do NOT call _require_websockets() here — keep construction
        # lightweight so the REST-only client works without websockets installed.
        self._api_key       = api_key
        self._pro_username  = pro_username
        self._pro_password  = pro_password
        self._ws_base_url   = (ws_base_url or self.DEFAULT_WS_URL).rstrip("/")
        self._ping_interval = ping_interval
        self._ping_timeout  = ping_timeout
        self._max_reconnects = max_reconnects

    def _build_uri(self, account_id: str) -> str:
        """Build the authenticated WebSocket URI."""
        if self._api_key:
            return f"{self._ws_base_url}?api_key={self._api_key}&id={account_id}"
        # Pro plans: use ?id= only; Basic Auth is passed via websockets extra_headers
        return f"{self._ws_base_url}?id={account_id}"

    def _extra_headers(self) -> dict:
        """Return extra HTTP headers for Pro plan Basic Auth."""
        if self._pro_username and self._pro_password:
            import base64
            credentials = base64.b64encode(
                f"{self._pro_username}:{self._pro_password}".encode()
            ).decode()
            return {"Authorization": f"Basic {credentials}"}
        return {}

    async def stream(
        self,
        account_id: str,
        symbols: List[str],
        on_tick: TickCallback,
        on_error: Optional[ErrorCallback] = None,
        on_connect: Optional[ConnectCallback] = None,
        on_disconnect: Optional[ConnectCallback] = None,
    ) -> None:
        """
        Subscribe to real-time ticks and invoke ``on_tick`` for every quote.

        Automatically reconnects with exponential back-off if the connection
        drops.  Runs **indefinitely** until cancelled or ``max_reconnects``
        is exceeded.

        Args:
            account_id:    Account UUID.
            symbols:       List of symbols to subscribe to.
            on_tick:       Callback invoked with a :class:`~api2trade_sdk.models.Tick`
                           on every new price update.
            on_error:      Optional callback invoked with the exception on errors.
            on_connect:    Optional callback invoked when a (re-)connection succeeds.
            on_disconnect: Optional callback invoked when the connection drops.

        Example::

            def handle_tick(tick):
                if tick.symbol == "EURUSD" and tick.ask > 1.10:
                    print("EURUSD broke 1.10!")

            await client.stream(account_id, ["EURUSD"], on_tick=handle_tick)
        """
        _require_websockets()
        import websockets
        from websockets.exceptions import ConnectionClosed, WebSocketException

        uri          = self._build_uri(account_id)
        headers      = self._extra_headers()
        reconnects   = 0
        delay        = _BASE_RECONNECT_DELAY

        while True:
            try:
                logger.info("Connecting to WebSocket stream… attempt %d", reconnects + 1)
                async with websockets.connect(
                    uri,
                    extra_headers=headers,
                    ping_interval=self._ping_interval,
                    ping_timeout=self._ping_timeout,
                ) as ws:
                    logger.info("WebSocket connected. Subscribing to %s", symbols)
                    reconnects = 0
                    delay      = _BASE_RECONNECT_DELAY

                    await ws.send(json.dumps({"action": "subscribe", "symbols": symbols}))

                    if on_connect:
                        on_connect()

                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            logger.warning("Non-JSON message received: %r", raw)
                            continue

                        msg_type = msg.get("type", "")

                        if msg_type == "quote":
                            on_tick(Tick.from_dict(msg))

                        elif msg_type == "error":
                            logger.error("Server error: %s", msg)
                            exc = RuntimeError(f"Server stream error: {msg}")
                            if on_error:
                                on_error(exc)

                        else:
                            logger.debug("Unhandled message type %r: %s", msg_type, msg)

            except (ConnectionClosed, WebSocketException) as exc:
                logger.warning("WebSocket disconnected: %s", exc)
                if on_disconnect:
                    on_disconnect()
                if on_error:
                    on_error(exc)

            except asyncio.CancelledError:
                logger.info("Stream cancelled.")
                return

            except Exception as exc:
                logger.exception("Unexpected stream error: %s", exc)
                if on_error:
                    on_error(exc)

            # Reconnect logic
            reconnects += 1
            if self._max_reconnects is not None and reconnects > self._max_reconnects:
                logger.error(
                    "Max reconnect attempts (%d) reached. Stopping stream.",
                    self._max_reconnects,
                )
                return

            logger.info("Reconnecting in %.1fs…", delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, _MAX_RECONNECT_DELAY)

    async def stream_iter(
        self,
        account_id: str,
        symbols: List[str],
    ) -> AsyncIterator[Tick]:
        """
        Async generator that yields :class:`~api2trade_sdk.models.Tick` objects.

        Suitable for use in ``async for`` loops. Does **not** auto-reconnect —
        use :meth:`stream` with callbacks for production use.

        Args:
            account_id: Account UUID.
            symbols:    List of symbols to subscribe to.

        Yields:
            :class:`~api2trade_sdk.models.Tick`

        Example::

            async for tick in client.stream_iter(account_id, ["EURUSD"]):
                print(f"{tick.symbol}: {tick.bid:.5f} / {tick.ask:.5f}")
                if some_condition:
                    break
        """
        _require_websockets()
        import websockets

        uri     = self._build_uri(account_id)
        headers = self._extra_headers()

        async with websockets.connect(
            uri,
            extra_headers=headers,
            ping_interval=self._ping_interval,
            ping_timeout=self._ping_timeout,
        ) as ws:
            await ws.send(json.dumps({"action": "subscribe", "symbols": symbols}))
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "quote":
                    yield Tick.from_dict(msg)
