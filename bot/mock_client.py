"""
mock_client.py — Simulates Binance API responses locally.
No internet connection or API keys required.
"""

import random
import time

from .logging_config import get_logger

logger = get_logger(__name__)

# Fake market prices for common symbols
MOCK_PRICES = {
    "BTCUSDT":  83500.0,
    "ETHUSDT":   3200.0,
    "BNBUSDT":    600.0,
    "SOLUSDT":    180.0,
    "XRPUSDT":      0.6,
}


def _mock_price(symbol: str) -> float:
    """Return a fake price with a small random spread."""
    base = MOCK_PRICES.get(symbol.upper(), 100.0)
    # ±0.05% random fluctuation
    return round(base * (1 + random.uniform(-0.0005, 0.0005)), 2)


def _mock_order_id() -> int:
    return random.randint(4_000_000_000, 4_999_999_999)


def _mock_client_order_id() -> str:
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    suffix = "".join(random.choices(chars, k=16))
    return f"x-MOCK{suffix}"


class MockBinanceClient:
    """
    Drop-in replacement for BinanceClient that returns realistic fake responses.
    All methods log exactly like the real client so log files look identical.
    """

    def __init__(self):
        logger.info("*** MOCK MODE — no real API calls will be made ***")

    def ping(self) -> dict:
        logger.debug("→ MOCK GET /fapi/v1/ping")
        logger.debug("← 200 {}")
        return {}

    def get_account(self) -> dict:
        logger.debug("→ MOCK GET /fapi/v2/account")
        data = {
            "assets": [
                {
                    "asset": "USDT",
                    "walletBalance": "10000.00000000",
                    "availableBalance": "9850.00000000",
                }
            ]
        }
        logger.debug("← 200 %s", data)
        return data

    def place_order(self, **params) -> dict:
        symbol = params.get("symbol", "BTCUSDT")
        side = params.get("side", "BUY")
        order_type = params.get("type", "MARKET")
        quantity = params.get("quantity", 0)
        price = params.get("price", None)
        stop_price = params.get("stopPrice", None)
        tif = params.get("timeInForce", "GTC")

        order_id = _mock_order_id()
        client_order_id = _mock_client_order_id()
        update_time = int(time.time() * 1000)

        # Determine fill behaviour
        if order_type == "MARKET":
            status = "FILLED"
            avg_price = str(_mock_price(symbol))
            executed_qty = str(quantity)
            cum_quote = str(round(float(avg_price) * float(quantity), 5))
            resp_price = "0"
        else:
            # LIMIT / STOP / STOP_MARKET sit as NEW (not yet triggered)
            status = "NEW"
            avg_price = "0.00000"
            executed_qty = "0"
            cum_quote = "0"
            resp_price = str(price) if price else "0"

        response = {
            "orderId": order_id,
            "symbol": symbol,
            "status": status,
            "clientOrderId": client_order_id,
            "price": resp_price,
            "avgPrice": avg_price,
            "origQty": str(quantity),
            "executedQty": executed_qty,
            "cumQty": executed_qty,
            "cumQuote": cum_quote,
            "timeInForce": tif,
            "type": order_type,
            "reduceOnly": False,
            "closePosition": False,
            "side": side,
            "positionSide": "BOTH",
            "stopPrice": str(stop_price) if stop_price else "0",
            "workingType": "CONTRACT_PRICE",
            "priceProtect": False,
            "origType": order_type,
            "updateTime": update_time,
        }

        logger.info("MOCK order placed: orderId=%s status=%s", order_id, status)
        logger.debug("← 200 %s", response)
        return response
