"""
Typed response models for the API2Trade SDK.

All models are plain Python dataclasses with no runtime dependencies.
They are constructed from raw API JSON dicts via ``Model.from_dict()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Account models
# ---------------------------------------------------------------------------


@dataclass
class ConnectStatus:
    """
    Response from ``GET /CheckConnect``.

    Attributes:
        connected: True if the MT4/MT5 bridge is currently live.
        account_id: The account UUID.
    """

    connected: bool
    account_id: str

    @classmethod
    def from_dict(cls, data: dict) -> "ConnectStatus":
        return cls(
            connected=data.get("connected", False),
            account_id=data.get("id", ""),
        )

    def __str__(self) -> str:
        status = "✅ Connected" if self.connected else "❌ Disconnected"
        return f"ConnectStatus({status}, id={self.account_id})"


@dataclass
class RegisteredAccount:
    """
    Response from ``POST /RegisterAccount``.

    Attributes:
        account_id: UUID to use in all subsequent requests.
        status:     Raw status string returned by the bridge.
    """

    account_id: str
    status: str

    @classmethod
    def from_dict(cls, data: dict) -> "RegisteredAccount":
        return cls(
            account_id=data.get("id", ""),
            status=data.get("status", ""),
        )

    def __str__(self) -> str:
        return f"RegisteredAccount(id={self.account_id}, status={self.status!r})"


@dataclass
class AccountSummary:
    """
    Response from ``GET /AccountSummary``.

    Attributes:
        balance:      Settled cash balance.
        equity:       Balance + floating P&L.
        margin:       Margin currently used.
        free_margin:  Available margin for new trades.
        margin_level: equity / margin * 100. Margin call risk indicator.
        currency:     Account currency code (e.g. ``"USD"``).
    """

    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    currency: str

    @classmethod
    def from_dict(cls, data: dict) -> "AccountSummary":
        return cls(
            balance=float(data.get("balance", 0)),
            equity=float(data.get("equity", 0)),
            margin=float(data.get("margin", 0)),
            free_margin=float(data.get("freeMargin", 0)),
            margin_level=float(data.get("marginLevel", 0)),
            currency=data.get("currency", ""),
        )

    @property
    def is_margin_call_risk(self) -> bool:
        """True when margin level drops below 150% — common danger zone."""
        return 0 < self.margin_level < 150

    def __str__(self) -> str:
        return (
            f"AccountSummary("
            f"balance={self.balance:.2f}, equity={self.equity:.2f}, "
            f"free_margin={self.free_margin:.2f}, "
            f"margin_level={self.margin_level:.1f}%, "
            f"currency={self.currency!r})"
        )


# ---------------------------------------------------------------------------
# Market data models
# ---------------------------------------------------------------------------


@dataclass
class Quote:
    """
    Response from ``GET /GetQuote``.

    Attributes:
        symbol: Trading symbol (e.g. ``"EURUSD"``).
        bid:    Current bid price.
        ask:    Current ask price.
    """

    symbol: str
    bid: float
    ask: float

    @classmethod
    def from_dict(cls, data: dict) -> "Quote":
        return cls(
            symbol=data.get("symbol", ""),
            bid=float(data.get("bid", 0)),
            ask=float(data.get("ask", 0)),
        )

    @property
    def spread(self) -> float:
        """Spread in price units (ask - bid)."""
        return round(self.ask - self.bid, 6)

    @property
    def spread_pips(self) -> float:
        """Spread in pips for 5-decimal FX pairs (multiply by 100 000)."""
        return round(self.spread * 100_000, 1)

    @property
    def mid(self) -> float:
        """Mid price (average of bid and ask)."""
        return round((self.bid + self.ask) / 2, 6)

    def __str__(self) -> str:
        return (
            f"Quote({self.symbol}: bid={self.bid:.5f}, ask={self.ask:.5f}, "
            f"spread={self.spread_pips:.1f} pips)"
        )


# ---------------------------------------------------------------------------
# Trade / position models
# ---------------------------------------------------------------------------


@dataclass
class OrderResult:
    """
    Response from ``POST /OrderSend``, ``/OrderModify``, or ``/OrderClose``.

    Attributes:
        ticket:  MetaTrader ticket number (0 if the order was rejected).
        retcode: Broker return code (0 = success).
        comment: Broker text comment.
    """

    ticket: int
    retcode: int
    comment: str

    @classmethod
    def from_dict(cls, data: dict) -> "OrderResult":
        return cls(
            ticket=int(data.get("ticket", 0)),
            retcode=int(data.get("retcode", -1)),
            comment=data.get("comment", ""),
        )

    @property
    def success(self) -> bool:
        """True when retcode == 0."""
        return self.retcode == 0

    def __str__(self) -> str:
        status = "✅ OK" if self.success else f"❌ retcode={self.retcode}"
        return f"OrderResult(ticket={self.ticket}, {status}, comment={self.comment!r})"


@dataclass
class Position:
    """
    A single open position from ``GET /Positions``.

    Attributes:
        ticket:      MetaTrader ticket number.
        symbol:      Trading symbol.
        order_type:  ``"buy"`` or ``"sell"``.
        volume:      Lot size.
        open_price:  Entry price.
        stop_loss:   Current SL price level (0 if none).
        take_profit: Current TP price level (0 if none).
        profit:      Floating P&L in account currency.
        swap:        Accumulated swap charges.
        comment:     Order comment string.
    """

    ticket: int
    symbol: str
    order_type: str
    volume: float
    open_price: float
    stop_loss: float
    take_profit: float
    profit: float
    swap: float
    comment: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        return cls(
            ticket=int(data.get("ticket", 0)),
            symbol=data.get("symbol", ""),
            order_type=data.get("type", ""),
            volume=float(data.get("volume", 0)),
            open_price=float(data.get("openPrice", 0)),
            stop_loss=float(data.get("stopLoss", 0)),
            take_profit=float(data.get("takeProfit", 0)),
            profit=float(data.get("profit", 0)),
            swap=float(data.get("swap", 0)),
            comment=data.get("comment", ""),
        )

    @property
    def total_pnl(self) -> float:
        """Total P&L including swap."""
        return round(self.profit + self.swap, 2)

    def __str__(self) -> str:
        direction = "↑ BUY" if "buy" in self.order_type.lower() else "↓ SELL"
        pnl_str = f"+{self.total_pnl:.2f}" if self.total_pnl >= 0 else f"{self.total_pnl:.2f}"
        return (
            f"Position(#{self.ticket} {direction} {self.volume} {self.symbol} "
            f"@ {self.open_price} | P&L: {pnl_str})"
        )


# ---------------------------------------------------------------------------
# History models
# ---------------------------------------------------------------------------


@dataclass
class OrderHistoryItem:
    """
    A single closed order from ``GET /OrderHistory``.

    Attributes:
        ticket:      MetaTrader ticket number.
        symbol:      Trading symbol.
        order_type:  ``"buy"`` or ``"sell"``.
        volume:      Lot size.
        open_price:  Entry price.
        close_price: Exit price.
        open_time:   ISO 8601 open timestamp (string).
        close_time:  ISO 8601 close timestamp (string).
        profit:      Realized P&L in account currency.
        swap:        Swap charges.
        commission:  Commission charged.
        comment:     Order comment.
    """

    ticket: int
    symbol: str
    order_type: str
    volume: float
    open_price: float
    close_price: float
    open_time: str
    close_time: str
    profit: float
    swap: float
    commission: float
    comment: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "OrderHistoryItem":
        return cls(
            ticket=int(data.get("ticket", 0)),
            symbol=data.get("symbol", ""),
            order_type=data.get("type", ""),
            volume=float(data.get("volume", 0)),
            open_price=float(data.get("openPrice", 0)),
            close_price=float(data.get("closePrice", 0)),
            open_time=data.get("openTime", ""),
            close_time=data.get("closeTime", ""),
            profit=float(data.get("profit", 0)),
            swap=float(data.get("swap", 0)),
            commission=float(data.get("commission", 0)),
            comment=data.get("comment", ""),
        )

    @property
    def net_profit(self) -> float:
        """Profit after swap and commission."""
        return round(self.profit + self.swap + self.commission, 2)

    def __str__(self) -> str:
        net = f"+{self.net_profit:.2f}" if self.net_profit >= 0 else f"{self.net_profit:.2f}"
        return (
            f"OrderHistoryItem(#{self.ticket} {self.symbol} {self.order_type} "
            f"{self.volume} lots | net={net} | closed={self.close_time})"
        )


@dataclass
class PaginatedHistory:
    """
    Response from ``GET /OrderHistoryPagination``.

    Attributes:
        data:      List of closed orders on this page.
        total:     Total number of closed orders in the date range.
        page:      Current page number (1-indexed).
        page_size: Number of records per page.
    """

    data: List[OrderHistoryItem]
    total: int
    page: int
    page_size: int

    @classmethod
    def from_dict(cls, raw: dict) -> "PaginatedHistory":
        items = [OrderHistoryItem.from_dict(item) for item in raw.get("data", [])]
        return cls(
            data=items,
            total=int(raw.get("total", 0)),
            page=int(raw.get("page", 1)),
            page_size=int(raw.get("pageSize", 50)),
        )

    @property
    def total_pages(self) -> int:
        """Total number of pages for this result set."""
        if self.page_size == 0:
            return 0
        import math
        return math.ceil(self.total / self.page_size)

    @property
    def has_next(self) -> bool:
        """True if there are more pages to fetch."""
        return self.page < self.total_pages

    def __str__(self) -> str:
        return (
            f"PaginatedHistory(page={self.page}/{self.total_pages}, "
            f"items={len(self.data)}/{self.total})"
        )


# ---------------------------------------------------------------------------
# WebSocket tick model
# ---------------------------------------------------------------------------


@dataclass
class Tick:
    """
    A single real-time price tick from the WebSocket stream.

    Attributes:
        symbol: Trading symbol.
        bid:    Current bid price.
        ask:    Current ask price.
        type:   Message type (usually ``"quote"``).
    """

    symbol: str
    bid: float
    ask: float
    type: str = "quote"

    @classmethod
    def from_dict(cls, data: dict) -> "Tick":
        return cls(
            symbol=data.get("symbol", ""),
            bid=float(data.get("bid", 0)),
            ask=float(data.get("ask", 0)),
            type=data.get("type", "quote"),
        )

    @property
    def spread_pips(self) -> float:
        return round((self.ask - self.bid) * 100_000, 1)

    def __str__(self) -> str:
        return (
            f"Tick({self.symbol}: bid={self.bid:.5f}, ask={self.ask:.5f}, "
            f"spread={self.spread_pips:.1f} pips)"
        )
