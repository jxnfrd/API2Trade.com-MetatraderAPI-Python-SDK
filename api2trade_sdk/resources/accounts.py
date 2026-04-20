"""
AccountsResource — wraps all account-management endpoints.

Endpoints covered:
  POST   /RegisterAccount
  GET    /CheckConnect
  GET    /AccountSummary
  DELETE /DeleteAccount
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..models import RegisteredAccount, ConnectStatus, AccountSummary

if TYPE_CHECKING:
    from ..http import HttpClient

logger = logging.getLogger("api2trade_sdk.accounts")


class AccountsResource:
    """
    Account management operations.

    Access via ``client.accounts``.

    Example::

        account_id = client.accounts.register(
            login="123456",
            password="BrokerPass",
            server="ICMarkets-Live01",
        )
        summary = client.accounts.summary(account_id)
        print(f"Balance: {summary.balance} {summary.currency}")
    """

    def __init__(self, http: "HttpClient") -> None:
        self._http = http

    def register(self, login: str, password: str, server: str) -> str:
        """
        Connect an MT4 or MT5 account to the API2Trade bridge.

        Calls ``POST /RegisterAccount``.

        Args:
            login:    The MetaTrader account number (as a string).
            password: The main trading password (NOT the investor read-only password).
            server:   The exact broker server name as shown in the MT terminal
                      (e.g. ``"ICMarkets-Live01"``, ``"XMGlobal-MT5"``).

        Returns:
            The Account UUID string. **Store this — it is required for all
            subsequent API calls.**

        Raises:
            AuthenticationError: Invalid API key.
            Api2TradeError:      Registration failed (bad credentials / server name).

        Example::

            account_id = client.accounts.register(
                login="123456",
                password="StrongPass!",
                server="ICMarkets-Live01",
            )
        """
        payload = {"login": str(login), "password": password, "server": server}
        logger.info("Registering account login=%s server=%s", login, server)
        data = self._http.post("/RegisterAccount", json=payload)
        result = RegisteredAccount.from_dict(data)
        logger.info("Account registered: id=%s status=%s", result.account_id, result.status)
        return result.account_id

    def register_full(self, login: str, password: str, server: str) -> RegisteredAccount:
        """
        Same as :meth:`register` but returns the full :class:`~api2trade_sdk.models.RegisteredAccount`
        object (including ``status`` field) instead of just the UUID string.
        """
        payload = {"login": str(login), "password": password, "server": server}
        data = self._http.post("/RegisterAccount", json=payload)
        return RegisteredAccount.from_dict(data)

    def check_connect(self, account_id: str) -> ConnectStatus:
        """
        Verify that an account is connected to the broker bridge.

        Calls ``GET /CheckConnect?id=<uuid>``.

        Triggers an automatic reconnection attempt on the server side if the
        connection has dropped. Call this before every trading session.

        Args:
            account_id: The Account UUID returned by :meth:`register`.

        Returns:
            :class:`~api2trade_sdk.models.ConnectStatus`

        Example::

            status = client.accounts.check_connect(account_id)
            if not status.connected:
                print("Bridge is reconnecting — wait a moment and retry")
        """
        logger.debug("CheckConnect id=%s", account_id)
        data = self._http.get("/CheckConnect", params={"id": account_id})
        return ConnectStatus.from_dict(data)

    def summary(self, account_id: str) -> AccountSummary:
        """
        Fetch the live financial state of a connected account.

        Calls ``GET /AccountSummary?id=<uuid>``.

        Args:
            account_id: The Account UUID.

        Returns:
            :class:`~api2trade_sdk.models.AccountSummary` with balance, equity,
            margin, free margin, margin level, and currency.

        Example::

            s = client.accounts.summary(account_id)
            print(f"Balance: {s.balance} {s.currency}")
            print(f"Equity:  {s.equity} {s.currency}")
            if s.is_margin_call_risk:
                print(f"⚠ LOW MARGIN LEVEL: {s.margin_level:.1f}%")
        """
        logger.debug("AccountSummary id=%s", account_id)
        data = self._http.get("/AccountSummary", params={"id": account_id})
        return AccountSummary.from_dict(data)

    def delete(self, account_id: str) -> bool:
        """
        Remove an account from the bridge.

        Calls ``DELETE /DeleteAccount``.

        Args:
            account_id: The Account UUID to remove.

        Returns:
            ``True`` on success.

        .. warning::
            This is irreversible. You will need to call :meth:`register`
            again to re-add the account.
        """
        logger.warning("Deleting account id=%s", account_id)
        self._http.delete("/DeleteAccount", json={"id": account_id})
        return True
