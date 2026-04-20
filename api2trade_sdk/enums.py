"""
Enumerations for the API2Trade SDK.
"""

from enum import IntEnum


class OrderType(IntEnum):
    """
    Operation codes for ``OrderSend``.

    These map directly to MetaTrader order types.
    """

    BUY_MARKET = 0
    """Open a long position at the current market price."""

    SELL_MARKET = 1
    """Open a short position at the current market price."""

    BUY_LIMIT = 2
    """Place a pending Buy Limit order (trigger when price falls to level)."""

    SELL_LIMIT = 3
    """Place a pending Sell Limit order (trigger when price rises to level)."""

    BUY_STOP = 4
    """Place a pending Buy Stop order (trigger when price breaks above level)."""

    SELL_STOP = 5
    """Place a pending Sell Stop order (trigger when price breaks below level)."""

    def is_market(self) -> bool:
        """Return True for market (instant) order types."""
        return self in (OrderType.BUY_MARKET, OrderType.SELL_MARKET)

    def is_pending(self) -> bool:
        """Return True for pending order types."""
        return self in (
            OrderType.BUY_LIMIT,
            OrderType.SELL_LIMIT,
            OrderType.BUY_STOP,
            OrderType.SELL_STOP,
        )

    def is_buy(self) -> bool:
        return self in (OrderType.BUY_MARKET, OrderType.BUY_LIMIT, OrderType.BUY_STOP)

    def is_sell(self) -> bool:
        return self in (OrderType.SELL_MARKET, OrderType.SELL_LIMIT, OrderType.SELL_STOP)


class RetCode(IntEnum):
    """
    Broker-level ``retcode`` values returned by OrderSend / OrderModify.

    A ``retcode`` of 0 means success. All other values are broker rejection
    or informational codes originating from the MetaTrader server.

    Reference: docs/error_codes.md
    """

    SUCCESS = 0

    REQUOTE = 10004
    """Market moved; safe to retry immediately."""

    REJECTED = 10006
    """Broker rejected; check symbol, volume, and account status."""

    CANCELED = 10007
    """Request timed out; retry."""

    ORDER_PLACED = 10008
    """Async confirmation — order is in broker queue."""

    COMPLETED = 10009
    """Already processed."""

    PARTIAL_FILL = 10010
    """Order only partially executed."""

    PROCESSING_ERROR = 10011
    """Internal broker error; retry."""

    CANCELED_TIMEOUT = 10012
    """Broker timeout; retry with backoff."""

    INVALID_REQUEST = 10013
    """Malformed parameters."""

    INVALID_VOLUME = 10014
    """Volume outside broker min/max for the symbol."""

    INVALID_PRICE = 10015
    """Price out of tradeable range or market is closed."""

    INVALID_STOPS = 10016
    """SL/TP too close to current price."""

    TRADE_DISABLED = 10017
    """Broker has disabled trading for this account."""

    MARKET_CLOSED = 10018
    """Outside trading hours for this symbol."""

    INSUFFICIENT_FUNDS = 10019
    """Not enough free margin."""

    PRICES_CHANGED = 10020
    """Market moved; requote."""

    NO_QUOTES = 10021
    """Broker not streaming prices for this symbol."""

    INVALID_EXPIRATION = 10022
    """Bad expiry time for a pending order."""

    ORDER_CHANGED = 10023
    """Modification race condition."""

    TOO_MANY_REQUESTS = 10024
    """Broker-side rate limit; slow down."""

    NO_CHANGES = 10025
    """Modify request sent with identical values."""

    AUTOTRADING_DISABLED = 10026
    """Check broker/account settings."""

    AGENT_BLOCKED = 10027
    """Contact your broker."""

    ORDER_FROZEN = 10028
    """Order is being processed; wait."""

    INVALID_FILL = 10029
    """Fill mode not supported."""

    NO_CONNECTION = 10030
    """Broker server offline; wait."""

    INSUFFICIENT_RIGHTS = 10031
    """Account permissions issue."""

    TOO_FREQUENT = 10032
    """Broker-side throttle."""

    NO_CHANGES_IN_REQUEST = 10033
    """Duplicate request."""

    SERVER_BUSY = 10034
    """Retry with backoff."""

    ORDER_LOCKED = 10035
    """Order locked by broker."""

    LONG_ONLY = 10036
    """Broker doesn't allow short positions."""

    TOO_MANY_POSITIONS = 10037
    """Account position limit reached."""

    @classmethod
    def is_retryable(cls, code: int) -> bool:
        """Return True if this retcode is safe to retry after a short delay."""
        return code in (
            cls.REQUOTE,
            cls.CANCELED,
            cls.PROCESSING_ERROR,
            cls.CANCELED_TIMEOUT,
            cls.PRICES_CHANGED,
            cls.SERVER_BUSY,
        )

    @classmethod
    def description(cls, code: int) -> str:
        """Return a human-readable description for any retcode."""
        _descriptions = {
            0: "Success",
            10004: "Requote — market moved, retry immediately",
            10006: "Request rejected by broker",
            10007: "Request canceled",
            10008: "Order placed (async)",
            10009: "Request already completed",
            10010: "Partial execution",
            10011: "Broker processing error — retry",
            10012: "Broker timeout — retry with backoff",
            10013: "Invalid request parameters",
            10014: "Invalid volume for this symbol",
            10015: "Invalid price — market may be closed",
            10016: "Invalid stop levels — too close to price",
            10017: "Trading disabled by broker",
            10018: "Market closed",
            10019: "Insufficient margin",
            10020: "Prices changed — requote",
            10021: "No quotes for this symbol",
            10022: "Invalid expiration time",
            10023: "Order changed (race condition)",
            10024: "Too many requests",
            10025: "No changes to apply",
            10026: "Autotrading disabled",
            10027: "Agent is blocked",
            10028: "Order is frozen",
            10029: "Invalid fill mode",
            10030: "No connection to broker",
            10031: "Insufficient account rights",
            10032: "Too frequent requests",
            10033: "No changes in request",
            10034: "Server busy",
            10035: "Order is locked",
            10036: "Long positions only",
            10037: "Too many open positions",
        }
        return _descriptions.get(code, f"Unknown retcode {code}")
