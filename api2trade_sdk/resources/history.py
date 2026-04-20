"""
HistoryResource — wraps trade-history endpoints.

Endpoints covered:
  GET /OrderHistory
  GET /OrderHistoryPagination
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Generator, List, Optional, Union

from ..models import OrderHistoryItem, PaginatedHistory

if TYPE_CHECKING:
    from ..http import HttpClient

logger = logging.getLogger("api2trade_sdk.history")

DateLike = Union[str, datetime]


def _to_iso(dt: DateLike) -> str:
    """Convert a datetime object or ISO string to the format expected by the API."""
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return dt  # already a string — pass through


class HistoryResource:
    """
    Trade history operations.

    Access via ``client.history``.

    Example::

        from datetime import datetime, timedelta

        history = client.history.get(
            account_id,
            date_from=datetime.utcnow() - timedelta(days=30),
            date_to=datetime.utcnow(),
        )
        total_pnl = sum(o.net_profit for o in history)
        print(f"Closed trades: {len(history)}  |  Net P&L: {total_pnl:.2f}")
    """

    def __init__(self, http: "HttpClient") -> None:
        self._http = http

    def get(
        self,
        account_id: str,
        date_from: DateLike,
        date_to: DateLike,
    ) -> List[OrderHistoryItem]:
        """
        Fetch all closed orders in a date range (non-paginated).

        Calls ``GET /OrderHistory?id=<uuid>&dateFrom=<ISO>&dateTo=<ISO>``.

        Best for accounts with moderate trade counts (< ~5 000 per query).
        For large accounts use :meth:`get_page` or :meth:`iter_all`.

        Args:
            account_id: Account UUID.
            date_from:  Start of period — ``datetime`` object or ISO 8601 string.
            date_to:    End of period — ``datetime`` object or ISO 8601 string.

        Returns:
            List of :class:`~api2trade_sdk.models.OrderHistoryItem`.

        Example::

            from datetime import datetime, timedelta, timezone

            history = client.history.get(
                account_id,
                date_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                date_to=datetime(2026, 4, 1, tzinfo=timezone.utc),
            )
        """
        params = {
            "id": account_id,
            "dateFrom": _to_iso(date_from),
            "dateTo": _to_iso(date_to),
        }
        logger.debug("OrderHistory id=%s dateFrom=%s dateTo=%s", account_id, params["dateFrom"], params["dateTo"])
        data = self._http.get("/OrderHistory", params=params)
        if isinstance(data, list):
            return [OrderHistoryItem.from_dict(item) for item in data]
        return []

    def get_page(
        self,
        account_id: str,
        date_from: DateLike,
        date_to: DateLike,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedHistory:
        """
        Fetch a single page of closed-order history.

        Calls ``GET /OrderHistoryPagination``.

        Args:
            account_id: Account UUID.
            date_from:  Start of period.
            date_to:    End of period.
            page:       Page number (1-indexed).
            page_size:  Records per page (max varies by plan — 50 is safe).

        Returns:
            :class:`~api2trade_sdk.models.PaginatedHistory` with ``data``,
            ``total``, ``page``, ``page_size``, ``total_pages``, and
            ``has_next`` properties.

        Example::

            page = client.history.get_page(account_id, date_from, date_to, page=1)
            print(f"Page 1 of {page.total_pages}: {len(page.data)} orders")
        """
        params = {
            "id": account_id,
            "dateFrom": _to_iso(date_from),
            "dateTo": _to_iso(date_to),
            "page": page,
            "pageSize": page_size,
        }
        logger.debug("OrderHistoryPagination id=%s page=%s", account_id, page)
        data = self._http.get("/OrderHistoryPagination", params=params)
        return PaginatedHistory.from_dict(data)

    def iter_all(
        self,
        account_id: str,
        date_from: DateLike,
        date_to: DateLike,
        page_size: int = 50,
    ) -> Generator[OrderHistoryItem, None, None]:
        """
        Iterate over **all** closed orders in a date range, transparently
        handling pagination.

        Uses ``GET /OrderHistoryPagination`` under the hood. Each item is
        yielded as soon as its page is fetched, so memory use is bounded by
        ``page_size`` regardless of total trade count.

        Args:
            account_id: Account UUID.
            date_from:  Start of period.
            date_to:    End of period.
            page_size:  Records to fetch per page.

        Yields:
            :class:`~api2trade_sdk.models.OrderHistoryItem`

        Example::

            winners = [
                o for o in client.history.iter_all(account_id, date_from, date_to)
                if o.net_profit > 0
            ]
            print(f"Winning trades: {len(winners)}")
        """
        page = 1
        while True:
            result = self.get_page(account_id, date_from, date_to, page=page, page_size=page_size)
            for item in result.data:
                yield item
            if not result.has_next:
                break
            page += 1

    def last_n_days(
        self,
        account_id: str,
        days: int = 30,
    ) -> List[OrderHistoryItem]:
        """
        Convenience helper: fetch all closed orders from the past *N* days.

        Args:
            account_id: Account UUID.
            days:       Number of calendar days to look back (default: 30).

        Returns:
            List of :class:`~api2trade_sdk.models.OrderHistoryItem`.

        Example::

            week = client.history.last_n_days(account_id, days=7)
            print(f"Last 7 days: {len(week)} trades")
        """
        now = datetime.now(tz=timezone.utc)
        date_from = now - timedelta(days=days)
        return self.get(account_id, date_from=date_from, date_to=now)

    def summary_stats(
        self,
        account_id: str,
        date_from: DateLike,
        date_to: DateLike,
    ) -> dict:
        """
        Compute a P&L summary dictionary for a date range.

        Calls :meth:`get` internally and aggregates results.

        Returns a dict with keys::

            {
                "total_trades":   int,
                "winning_trades": int,
                "losing_trades":  int,
                "win_rate":       float,   # 0.0–1.0
                "gross_profit":   float,
                "gross_loss":     float,
                "net_profit":     float,
                "profit_factor":  float,   # gross_profit / abs(gross_loss)
                "avg_win":        float,
                "avg_loss":       float,
            }

        Example::

            stats = client.history.summary_stats(account_id, date_from, date_to)
            print(f"Win rate: {stats['win_rate']:.1%}")
            print(f"Profit factor: {stats['profit_factor']:.2f}")
        """
        orders = self.get(account_id, date_from=date_from, date_to=date_to)
        profits = [o.net_profit for o in orders]

        winners = [p for p in profits if p > 0]
        losers  = [p for p in profits if p < 0]

        gross_profit = sum(winners) if winners else 0.0
        gross_loss   = sum(losers)  if losers  else 0.0
        net_profit   = gross_profit + gross_loss

        win_rate      = len(winners) / len(profits) if profits else 0.0
        profit_factor = gross_profit / abs(gross_loss) if gross_loss != 0 else float("inf")
        avg_win       = gross_profit / len(winners) if winners else 0.0
        avg_loss      = gross_loss   / len(losers)  if losers  else 0.0

        return {
            "total_trades":   len(orders),
            "winning_trades": len(winners),
            "losing_trades":  len(losers),
            "win_rate":       round(win_rate, 4),
            "gross_profit":   round(gross_profit, 2),
            "gross_loss":     round(gross_loss, 2),
            "net_profit":     round(net_profit, 2),
            "profit_factor":  round(profit_factor, 4),
            "avg_win":        round(avg_win, 2),
            "avg_loss":       round(avg_loss, 2),
        }
