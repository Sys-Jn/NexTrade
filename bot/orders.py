"""
Order placement logic.
Builds the correct parameter payload for each order type and delegates
the actual HTTP call to BinanceClient.
"""

from __future__ import annotations

from typing import Optional

from .client import BinanceClient
from .logging_config import get_logger
from .validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

logger = get_logger(__name__)


def build_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float | str,
    price: Optional[float | str] = None,
    stop_price: Optional[float | str] = None,
    time_in_force: str = "GTC",
) -> dict:
    """
    Validate inputs and return a ready-to-send order parameter dict.

    Raises
    ------
    ValueError
        If any parameter fails validation.
    """
    sym = validate_symbol(symbol)
    sid = validate_side(side)
    otype = validate_order_type(order_type)
    qty = validate_quantity(quantity)
    px = validate_price(price, otype)
    stop_px = validate_stop_price(stop_price, otype)

    params: dict = {
        "symbol": sym,
        "side": sid,
        "type": otype,
        "quantity": qty,
    }

    if otype == "LIMIT":
        params["price"] = px
        params["timeInForce"] = time_in_force

    elif otype == "STOP":
        params["price"] = px          # limit price
        params["stopPrice"] = stop_px  # trigger price
        params["timeInForce"] = time_in_force

    elif otype == "STOP_MARKET":
        params["stopPrice"] = stop_px

    return params


def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float | str,
    price: Optional[float | str] = None,
    stop_price: Optional[float | str] = None,
    time_in_force: str = "GTC",
) -> dict:
    """
    Validate, build, and submit an order. Returns the full API response dict.

    Raises
    ------
    ValueError
        On invalid input parameters.
    requests.HTTPError
        On API-level rejections (e.g. insufficient balance, bad symbol).
    requests.RequestException
        On network failures.
    """
    params = build_order_params(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=time_in_force,
    )

    logger.info(
        "Submitting %s %s order | symbol=%s qty=%s price=%s stopPrice=%s",
        side.upper(),
        order_type.upper(),
        params["symbol"],
        params["quantity"],
        params.get("price", "N/A"),
        params.get("stopPrice", "N/A"),
    )

    return client.place_order(**params)


def format_order_response(response: dict) -> str:
    """Return a human-readable multi-line summary of an order response."""
    lines = [
        "┌─────────────────────────────────────────┐",
        "│           ORDER RESPONSE DETAILS         │",
        "├─────────────────────────────────────────┤",
        f"│  Order ID      : {response.get('orderId', 'N/A')}",
        f"│  Symbol        : {response.get('symbol', 'N/A')}",
        f"│  Side          : {response.get('side', 'N/A')}",
        f"│  Type          : {response.get('type', 'N/A')}",
        f"│  Status        : {response.get('status', 'N/A')}",
        f"│  Quantity      : {response.get('origQty', 'N/A')}",
        f"│  Executed Qty  : {response.get('executedQty', 'N/A')}",
        f"│  Avg Price     : {response.get('avgPrice', 'N/A')}",
        f"│  Price         : {response.get('price', 'N/A')}",
        f"│  Time in Force : {response.get('timeInForce', 'N/A')}",
        f"│  Client OID    : {response.get('clientOrderId', 'N/A')}",
        "└─────────────────────────────────────────┘",
    ]
    return "\n".join(lines)
