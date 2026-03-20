"""
Binance Futures Testnet client wrapper.
Handles authentication, request signing, and raw HTTP communication.
"""

import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger(__name__)

BASE_URL = "https://testnet.binancefuture.com"


class BinanceClient:
    """Thin wrapper around the Binance Futures Testnet REST API."""

    def __init__(self, api_key: str, api_secret: str, base_url: str = BASE_URL):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict) -> dict:
        """Append HMAC-SHA256 signature to a parameter dict (in-place + return)."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(self, method: str, path: str, signed: bool = False, **kwargs) -> dict:
        """
        Execute an HTTP request, optionally signing the query parameters.

        Raises
        ------
        requests.HTTPError
            If the server returns a non-2xx status code.
        requests.RequestException
            On network-level failures (timeout, connection error, etc.).
        """
        url = f"{self.base_url}{path}"

        # Merge caller-supplied params
        params = kwargs.pop("params", {}) or {}

        if signed:
            params = self._sign(params)

        logger.debug("→ %s %s  params=%s", method.upper(), url, params)

        try:
            response = self.session.request(
                method,
                url,
                params=params,
                timeout=10,
                **kwargs,
            )
        except requests.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise
        except requests.Timeout as exc:
            logger.error("Request timed out: %s", exc)
            raise

        logger.debug("← %s %s", response.status_code, response.text[:500])

        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise

        if not response.ok:
            code = data.get("code", response.status_code)
            msg = data.get("msg", response.text)
            logger.error("API error %s: %s", code, msg)
            # Attach structured info so callers can inspect it
            err = requests.HTTPError(f"[{code}] {msg}", response=response)
            err.api_code = code  # type: ignore[attr-defined]
            err.api_msg = msg  # type: ignore[attr-defined]
            raise err

        return data

    # ------------------------------------------------------------------
    # Public endpoints
    # ------------------------------------------------------------------

    def ping(self) -> dict:
        """Check server connectivity."""
        return self._request("GET", "/fapi/v1/ping")

    def get_exchange_info(self) -> dict:
        """Fetch exchange trading rules and symbol information."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account(self) -> dict:
        """Fetch account information (balances, positions)."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    # ------------------------------------------------------------------
    # Order endpoints
    # ------------------------------------------------------------------

    def place_order(self, **order_params) -> dict:
        """
        POST /fapi/v1/order — place a new order.

        Parameters are passed directly as keyword arguments and must match
        the Binance Futures API spec (symbol, side, type, quantity, …).
        """
        logger.info("Placing order: %s", order_params)
        result = self._request(
            "POST",
            "/fapi/v1/order",
            signed=True,
            params=order_params,
        )
        logger.info("Order placed successfully: orderId=%s status=%s",
                    result.get("orderId"), result.get("status"))
        return result

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order by ID."""
        params = {"symbol": symbol.upper(), "orderId": order_id}
        logger.info("Cancelling orderId=%s for %s", order_id, symbol)
        result = self._request("DELETE", "/fapi/v1/order", signed=True, params=params)
        logger.info("Order cancelled: %s", result.get("status"))
        return result

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Query a single order by ID."""
        params = {"symbol": symbol.upper(), "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", signed=True, params=params)
