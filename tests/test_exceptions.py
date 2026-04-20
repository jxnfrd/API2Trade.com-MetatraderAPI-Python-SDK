"""
Unit tests for SDK exceptions.

Run with:  pytest tests/test_exceptions.py -v
"""

import pytest

from api2trade_sdk.exceptions import (
    Api2TradeError,
    AuthenticationError,
    AccountNotFoundError,
    RateLimitError,
    BrokerRejectionError,
    ServerError,
)
from api2trade_sdk.enums import RetCode


class TestApi2TradeError:
    def test_basic(self):
        e = Api2TradeError("something went wrong", status_code=500)
        assert str(e) == "something went wrong"
        assert e.status_code == 500
        assert e.response_body == {}

    def test_with_body(self):
        e = Api2TradeError("err", response_body={"detail": "x"})
        assert e.response_body == {"detail": "x"}

    def test_is_exception(self):
        with pytest.raises(Api2TradeError):
            raise Api2TradeError("boom")


class TestAuthenticationError:
    def test_is_subclass(self):
        assert issubclass(AuthenticationError, Api2TradeError)

    def test_raise(self):
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("bad key", status_code=401)

    def test_status_code(self):
        e = AuthenticationError("bad", status_code=401)
        assert e.status_code == 401


class TestAccountNotFoundError:
    def test_message_contains_account_id(self):
        e = AccountNotFoundError(account_id="uuid-abc")
        assert "uuid-abc" in str(e)

    def test_status_code_default_404(self):
        e = AccountNotFoundError(account_id="x")
        assert e.status_code == 404

    def test_account_id_attr(self):
        e = AccountNotFoundError(account_id="test-uuid")
        assert e.account_id == "test-uuid"


class TestRateLimitError:
    def test_without_retry_after(self):
        e = RateLimitError()
        assert e.status_code == 429
        assert e.retry_after is None
        assert "Rate limit" in str(e)

    def test_with_retry_after(self):
        e = RateLimitError(retry_after=30)
        assert e.retry_after == 30
        assert "30" in str(e)


class TestBrokerRejectionError:
    def test_success_retcode_raises_no_error(self):
        # Do NOT raise on retcode 0 — that's handled by OrderResult.success
        e = BrokerRejectionError(retcode=10019, comment="No funds")
        assert e.retcode == 10019
        assert "10019" in str(e)

    def test_comment_included_in_message(self):
        e = BrokerRejectionError(retcode=10019, comment="No margin")
        assert "No margin" in str(e)

    def test_is_retryable_for_requote(self):
        e = BrokerRejectionError(retcode=RetCode.REQUOTE)
        assert e.is_retryable is True

    def test_is_not_retryable_for_insufficient_funds(self):
        e = BrokerRejectionError(retcode=RetCode.INSUFFICIENT_FUNDS)
        assert e.is_retryable is False

    def test_is_retryable_for_server_busy(self):
        e = BrokerRejectionError(retcode=RetCode.SERVER_BUSY)
        assert e.is_retryable is True

    def test_description_in_message(self):
        e = BrokerRejectionError(retcode=RetCode.MARKET_CLOSED)
        assert "Market closed" in str(e)

    def test_is_subclass_of_base(self):
        assert issubclass(BrokerRejectionError, Api2TradeError)


class TestServerError:
    def test_is_subclass(self):
        assert issubclass(ServerError, Api2TradeError)

    def test_raise(self):
        with pytest.raises(ServerError):
            raise ServerError("Internal error", status_code=500)


class TestRetCodeEnum:
    def test_is_retryable_requote(self):
        assert RetCode.is_retryable(10004) is True

    def test_is_retryable_insufficient_funds(self):
        assert RetCode.is_retryable(10019) is False

    def test_description_success(self):
        assert RetCode.description(0) == "Success"

    def test_description_unknown(self):
        desc = RetCode.description(99999)
        assert "99999" in desc

    def test_description_market_closed(self):
        desc = RetCode.description(10018)
        assert "Market" in desc
