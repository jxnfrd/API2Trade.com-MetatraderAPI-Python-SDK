"""
Integration-style unit tests for resource modules using mocked HTTP.

Each test patches the underlying HttpClient so no real network calls are made.

Run with:  pytest tests/test_resources.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call
import pytest

from api2trade_sdk import Api2TradeClient
from api2trade_sdk.exceptions import BrokerRejectionError, AccountNotFoundError
from api2trade_sdk.enums import OrderType, RetCode
from api2trade_sdk.models import (
    AccountSummary,
    ConnectStatus,
    OrderResult,
    PaginatedHistory,
    Position,
    Quote,
    RegisteredAccount,
)


ACCOUNT_ID = "a1b2c3d4-0000-0000-0000-000000000000"


@pytest.fixture
def client():
    """Return a client with a mocked HTTP session so no real requests fire."""
    with patch("api2trade_sdk.http._build_session"):
        c = Api2TradeClient(api_key="test-key-123")
        yield c


# ---------------------------------------------------------------------------
# AccountsResource
# ---------------------------------------------------------------------------

class TestAccountsResource:
    def test_register_returns_uuid(self, client):
        client._http.post = MagicMock(return_value={"id": ACCOUNT_ID, "status": "connected"})

        result = client.accounts.register("123456", "pass", "Broker-Live01")

        client._http.post.assert_called_once_with(
            "/RegisterAccount",
            json={"login": "123456", "password": "pass", "server": "Broker-Live01"},
        )
        assert result == ACCOUNT_ID

    def test_register_full_returns_model(self, client):
        client._http.post = MagicMock(return_value={"id": ACCOUNT_ID, "status": "connected"})
        result = client.accounts.register_full("123456", "pass", "Broker-Live01")
        assert isinstance(result, RegisteredAccount)
        assert result.account_id == ACCOUNT_ID

    def test_check_connect(self, client):
        client._http.get = MagicMock(return_value={"connected": True, "id": ACCOUNT_ID})
        status = client.accounts.check_connect(ACCOUNT_ID)
        assert isinstance(status, ConnectStatus)
        assert status.connected is True

    def test_summary(self, client):
        client._http.get = MagicMock(return_value={
            "balance": 10000.0, "equity": 9900.0, "margin": 100.0,
            "freeMargin": 9800.0, "marginLevel": 9900.0, "currency": "USD",
        })
        s = client.accounts.summary(ACCOUNT_ID)
        assert isinstance(s, AccountSummary)
        assert s.balance == 10000.0
        assert s.currency == "USD"

    def test_delete_returns_true(self, client):
        client._http.delete = MagicMock(return_value={})
        assert client.accounts.delete(ACCOUNT_ID) is True
        client._http.delete.assert_called_once_with("/DeleteAccount", json={"id": ACCOUNT_ID})


# ---------------------------------------------------------------------------
# MarketResource
# ---------------------------------------------------------------------------

class TestMarketResource:
    def test_quote(self, client):
        client._http.get = MagicMock(return_value={
            "symbol": "EURUSD", "bid": 1.08500, "ask": 1.08510,
        })
        q = client.market.quote(ACCOUNT_ID, "EURUSD")
        assert isinstance(q, Quote)
        assert q.symbol == "EURUSD"
        client._http.get.assert_called_once_with(
            "/GetQuote", params={"id": ACCOUNT_ID, "symbol": "EURUSD"}
        )

    def test_quotes_calls_quote_multiple_times(self, client):
        responses = [
            {"symbol": "EURUSD", "bid": 1.085, "ask": 1.086},
            {"symbol": "GBPUSD", "bid": 1.270, "ask": 1.271},
        ]
        client._http.get = MagicMock(side_effect=responses)
        quotes = client.market.quotes(ACCOUNT_ID, ["EURUSD", "GBPUSD"])
        assert len(quotes) == 2
        assert quotes[0].symbol == "EURUSD"
        assert quotes[1].symbol == "GBPUSD"


# ---------------------------------------------------------------------------
# OrdersResource
# ---------------------------------------------------------------------------

class TestOrdersResource:
    def _order_response(self, ticket=12345678, retcode=0, comment="OK"):
        return {"ticket": ticket, "retcode": retcode, "comment": comment}

    def test_send_success(self, client):
        client._http.post = MagicMock(return_value=self._order_response())
        result = client.orders.send(
            ACCOUNT_ID, symbol="EURUSD",
            order_type=OrderType.BUY_MARKET, volume=0.01,
        )
        assert isinstance(result, OrderResult)
        assert result.success is True
        assert result.ticket == 12345678

    def test_send_raises_broker_rejection(self, client):
        client._http.post = MagicMock(
            return_value=self._order_response(ticket=0, retcode=10019, comment="No margin")
        )
        with pytest.raises(BrokerRejectionError) as exc_info:
            client.orders.send(
                ACCOUNT_ID, symbol="EURUSD",
                order_type=OrderType.BUY_MARKET, volume=0.01,
                auto_retry=False,
            )
        assert exc_info.value.retcode == 10019

    def test_send_auto_retries_on_requote(self, client):
        """Should retry on retcode 10004 (requote) and succeed on second call."""
        responses = [
            self._order_response(ticket=0, retcode=RetCode.REQUOTE, comment="Requote"),
            self._order_response(ticket=99, retcode=0, comment="OK"),
        ]
        client._http.post = MagicMock(side_effect=responses)

        with patch("time.sleep"):  # don't actually sleep in tests
            result = client.orders.send(
                ACCOUNT_ID, symbol="EURUSD",
                order_type=OrderType.BUY_MARKET, volume=0.01,
                auto_retry=True, max_retries=1,
            )
        assert result.ticket == 99
        assert client._http.post.call_count == 2

    def test_send_raises_after_max_retries_exhausted(self, client):
        requote = self._order_response(ticket=0, retcode=RetCode.REQUOTE, comment="Requote")
        client._http.post = MagicMock(return_value=requote)
        with patch("time.sleep"):
            with pytest.raises(BrokerRejectionError) as exc_info:
                client.orders.send(
                    ACCOUNT_ID, symbol="EURUSD",
                    order_type=OrderType.BUY_MARKET, volume=0.01,
                    auto_retry=True, max_retries=2,
                )
        assert exc_info.value.retcode == RetCode.REQUOTE
        assert client._http.post.call_count == 3  # 1 initial + 2 retries

    def test_modify_success(self, client):
        client._http.post = MagicMock(return_value=self._order_response())
        result = client.orders.modify(ACCOUNT_ID, ticket=1, stop_loss=1.07)
        assert result.success is True

    def test_modify_raises_if_no_sl_or_tp(self, client):
        with pytest.raises(ValueError, match="stop_loss or take_profit"):
            client.orders.modify(ACCOUNT_ID, ticket=1)

    def test_modify_raises_broker_rejection(self, client):
        client._http.post = MagicMock(
            return_value=self._order_response(retcode=10025, comment="No changes")
        )
        with pytest.raises(BrokerRejectionError):
            client.orders.modify(ACCOUNT_ID, ticket=1, stop_loss=1.07)

    def test_close_success(self, client):
        client._http.post = MagicMock(return_value=self._order_response())
        result = client.orders.close(ACCOUNT_ID, ticket=12345678, volume=0.01)
        assert result.success is True

    def test_close_raises_broker_rejection(self, client):
        client._http.post = MagicMock(
            return_value=self._order_response(retcode=10028, comment="Frozen")
        )
        with pytest.raises(BrokerRejectionError):
            client.orders.close(ACCOUNT_ID, ticket=1)

    def test_positions_returns_list(self, client):
        client._http.get = MagicMock(return_value=[
            {
                "ticket": 1, "symbol": "EURUSD", "type": "buy",
                "volume": 0.01, "openPrice": 1.08, "stopLoss": 1.07,
                "takeProfit": 1.10, "profit": 10.0, "swap": 0.0,
            }
        ])
        positions = client.orders.positions(ACCOUNT_ID)
        assert len(positions) == 1
        assert isinstance(positions[0], Position)

    def test_positions_empty_returns_empty_list(self, client):
        client._http.get = MagicMock(return_value=[])
        positions = client.orders.positions(ACCOUNT_ID)
        assert positions == []

    def test_close_all(self, client):
        client._http.get = MagicMock(return_value=[
            {"ticket": 1, "symbol": "EURUSD", "type": "buy", "volume": 0.01,
             "openPrice": 1.08, "stopLoss": 0, "takeProfit": 0, "profit": 0, "swap": 0},
            {"ticket": 2, "symbol": "GBPUSD", "type": "sell", "volume": 0.02,
             "openPrice": 1.27, "stopLoss": 0, "takeProfit": 0, "profit": 0, "swap": 0},
        ])
        client._http.post = MagicMock(return_value=self._order_response())
        results = client.orders.close_all(ACCOUNT_ID)
        assert len(results) == 2
        assert client._http.post.call_count == 2


# ---------------------------------------------------------------------------
# HistoryResource
# ---------------------------------------------------------------------------

class TestHistoryResource:
    ITEM = {
        "ticket": 1, "symbol": "EURUSD", "type": "buy", "volume": 0.01,
        "openPrice": 1.08, "closePrice": 1.09, "openTime": "2026-01-01T00:00:00Z",
        "closeTime": "2026-01-02T00:00:00Z", "profit": 100.0, "swap": -1.0,
        "commission": -0.5,
    }

    def test_get_returns_list(self, client):
        client._http.get = MagicMock(return_value=[self.ITEM])
        history = client.history.get(ACCOUNT_ID, "2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z")
        assert len(history) == 1
        assert history[0].symbol == "EURUSD"

    def test_get_empty(self, client):
        client._http.get = MagicMock(return_value=[])
        history = client.history.get(ACCOUNT_ID, "2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z")
        assert history == []

    def test_get_page(self, client):
        client._http.get = MagicMock(return_value={
            "data": [self.ITEM],
            "total": 100, "page": 1, "pageSize": 50,
        })
        result = client.history.get_page(ACCOUNT_ID, "2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z")
        assert isinstance(result, PaginatedHistory)
        assert result.total == 100
        assert len(result.data) == 1

    def test_iter_all_single_page(self, client):
        client._http.get = MagicMock(return_value={
            "data": [self.ITEM, self.ITEM],
            "total": 2, "page": 1, "pageSize": 50,
        })
        items = list(client.history.iter_all(ACCOUNT_ID, "2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z"))
        assert len(items) == 2

    def test_iter_all_multiple_pages(self, client):
        page1 = {"data": [self.ITEM] * 2, "total": 4, "page": 1, "pageSize": 2}
        page2 = {"data": [self.ITEM] * 2, "total": 4, "page": 2, "pageSize": 2}
        client._http.get = MagicMock(side_effect=[page1, page2])
        items = list(client.history.iter_all(
            ACCOUNT_ID, "2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z", page_size=2
        ))
        assert len(items) == 4
        assert client._http.get.call_count == 2

    def test_last_n_days(self, client):
        client._http.get = MagicMock(return_value=[self.ITEM])
        result = client.history.last_n_days(ACCOUNT_ID, days=7)
        assert len(result) == 1
        call_params = client._http.get.call_args[1]["params"]
        assert "dateFrom" in call_params

    def test_summary_stats(self, client):
        winning = {**self.ITEM, "profit": 100.0, "swap": 0.0, "commission": 0.0}
        losing  = {**self.ITEM, "profit": -40.0, "swap": 0.0, "commission": 0.0}
        client._http.get = MagicMock(return_value=[winning, winning, losing])
        stats = client.history.summary_stats(ACCOUNT_ID, "2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z")

        assert stats["total_trades"] == 3
        assert stats["winning_trades"] == 2
        assert stats["losing_trades"] == 1
        assert stats["net_profit"] == pytest.approx(160.0, abs=0.01)
        assert stats["win_rate"] == pytest.approx(2/3, abs=0.01)
        assert stats["profit_factor"] == pytest.approx(200.0 / 40.0, abs=0.01)


# ---------------------------------------------------------------------------
# Client-level integration
# ---------------------------------------------------------------------------

class TestClientSetup:
    def test_context_manager(self):
        with patch("api2trade_sdk.http._build_session"):
            with Api2TradeClient(api_key="key") as c:
                assert c.accounts is not None
                assert c.market   is not None
                assert c.orders   is not None
                assert c.history  is not None

    def test_repr(self):
        with patch("api2trade_sdk.http._build_session"):
            c = Api2TradeClient(api_key="key")
            assert "Api2TradeClient" in repr(c)

    def test_missing_credentials_raises(self):
        with pytest.raises(ValueError, match="api_key"):
            with patch("api2trade_sdk.http._build_session"):
                with patch.dict("os.environ", {}, clear=True):
                    Api2TradeClient()
