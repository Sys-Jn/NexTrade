"""
Input validation for order parameters.
All validators raise ValueError with a human-readable message on failure.
"""

from __future__ import annotations

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "STOP"}
VALID_TIME_IN_FORCE = {"GTC", "IOC", "FOK", "GTX"}


def validate_symbol(symbol: str) -> str:
    """Return upper-cased symbol or raise ValueError."""
    if not symbol or not symbol.strip():
        raise ValueError("Symbol must not be empty.")
    cleaned = symbol.strip().upper()
    if not cleaned.isalnum():
        raise ValueError(f"Symbol '{cleaned}' contains invalid characters. Example: BTCUSDT")
    return cleaned


def validate_side(side: str) -> str:
    """Return upper-cased side (BUY/SELL) or raise ValueError."""
    cleaned = side.strip().upper()
    if cleaned not in VALID_SIDES:
        raise ValueError(
            f"Side '{side}' is invalid. Must be one of: {', '.join(sorted(VALID_SIDES))}"
        )
    return cleaned


def validate_order_type(order_type: str) -> str:
    """Return upper-cased order type or raise ValueError."""
    cleaned = order_type.strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type '{order_type}' is invalid. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}"
        )
    return cleaned


def validate_quantity(quantity: str | float) -> float:
    """Return positive float quantity or raise ValueError."""
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than 0, got {qty}.")
    return qty


def validate_price(price: str | float | None, order_type: str) -> float | None:
    """
    Return float price (required for LIMIT/STOP orders) or None for MARKET.
    Raises ValueError when price is missing for limit-style orders.
    """
    limit_types = {"LIMIT", "STOP"}
    if order_type.upper() in limit_types:
        if price is None:
            raise ValueError(f"Price is required for {order_type} orders.")
        try:
            p = float(price)
        except (TypeError, ValueError):
            raise ValueError(f"Price '{price}' is not a valid number.")
        if p <= 0:
            raise ValueError(f"Price must be greater than 0, got {p}.")
        return p
    # MARKET / STOP_MARKET — price ignored
    if price is not None:
        try:
            p = float(price)
            if p <= 0:
                raise ValueError(f"Price must be greater than 0 if provided, got {p}.")
        except (TypeError, ValueError):
            raise ValueError(f"Price '{price}' is not a valid number.")
    return None


def validate_stop_price(stop_price: str | float | None, order_type: str) -> float | None:
    """Return float stop price (required for STOP / STOP_MARKET) or None."""
    stop_types = {"STOP", "STOP_MARKET"}
    if order_type.upper() in stop_types:
        if stop_price is None:
            raise ValueError(f"--stop-price is required for {order_type} orders.")
        try:
            p = float(stop_price)
        except (TypeError, ValueError):
            raise ValueError(f"Stop price '{stop_price}' is not a valid number.")
        if p <= 0:
            raise ValueError(f"Stop price must be greater than 0, got {p}.")
        return p
    return None
