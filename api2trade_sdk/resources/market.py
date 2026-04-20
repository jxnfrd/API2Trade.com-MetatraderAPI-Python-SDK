"""
MarketResource — wraps market-data endpoints.

Endpoints covered:
  GET /GetQuote
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

from ..models import Quote

if TYPE_CHECKING:
    from ..http import HttpClient

logger = logging.getLogger("api2trade_sdk.market")


class MarketResource:
    """
    Live market data operations.

    Access via ``client.market``.

    Example::

        quote = client.market.quote(account_id, "EURUSD")
        print(f"EURUSD  bid={quote.bid}  ask={quote.ask}  spread={quote.spread_pips} pips")
    """

    def __init__(self, http: "HttpClient") -> None:
        self._http = http

    def quote(self, account_id: str, symbol: str) -> Quote:
        """
        Get the current bid/ask price for a symbol.

        Calls ``GET /GetQuote?id=<uuid>&symbol=<symbol>``.

        Args:
            account_id: Account UUID.
            symbol:     Trading symbol (e.g. ``"EURUSD"``, ``"XAUUSD"``, ``"BTCUSD"``).

        Returns:
            :class:`~api2trade_sdk.models.Quote` with ``bid``, ``ask``,
            ``spread``, ``spread_pips``, and ``mid`` properties.

        Example::

            q = client.market.quote(account_id, "XAUUSD")
            print(f"Gold: {q.bid:.2f} / {q.ask:.2f}")
        """
        logger.debug("GetQuote id=%s symbol=%s", account_id, symbol)
        data = self._http.get("/GetQuote", params={"id": account_id, "symbol": symbol})
        return Quote.from_dict(data)

    def quotes(self, account_id: str, symbols: List[str]) -> List[Quote]:
        """
        Fetch live quotes for multiple symbols sequentially.

        This is a convenience wrapper that calls :meth:`quote` once per symbol.
        For real-time streaming of multiple symbols simultaneously, use the
        WebSocket stream via ``client.stream()``.

        Args:
            account_id: Account UUID.
            symbols:    List of symbol strings.

        Returns:
            List of :class:`~api2trade_sdk.models.Quote` objects, in the same
            order as ``symbols``.

        Example::

            quotes = client.market.quotes(account_id, ["EURUSD", "GBPUSD", "XAUUSD"])
            for q in quotes:
                print(q)
        """
        results = []
        for symbol in symbols:
            results.append(self.quote(account_id, symbol))
        return results
