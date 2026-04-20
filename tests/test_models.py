"""
Unit tests for SDK models.

Run with:  pytest tests/test_models.py -v
"""

import math
import pytest

from api2trade_sdk.models import (
    AccountSummary,
    ConnectStatus,
    OrderHistoryItem,
    OrderResult,
    PaginatedHistory,
    Position,
    Quote,
    RegisteredAccount,
    Tick,
)


# ---------------------------------------------------------------------------
# ConnectStatus
# ---------------------------------------------------------------------------

class TestConnectStatus:
    def test_from_dict_connected(self):
        s = ConnectStatus.from_dict({"connected": True, "id": "abc-123"})
        assert s.connected is True
        assert s.account_id == "abc-123"

    def test_from_dict_disconnected(self):
        s = ConnectStatus.from_dict({"connected": False, "id": "xyz"})
        assert s.connected is False

    def test_str_connected(self):
        s = ConnectStatus.from_dict({"connected": True, "id": "x"})
        assert "Connected" in str(s)

    def test_str_disconnected(self):
        s = ConnectStatus.from_dict({"connected": False, "id": "x"})
        assert "Disconnected" in str(s)

    def test_missing_fields_default(self):
        s = ConnectStatus.from_dict({})
        assert s.connected is False
        assert s.account_id == ""


# ---------------------------------------------------------------------------
# RegisteredAccount
# ---------------------------------------------------------------------------

class TestRegisteredAccount:
    def test_from_dict(self):
        r = RegisteredAccount.from_dict({"id": "uuid-1", "status": "connected"})
        assert r.account_id == "uuid-1"
        assert r.status == "connected"

    def test_str(self):
        r = RegisteredAccount.from_dict({"id": "uuid-1", "status": "connected"})
        assert "uuid-1" in str(r)
        assert "connected" in str(r)


# ---------------------------------------------------------------------------
# AccountSummary
# ---------------------------------------------------------------------------

class TestAccountSummary:
    SAMPLE = {
        "balance": 10000.00,
        "equity": 9850.50,
        "margin": 150.00,
        "freeMargin": 9700.50,
        "marginLevel": 6567.00,
        "currency": "USD",
    }

    def test_from_dict(self):
        s = AccountSummary.from_dict(self.SAMPLE)
        assert s.balance == 10000.00
        assert s.equity == 9850.50
        assert s.margin == 150.00
        assert s.free_margin == 9700.50
        assert s.margin_level == 6567.00
        assert s.currency == "USD"

    def test_is_margin_call_risk_false_when_healthy(self):
        s = AccountSummary.from_dict(self.SAMPLE)
        assert s.is_margin_call_risk is False

    def test_is_margin_call_risk_true_when_low(self):
        data = {**self.SAMPLE, "marginLevel": 120.0}
        s = AccountSummary.from_dict(data)
        assert s.is_margin_call_risk is True

    def test_is_margin_call_risk_false_when_no_margin(self):
        data = {**self.SAMPLE, "marginLevel": 0}
        s = AccountSummary.from_dict(data)
        assert s.is_margin_call_risk is False

    def test_str_contains_balance(self):
        s = AccountSummary.from_dict(self.SAMPLE)
        assert "10000" in str(s)
        assert "USD" in str(s)

    def test_missing_fields_default_to_zero(self):
        s = AccountSummary.from_dict({})
        assert s.balance == 0.0
        assert s.currency == ""


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------

class TestQuote:
    def test_from_dict(self):
        q = Quote.from_dict({"symbol": "EURUSD", "bid": 1.08500, "ask": 1.08510})
        assert q.symbol == "EURUSD"
        assert q.bid == 1.08500
        assert q.ask == 1.08510

    def test_spread(self):
        q = Quote.from_dict({"symbol": "EURUSD", "bid": 1.08500, "ask": 1.08501})
        assert abs(q.spread - 0.00001) < 1e-9

    def test_spread_pips(self):
        q = Quote.from_dict({"symbol": "EURUSD", "bid": 1.08500, "ask": 1.08501})
        assert q.spread_pips == pytest.approx(1.0, abs=0.05)

    def test_mid(self):
        q = Quote.from_dict({"symbol": "EURUSD", "bid": 1.08500, "ask": 1.08510})
        assert q.mid == pytest.approx(1.08505, abs=1e-6)

    def test_str(self):
        q = Quote.from_dict({"symbol": "EURUSD", "bid": 1.08500, "ask": 1.08510})
        assert "EURUSD" in str(q)


# ---------------------------------------------------------------------------
# OrderResult
# ---------------------------------------------------------------------------

class TestOrderResult:
    def test_success(self):
        r = OrderResult.from_dict({"ticket": 12345678, "retcode": 0, "comment": "OK"})
        assert r.success is True
        assert r.ticket == 12345678

    def test_failure(self):
        r = OrderResult.from_dict({"ticket": 0, "retcode": 10019, "comment": "No funds"})
        assert r.success is False
        assert r.retcode == 10019

    def test_str_success(self):
        r = OrderResult.from_dict({"ticket": 1, "retcode": 0, "comment": ""})
        assert "✅" in str(r)

    def test_str_failure(self):
        r = OrderResult.from_dict({"ticket": 0, "retcode": 10019, "comment": ""})
        assert "❌" in str(r)

    def test_missing_ticket_defaults_zero(self):
        r = OrderResult.from_dict({"retcode": 0})
        assert r.ticket == 0


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

class TestPosition:
    SAMPLE = {
        "ticket": 99999,
        "symbol": "XAUUSD",
        "type": "buy",
        "volume": 0.10,
        "openPrice": 2000.50,
        "stopLoss": 1990.00,
        "takeProfit": 2020.00,
        "profit": 50.00,
        "swap": -1.50,
        "comment": "scalper",
    }

    def test_from_dict(self):
        p = Position.from_dict(self.SAMPLE)
        assert p.ticket == 99999
        assert p.symbol == "XAUUSD"
        assert p.order_type == "buy"
        assert p.volume == 0.10
        assert p.profit == 50.00

    def test_total_pnl(self):
        p = Position.from_dict(self.SAMPLE)
        assert p.total_pnl == pytest.approx(48.50, abs=0.01)

    def test_str_buy(self):
        p = Position.from_dict(self.SAMPLE)
        assert "BUY" in str(p)
        assert "XAUUSD" in str(p)


# ---------------------------------------------------------------------------
# OrderHistoryItem
# ---------------------------------------------------------------------------

class TestOrderHistoryItem:
    SAMPLE = {
        "ticket": 555,
        "symbol": "GBPUSD",
        "type": "sell",
        "volume": 0.01,
        "openPrice": 1.2700,
        "closePrice": 1.2650,
        "openTime": "2026-01-01T09:00:00Z",
        "closeTime": "2026-01-01T10:00:00Z",
        "profit": 50.00,
        "swap": -0.50,
        "commission": -0.10,
    }

    def test_from_dict(self):
        h = OrderHistoryItem.from_dict(self.SAMPLE)
        assert h.ticket == 555
        assert h.symbol == "GBPUSD"

    def test_net_profit(self):
        h = OrderHistoryItem.from_dict(self.SAMPLE)
        assert h.net_profit == pytest.approx(49.40, abs=0.01)

    def test_str(self):
        h = OrderHistoryItem.from_dict(self.SAMPLE)
        assert "GBPUSD" in str(h)


# ---------------------------------------------------------------------------
# PaginatedHistory
# ---------------------------------------------------------------------------

class TestPaginatedHistory:
    def _make(self, total, page, page_size, count):
        items = [
            OrderHistoryItem.from_dict({
                "ticket": i, "symbol": "EURUSD", "type": "buy", "volume": 0.01,
                "openPrice": 1.08, "closePrice": 1.09, "openTime": "", "closeTime": "",
                "profit": 10.0, "swap": 0.0, "commission": 0.0,
            })
            for i in range(count)
        ]
        return PaginatedHistory(data=items, total=total, page=page, page_size=page_size)

    def test_total_pages(self):
        ph = self._make(total=100, page=1, page_size=50, count=50)
        assert ph.total_pages == 2

    def test_total_pages_ceiling(self):
        ph = self._make(total=101, page=1, page_size=50, count=50)
        assert ph.total_pages == 3

    def test_has_next_true(self):
        ph = self._make(total=100, page=1, page_size=50, count=50)
        assert ph.has_next is True

    def test_has_next_false_on_last_page(self):
        ph = self._make(total=100, page=2, page_size=50, count=50)
        assert ph.has_next is False

    def test_from_dict(self):
        raw = {
            "data": [],
            "total": 500,
            "page": 3,
            "pageSize": 50,
        }
        ph = PaginatedHistory.from_dict(raw)
        assert ph.total == 500
        assert ph.page == 3
        assert ph.page_size == 50
        assert ph.total_pages == 10

    def test_str(self):
        ph = self._make(total=100, page=1, page_size=50, count=50)
        assert "1/" in str(ph)


# ---------------------------------------------------------------------------
# Tick
# ---------------------------------------------------------------------------

class TestTick:
    def test_from_dict(self):
        t = Tick.from_dict({"type": "quote", "symbol": "EURUSD", "bid": 1.085, "ask": 1.086})
        assert t.symbol == "EURUSD"
        assert t.bid == 1.085
        assert t.ask == 1.086

    def test_spread_pips(self):
        t = Tick.from_dict({"type": "quote", "symbol": "EURUSD", "bid": 1.08500, "ask": 1.08501})
        assert t.spread_pips == pytest.approx(1.0, abs=0.05)

    def test_str(self):
        t = Tick.from_dict({"type": "quote", "symbol": "EURUSD", "bid": 1.085, "ask": 1.086})
        assert "EURUSD" in str(t)
