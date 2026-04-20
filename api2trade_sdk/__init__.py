"""
API2Trade Python SDK
====================
Official Python SDK for the API2Trade MetaTrader REST API.

Website:  https://www.api2trade.com/
Docs:     https://docs.metatraderapi.dev/docs
Support:  support@api2trade.com

Quick start::

    from api2trade_sdk import Api2TradeClient

    client = Api2TradeClient(api_key="YOUR_API_KEY")
    account_id = client.accounts.register(
        login="123456",
        password="BrokerPass",
        server="ICMarkets-Live01",
    )
    summary = client.accounts.summary(account_id)
    print(summary.balance, summary.currency)
"""

from .client import Api2TradeClient
from .exceptions import (
    Api2TradeError,
    AuthenticationError,
    AccountNotFoundError,
    RateLimitError,
    BrokerRejectionError,
    ConnectionError as Api2TradeConnectionError,
)
from .models import (
    AccountSummary,
    Quote,
    Position,
    OrderResult,
    OrderHistoryItem,
    PaginatedHistory,
    ConnectStatus,
)
from .enums import OrderType, RetCode

__version__ = "1.0.0"
__all__ = [
    # Core client
    "Api2TradeClient",
    # Exceptions
    "Api2TradeError",
    "AuthenticationError",
    "AccountNotFoundError",
    "RateLimitError",
    "BrokerRejectionError",
    "Api2TradeConnectionError",
    # Models
    "AccountSummary",
    "Quote",
    "Position",
    "OrderResult",
    "OrderHistoryItem",
    "PaginatedHistory",
    "ConnectStatus",
    # Enums
    "OrderType",
    "RetCode",
]
