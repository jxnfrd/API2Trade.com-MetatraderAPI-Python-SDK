"""
HTTP transport layer for the API2Trade SDK.

Handles:
- Session setup and keep-alive
- API key authentication (Single plan) and HTTP Basic Auth (Pro plans)
- Automatic retry with exponential backoff for transient errors
- Unified HTTP → SDK exception mapping
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    Api2TradeError,
    AuthenticationError,
    AccountNotFoundError,
    RateLimitError,
    ServerError,
    ConnectionError as Api2TradeConnectionError,
)

logger = logging.getLogger("api2trade_sdk.http")

# Default timeouts: (connect_timeout, read_timeout) in seconds
DEFAULT_TIMEOUT = (10, 30)

# Number of times to retry on network errors / 500s (not on 4xx)
DEFAULT_MAX_RETRIES = 3


def _build_session(
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = 0.5,
) -> requests.Session:
    """
    Build a ``requests.Session`` with connection pooling and automatic
    low-level retry for network-level failures (not for HTTP error codes —
    those are handled at the SDK level).
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        # Only retry on these status codes (server-side errors and rate limits)
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "DELETE", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class HttpClient:
    """
    Low-level authenticated HTTP client used by all resource modules.

    Args:
        api_key:      API key for the Single Account plan header ``x-api-key``.
        base_url:     Base URL override (default: ``https://api.metatraderapi.dev``).
        pro_username: Pro plan Basic Auth username.
        pro_password: Pro plan Basic Auth password.
        timeout:      ``(connect, read)`` timeout tuple in seconds.
        max_retries:  Number of retries for network-level failures.
        backoff_factor: Exponential backoff factor between retries.
        user_agent:   Custom ``User-Agent`` header value.
    """

    DEFAULT_BASE_URL = "https://api.metatraderapi.dev"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        pro_username: Optional[str] = None,
        pro_password: Optional[str] = None,
        timeout: tuple = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = 0.5,
        user_agent: str = "api2trade-python-sdk/1.0.0",
    ) -> None:
        if not api_key and not (pro_username and pro_password):
            raise ValueError(
                "Provide either api_key (Single plan) or "
                "pro_username + pro_password (Pro plans)."
            )

        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._session = _build_session(max_retries=max_retries, backoff_factor=backoff_factor)

        # Set authentication
        if pro_username and pro_password:
            self._session.auth = (pro_username, pro_password)
            logger.debug("Configured Pro plan Basic Auth.")
        else:
            self._session.headers.update({"x-api-key": api_key})
            logger.debug("Configured Single plan API key auth.")

        self._session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Public request methods
    # ------------------------------------------------------------------

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Perform a GET request and return the parsed JSON response."""
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Perform a POST request with an optional JSON body."""
        return self._request("POST", path, params=params, json=json)

    def delete(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Perform a DELETE request with an optional JSON body."""
        return self._request("DELETE", path, json=json)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.debug("%s %s  params=%s  body=%s", method, url, params, json)

        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise Api2TradeConnectionError(
                f"Request timed out: {method} {url}"
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise Api2TradeConnectionError(
                f"Network error connecting to API2Trade: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise Api2TradeConnectionError(f"Unexpected request error: {exc}") from exc

        self._raise_for_status(response)

        # Parse JSON — guard against empty bodies (e.g. 204 No Content)
        if response.content:
            try:
                return response.json()
            except ValueError:
                return response.text
        return {}

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        """Map HTTP error status codes to SDK exceptions."""
        code = response.status_code

        if code == 200:
            return  # Success — caller handles retcode if needed

        # Attempt to extract error body
        body: dict = {}
        try:
            body = response.json()
        except ValueError:
            pass

        if code == 401:
            raise AuthenticationError(
                "Invalid or missing API key. Check your credentials at "
                "https://app.metatraderapi.dev → Settings.",
                status_code=code,
                response_body=body,
            )

        if code == 404:
            # Extract account_id from URL or body for a helpful message
            account_id = body.get("id", body.get("accountId", "unknown"))
            raise AccountNotFoundError(
                account_id=account_id,
                status_code=code,
                response_body=body,
            )

        if code == 429:
            retry_after = None
            ra_header = response.headers.get("Retry-After")
            if ra_header and ra_header.isdigit():
                retry_after = int(ra_header)
            raise RateLimitError(retry_after=retry_after, status_code=code, response_body=body)

        if code == 400:
            msg = body.get("message", body.get("error", "Bad request"))
            raise Api2TradeError(
                f"Bad request (HTTP 400): {msg}",
                status_code=code,
                response_body=body,
            )

        if 500 <= code < 600:
            raise ServerError(
                f"API2Trade server error (HTTP {code}). "
                f"Check https://status.metatraderapi.dev/ — if this persists "
                f"contact support@api2trade.com.",
                status_code=code,
                response_body=body,
            )

        # Catch-all for unknown codes
        raise Api2TradeError(
            f"Unexpected HTTP {code} from API2Trade.",
            status_code=code,
            response_body=body,
        )
