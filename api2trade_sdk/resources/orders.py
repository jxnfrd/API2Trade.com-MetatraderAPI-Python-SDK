"""
OrdersResource — wraps all trade-execution endpoints.

Endpoints covered:
  POST /OrderSend
  POST /OrderModify
  POST /OrderClose
  GET  /Positions
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, List, Optional, Union

from ..models import OrderResult, Position
from ..enums import OrderType, RetCode
from ..exceptions import BrokerRejectionError

if TYPE_CHECKING:
    from ..http import HttpClient

logger = logging.getLogger("api2trade_sdk.orders")

# Default number of auto-retries on retryable broker rejections (requote, etc.)
DEFAULT_RETRY_COUNT = 2
DEFAULT_RETRY_DELAY = 1.0  # seconds


class OrdersResource:
    """
    Trade execution and position-management operations.

    Access via ``client.orders``.

    Example::

        # Get market price first
        q = client.market.quote(account_id, "EURUSD")

        # Place a Buy Market order with 20-pip SL and 40-pip TP
        result = client.orders.send(
            account_id,
            symbol="EURUSD",
            order_type=OrderType.BUY_MARKET,
            volume=0.01,
            stop_loss=round(q.ask - 0.0020, 5),
            take_profit=round(q.ask + 0.0040, 5),
        )
        print(result)   # OrderResult(ticket=12345678, ✅ OK, ...)
    """

    def __init__(self, http: "HttpClient") -> None:
        self._http = http

    # ------------------------------------------------------------------
    # OrderSend
    # ------------------------------------------------------------------

    def send(
        self,
        account_id: str,
        symbol: str,
        order_type: Union[OrderType, int],
        volume: float,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        price: Optional[float] = None,
        comment: str = "api2trade-sdk",
        auto_retry: bool = True,
        max_retries: int = DEFAULT_RETRY_COUNT,
    ) -> OrderResult:
        """
        Open a market or pending order.

        Calls ``POST /OrderSend?id=<uuid>``.

        Args:
            account_id:  Account UUID.
            symbol:      Trading symbol (``"EURUSD"``, ``"XAUUSD"``, …).
            order_type:  :class:`~api2trade_sdk.enums.OrderType` or raw int
                         (0=Buy, 1=Sell, 2=BuyLimit, 3=SellLimit, 4=BuyStop, 5=SellStop).
            volume:      Lot size (e.g. ``0.01`` = 1 micro lot).
            stop_loss:   Absolute SL price level (``0`` = none).
            take_profit: Absolute TP price level (``0`` = none).
            price:       Required for pending orders (Limit/Stop). For market
                         orders the current market price is used automatically.
            comment:     Order comment string (visible in MT terminal journal).
            auto_retry:  If ``True``, automatically retry on retryable broker
                         rejections (requote, timeout, server busy) up to
                         ``max_retries`` times.
            max_retries: Maximum number of automatic retries.

        Returns:
            :class:`~api2trade_sdk.models.OrderResult`

        Raises:
            BrokerRejectionError: Broker rejected the order with a non-zero retcode.
            AuthenticationError:  Invalid API key.
            AccountNotFoundError: Account UUID not registered.

        Example::

            from api2trade_sdk import OrderType

            result = client.orders.send(
                account_id,
                symbol="XAUUSD",
                order_type=OrderType.SELL_LIMIT,
                volume=0.01,
                price=2050.00,
                stop_loss=2060.00,
                take_profit=2020.00,
            )
        """
        payload: dict = {
            "symbol": symbol,
            "operation": int(order_type),
            "volume": volume,
            "stopLoss": stop_loss,
            "takeProfit": take_profit,
            "comment": comment,
        }
        if price is not None:
            payload["price"] = price

        logger.info(
            "OrderSend id=%s symbol=%s op=%s vol=%s",
            account_id, symbol, int(order_type), volume,
        )

        for attempt in range(1, max_retries + 2):  # +2 so we always try at least once
            data = self._http.post("/OrderSend", params={"id": account_id}, json=payload)
            result = OrderResult.from_dict(data)

            if result.success:
                logger.info("Order opened: ticket=%s", result.ticket)
                return result

            retcode = result.retcode
            logger.warning(
                "OrderSend retcode=%s (%s) on attempt %d/%d",
                retcode, RetCode.description(retcode), attempt, max_retries + 1,
            )

            should_retry = auto_retry and RetCode.is_retryable(retcode) and attempt <= max_retries
            if should_retry:
                delay = DEFAULT_RETRY_DELAY * attempt
                logger.info("Retrying in %.1fs (retcode=%s is retryable)…", delay, retcode)
                time.sleep(delay)
                continue

            raise BrokerRejectionError(
                retcode=retcode,
                comment=result.comment,
                response_body=data,
            )

        # Should never reach here, but just in case
        raise BrokerRejectionError(
            retcode=result.retcode,  # type: ignore[possibly-undefined]
            comment=result.comment,  # type: ignore[possibly-undefined]
        )

    # ------------------------------------------------------------------
    # OrderModify
    # ------------------------------------------------------------------

    def modify(
        self,
        account_id: str,
        ticket: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> OrderResult:
        """
        Modify the Stop Loss and/or Take Profit of an open position.

        Calls ``POST /OrderModify?id=<uuid>``.

        Args:
            account_id:  Account UUID.
            ticket:      MetaTrader ticket number of the open position.
            stop_loss:   New SL price level (``None`` = keep current).
            take_profit: New TP price level (``None`` = keep current).

        Returns:
            :class:`~api2trade_sdk.models.OrderResult`

        Raises:
            BrokerRejectionError: Broker rejected the modification.
            ValueError: Both ``stop_loss`` and ``take_profit`` are ``None``.

        Example::

            client.orders.modify(account_id, ticket=12345678, stop_loss=1.0750)
        """
        if stop_loss is None and take_profit is None:
            raise ValueError("Provide at least one of stop_loss or take_profit to modify.")

        payload: dict = {"ticket": ticket}
        if stop_loss is not None:
            payload["stopLoss"] = stop_loss
        if take_profit is not None:
            payload["takeProfit"] = take_profit

        logger.info("OrderModify ticket=%s sl=%s tp=%s", ticket, stop_loss, take_profit)
        data = self._http.post("/OrderModify", params={"id": account_id}, json=payload)
        result = OrderResult.from_dict(data)

        if not result.success:
            raise BrokerRejectionError(
                retcode=result.retcode,
                comment=result.comment,
                response_body=data,
            )
        return result

    # ------------------------------------------------------------------
    # OrderClose
    # ------------------------------------------------------------------

    def close(
        self,
        account_id: str,
        ticket: int,
        volume: Optional[float] = None,
    ) -> OrderResult:
        """
        Close an open position fully or partially.

        Calls ``POST /OrderClose?id=<uuid>``.

        Args:
            account_id: Account UUID.
            ticket:     MetaTrader ticket number of the position to close.
            volume:     Lot size to close. Pass ``None`` or the full lot size to
                        close the entire position. Pass a fraction to partially close.

        Returns:
            :class:`~api2trade_sdk.models.OrderResult`

        Raises:
            BrokerRejectionError: Broker rejected the close request.

        Example::

            # Partially close (0.005 of a 0.01 lot position)
            client.orders.close(account_id, ticket=12345678, volume=0.005)

            # Full close
            client.orders.close(account_id, ticket=12345678)
        """
        payload: dict = {"ticket": ticket}
        if volume is not None:
            payload["volume"] = volume

        logger.info("OrderClose ticket=%s volume=%s", ticket, volume)
        data = self._http.post("/OrderClose", params={"id": account_id}, json=payload)
        result = OrderResult.from_dict(data)

        if not result.success:
            raise BrokerRejectionError(
                retcode=result.retcode,
                comment=result.comment,
                response_body=data,
            )
        return result

    def close_all(self, account_id: str) -> List[OrderResult]:
        """
        Close all currently open positions on the account.

        Fetches positions first via :meth:`positions`, then closes each one.

        Args:
            account_id: Account UUID.

        Returns:
            List of :class:`~api2trade_sdk.models.OrderResult` — one per position closed.

        .. warning::
            This closes **every** open position. Use with caution in production.
        """
        open_positions = self.positions(account_id)
        results = []
        for pos in open_positions:
            logger.info("Closing all: ticket=%s %s %s", pos.ticket, pos.symbol, pos.volume)
            try:
                result = self.close(account_id, ticket=pos.ticket, volume=pos.volume)
                results.append(result)
            except BrokerRejectionError as exc:
                logger.error("Failed to close ticket=%s: %s", pos.ticket, exc)
                raise
        return results

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def positions(self, account_id: str) -> List[Position]:
        """
        Return all currently open positions on the account.

        Calls ``GET /Positions?id=<uuid>``.

        Args:
            account_id: Account UUID.

        Returns:
            List of :class:`~api2trade_sdk.models.Position` objects.
            Returns an empty list if the account has no open positions.

        Example::

            positions = client.orders.positions(account_id)
            total_pnl = sum(p.total_pnl for p in positions)
            print(f"Open positions: {len(positions)}  Total P&L: {total_pnl:.2f}")
        """
        logger.debug("Positions id=%s", account_id)
        data = self._http.get("/Positions", params={"id": account_id})
        if isinstance(data, list):
            return [Position.from_dict(item) for item in data]
        return []
