#!/usr/bin/env python3
"""
cli.py — Command-line interface for the Binance Futures Testnet trading bot.

Examples
--------
# Market BUY
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit SELL
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 100000

# Stop-Market BUY (bonus order type)
python cli.py place --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 95000

# Stop-Limit SELL
python cli.py place --symbol ETHUSDT --side SELL --type STOP --quantity 0.01 --price 3000 --stop-price 3050

Environment variables (or .env file):
  BINANCE_API_KEY     — your Testnet API key
  BINANCE_API_SECRET  — your Testnet API secret
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Allow running directly: python cli.py …
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import requests

from bot.client import BinanceClient
from bot.mock_client import MockBinanceClient
from bot.logging_config import configure_logging, get_logger
from bot.orders import format_order_response, place_order

load_dotenv()

# ── Logger setup ───────────────────────────────────────────────────────────────
# verbose flag is parsed early so we can set log level before subcommands run
_pre_parser = argparse.ArgumentParser(add_help=False)
_pre_parser.add_argument("-v", "--verbose", action="store_true")
_pre_args, _ = _pre_parser.parse_known_args()
configure_logging(logging.DEBUG if _pre_args.verbose else logging.INFO)
logger = get_logger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_credentials() -> tuple[str, str]:
    """Read API credentials from environment variables."""
    api_key = os.environ.get("BINANCE_API_KEY", "").strip()
    api_secret = os.environ.get("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        logger.error(
            "BINANCE_API_KEY and BINANCE_API_SECRET must be set "
            "(env vars or .env file)."
        )
        sys.exit(1)
    return api_key, api_secret


def get_client(mock: bool):
    """Return a real or mock Binance client depending on the --mock flag."""
    if mock:
        print("\n  ⚡  MOCK MODE — no real API calls, no keys needed\n")
        return MockBinanceClient()
    api_key, api_secret = get_credentials()
    return BinanceClient(api_key=api_key, api_secret=api_secret)


def print_request_summary(args: argparse.Namespace) -> None:
    """Pretty-print what we are about to submit."""
    lines = [
        "",
        "┌─────────────────────────────────────────┐",
        "│            ORDER REQUEST SUMMARY         │",
        "├─────────────────────────────────────────┤",
        f"│  Symbol        : {args.symbol.upper()}",
        f"│  Side          : {args.side.upper()}",
        f"│  Order Type    : {args.type.upper()}",
        f"│  Quantity      : {args.quantity}",
        f"│  Price         : {args.price if args.price else 'N/A (MARKET)'}",
        f"│  Stop Price    : {args.stop_price if args.stop_price else 'N/A'}",
        f"│  Time-in-Force : {args.tif}",
        "└─────────────────────────────────────────┘",
    ]
    print("\n".join(lines))


# ── Sub-commands ───────────────────────────────────────────────────────────────

def cmd_place(args: argparse.Namespace) -> int:
    """Handle the `place` sub-command. Returns exit code."""
    print_request_summary(args)
    logger.info(
        "CLI request — place %s %s | symbol=%s qty=%s price=%s stop=%s",
        args.side.upper(), args.type.upper(), args.symbol.upper(),
        args.quantity, args.price, args.stop_price,
    )

    client = get_client(args.mock)

    try:
        response = place_order(
            client=client,
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.tif,
        )
    except ValueError as exc:
        logger.error("Validation error: %s", exc)
        print(f"\n✗  Validation error: {exc}")
        return 2
    except requests.HTTPError as exc:
        logger.error("API error: %s", exc)
        print(f"\n✗  API error: {exc}")
        return 3
    except requests.RequestException as exc:
        logger.error("Network error: %s", exc)
        print(f"\n✗  Network error: {exc}")
        return 4

    print(format_order_response(response))
    print("\n✓  Order placed successfully!\n")
    logger.info("Order placed successfully. orderId=%s", response.get("orderId"))
    return 0


def cmd_ping(args: argparse.Namespace) -> int:
    """Handle the `ping` sub-command."""
    client = get_client(args.mock)
    try:
        client.ping()
        print("✓  Testnet server is reachable.")
        logger.info("Ping successful.")
        return 0
    except requests.RequestException as exc:
        print(f"✗  Ping failed: {exc}")
        logger.error("Ping failed: %s", exc)
        return 4


def cmd_account(args: argparse.Namespace) -> int:
    """Handle the `account` sub-command — show USDT balance."""
    client = get_client(args.mock)
    try:
        info = client.get_account()
    except (requests.HTTPError, requests.RequestException) as exc:
        print(f"✗  Failed to fetch account: {exc}")
        logger.error("Account fetch failed: %s", exc)
        return 3

    assets = [a for a in info.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    if not assets:
        print("No assets with non-zero balance found.")
        return 0

    print("\n┌──────────────────────────────────────────────┐")
    print("│              ACCOUNT BALANCES                 │")
    print("├──────────────────────────────────────────────┤")
    for a in assets:
        print(f"│  {a['asset']:<8}  wallet={float(a['walletBalance']):.4f}  "
              f"available={float(a['availableBalance']):.4f}")
    print("└──────────────────────────────────────────────┘\n")
    return 0


# ── Argument parser ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet trading bot CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable DEBUG-level console logging",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── place ──────────────────────────────────────────────────────────────────
    place_p = sub.add_parser("place", help="Place a new futures order")
    place_p.add_argument(
        "--symbol", required=True,
        metavar="BTCUSDT",
        help="Trading pair symbol (e.g. BTCUSDT)",
    )
    place_p.add_argument(
        "--side", required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        metavar="BUY|SELL",
        help="Order side",
    )
    place_p.add_argument(
        "--type", required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET", "STOP",
                 "market", "limit", "stop_market", "stop"],
        metavar="MARKET|LIMIT|STOP_MARKET|STOP",
        help="Order type",
    )
    place_p.add_argument(
        "--quantity", required=True,
        type=float,
        metavar="QTY",
        help="Order quantity (e.g. 0.001 for BTC)",
    )
    place_p.add_argument(
        "--price",
        type=float,
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT and STOP order types)",
    )
    place_p.add_argument(
        "--stop-price",
        dest="stop_price",
        type=float,
        default=None,
        metavar="STOP_PRICE",
        help="Stop/trigger price (required for STOP and STOP_MARKET)",
    )
    place_p.add_argument(
        "--tif",
        default="GTC",
        choices=["GTC", "IOC", "FOK", "GTX"],
        metavar="GTC|IOC|FOK|GTX",
        help="Time-in-force for LIMIT orders (default: GTC)",
    )
    place_p.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock/simulation mode — no API keys or internet needed",
    )
    place_p.set_defaults(func=cmd_place)

    # ── ping ───────────────────────────────────────────────────────────────────
    ping_p = sub.add_parser("ping", help="Check connectivity to the Testnet server")
    ping_p.add_argument("--mock", action="store_true", help="Simulate ping locally")
    ping_p.set_defaults(func=cmd_ping)

    # ── account ────────────────────────────────────────────────────────────────
    acc_p = sub.add_parser("account", help="Show account balances")
    acc_p.add_argument("--mock", action="store_true", help="Show mock account balance")
    acc_p.set_defaults(func=cmd_account)

    return parser


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
