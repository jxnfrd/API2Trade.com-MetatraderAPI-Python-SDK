"""
Exceptions raised by the API2Trade SDK.

Exception hierarchy::

    Api2TradeError
    ├── AuthenticationError    (HTTP 401)
    ├── AccountNotFoundError   (HTTP 404)
    ├── RateLimitError         (HTTP 429)
    ├── ServerError            (HTTP 5xx)
    ├── ConnectionError        (network / timeout)
    └── BrokerRejectionError   (HTTP 200 but retcode != 0)
"""

from __future__ import annotations
from typing import Optional


class Api2TradeError(Exception):
    """
    Base exception for all API2Trade SDK errors.

    Every exception carries an optional ``status_code`` (HTTP status) and
    ``response_body`` (raw JSON response dict) for detailed introspection.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body or {}

    def __repr__(self) -> str:  # pragma: no cover
        return f"{type(self).__name__}(message={self.message!r}, status_code={self.status_code})"


class AuthenticationError(Api2TradeError):
    """
    Raised when the API key is missing, invalid, or expired (HTTP 401).

    Verify your ``api_key`` in the API2Trade dashboard:
    https://app.metatraderapi.dev → Settings
    """


class AccountNotFoundError(Api2TradeError):
    """
    Raised when the account UUID is not registered on the bridge (HTTP 404).

    Call ``client.accounts.register(...)`` first to obtain a valid UUID.
    """

    def __init__(
        self,
        account_id: str,
        status_code: Optional[int] = 404,
        response_body: Optional[dict] = None,
    ) -> None:
        super().__init__(
            f"Account '{account_id}' not found. Register the account first via "
            f"client.accounts.register(login, password, server).",
            status_code=status_code,
            response_body=response_body,
        )
        self.account_id = account_id


class RateLimitError(Api2TradeError):
    """
    Raised when the Single Account plan rate limit is hit (HTTP 429).

    Implement exponential backoff or upgrade to a Pro plan for unlimited requests.
    The ``retry_after`` attribute holds the suggested wait time in seconds (if provided).
    """

    def __init__(
        self,
        retry_after: Optional[int] = None,
        status_code: int = 429,
        response_body: Optional[dict] = None,
    ) -> None:
        msg = "Rate limit exceeded."
        if retry_after:
            msg += f" Retry after {retry_after}s."
        super().__init__(msg, status_code=status_code, response_body=response_body)
        self.retry_after = retry_after


class ServerError(Api2TradeError):
    """
    Raised on HTTP 5xx responses from the API2Trade servers.

    If this persists, contact support@api2trade.com or check
    https://status.metatraderapi.dev/
    """


class ConnectionError(Api2TradeError):  # noqa: A001
    """
    Raised when a network-level error occurs (DNS failure, timeout, SSL error, etc.).

    The underlying ``requests`` exception is available via ``__cause__``.
    """


class BrokerRejectionError(Api2TradeError):
    """
    Raised when the API returns HTTP 200 but the broker rejected the trade
    (i.e., ``retcode != 0``).

    Attributes:
        retcode:  The MetaTrader broker return code.
        comment:  The broker's text comment explaining the rejection.
        is_retryable: True if the rejection is transient and safe to retry.

    Example::

        try:
            result = client.orders.send(account_id, symbol="EURUSD", ...)
        except BrokerRejectionError as e:
            if e.is_retryable:
                time.sleep(1)
                # retry ...
            elif e.retcode == RetCode.INSUFFICIENT_FUNDS:
                print("Not enough margin — reduce lot size")
    """

    def __init__(
        self,
        retcode: int,
        comment: str = "",
        response_body: Optional[dict] = None,
    ) -> None:
        from .enums import RetCode  # local import to avoid circular

        description = RetCode.description(retcode)
        msg = f"Broker rejection retcode={retcode}: {description}"
        if comment:
            msg += f" (broker comment: {comment!r})"
        super().__init__(msg, status_code=200, response_body=response_body)
        self.retcode = retcode
        self.comment = comment
        self.is_retryable = RetCode.is_retryable(retcode)
