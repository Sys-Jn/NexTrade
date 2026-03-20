#!/usr/bin/env python3
"""
gui.py — Tkinter desktop GUI for the Binance Futures Trading Bot.
Run with: python gui.py
"""

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import font, messagebox, scrolledtext, ttk

sys.path.insert(0, str(Path(__file__).parent))

from bot.mock_client import MockBinanceClient
from bot.client import BinanceClient
from bot.orders import format_order_response, place_order
from bot.logging_config import configure_logging

configure_logging()

# ── Colour palette ─────────────────────────────────────────────────────────────
BG        = "#1e1e2e"
PANEL     = "#2a2a3e"
ACCENT    = "#7c6af7"
GREEN     = "#50fa7b"
RED       = "#ff5555"
YELLOW    = "#f1fa8c"
FG        = "#cdd6f4"
FG_DIM    = "#888aaa"
BORDER    = "#44475a"
BTN_BUY   = "#238636"
BTN_SELL  = "#b91c1c"
BTN_HOV   = "#2ea043"


class TradingBotGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Binance Futures Trading Bot")
        self.root.geometry("680x720")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self._build_header()
        self._build_mode_toggle()
        self._build_form()
        self._build_buttons()
        self._build_output()
        self._build_footer()

        self._on_type_change()   # set initial state

    # ── Header ─────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=ACCENT, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(
            hdr,
            text="📈  Binance Futures Trading Bot",
            bg=ACCENT, fg="white",
            font=("Segoe UI", 15, "bold"),
        ).pack(side="left", padx=18, pady=12)

        self.mode_badge = tk.Label(
            hdr, text="● MOCK MODE", bg=ACCENT, fg=YELLOW,
            font=("Segoe UI", 9, "bold"),
        )
        self.mode_badge.pack(side="right", padx=18)

    # ── Mode toggle ────────────────────────────────────────────────────────────

    def _build_mode_toggle(self):
        frame = tk.Frame(self.root, bg=PANEL, pady=10)
        frame.pack(fill="x", padx=16, pady=(12, 0))

        tk.Label(frame, text="Mode:", bg=PANEL, fg=FG_DIM,
                 font=("Segoe UI", 9)).pack(side="left", padx=(12, 6))

        self.mock_var = tk.BooleanVar(value=True)

        mock_rb = tk.Radiobutton(
            frame, text="Mock (no keys needed)", variable=self.mock_var,
            value=True, bg=PANEL, fg=YELLOW, selectcolor=PANEL,
            activebackground=PANEL, activeforeground=YELLOW,
            font=("Segoe UI", 9, "bold"), command=self._on_mode_change,
        )
        mock_rb.pack(side="left", padx=4)

        live_rb = tk.Radiobutton(
            frame, text="Live Testnet (API keys required)", variable=self.mock_var,
            value=False, bg=PANEL, fg=FG, selectcolor=PANEL,
            activebackground=PANEL, activeforeground=FG,
            font=("Segoe UI", 9), command=self._on_mode_change,
        )
        live_rb.pack(side="left", padx=4)

        # API key fields (shown only in live mode)
        self.key_frame = tk.Frame(self.root, bg=PANEL, pady=6)

        self._lbl(self.key_frame, "API Key:").grid(row=0, column=0, sticky="e", padx=(12,6), pady=3)
        self.api_key_var = tk.StringVar()
        tk.Entry(self.key_frame, textvariable=self.api_key_var, width=48,
                 show="*", bg=BG, fg=FG, insertbackground=FG,
                 relief="flat", font=("Segoe UI", 9)).grid(row=0, column=1, sticky="w")

        self._lbl(self.key_frame, "API Secret:").grid(row=1, column=0, sticky="e", padx=(12,6), pady=3)
        self.api_secret_var = tk.StringVar()
        tk.Entry(self.key_frame, textvariable=self.api_secret_var, width=48,
                 show="*", bg=BG, fg=FG, insertbackground=FG,
                 relief="flat", font=("Segoe UI", 9)).grid(row=1, column=1, sticky="w")

    def _on_mode_change(self):
        if self.mock_var.get():
            self.key_frame.pack_forget()
            self.mode_badge.config(text="● MOCK MODE", fg=YELLOW)
        else:
            self.key_frame.pack(fill="x", padx=16, pady=(4, 0))
            self.mode_badge.config(text="● LIVE TESTNET", fg=GREEN)

    # ── Order form ─────────────────────────────────────────────────────────────

    def _build_form(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="x", padx=16, pady=12)

        form = tk.Frame(outer, bg=PANEL, padx=20, pady=16)
        form.pack(fill="x")

        tk.Label(form, text="Order Details", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

        # Row 1: Symbol + Side
        self._lbl(form, "Symbol:").grid(row=1, column=0, sticky="e", padx=(0,8), pady=6)
        self.symbol_var = tk.StringVar(value="BTCUSDT")
        sym_cb = ttk.Combobox(form, textvariable=self.symbol_var, width=14,
                               values=["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT"],
                               font=("Segoe UI", 10))
        sym_cb.grid(row=1, column=1, sticky="w", padx=(0,20))

        self._lbl(form, "Side:").grid(row=1, column=2, sticky="e", padx=(0,8))
        self.side_var = tk.StringVar(value="BUY")
        side_frame = tk.Frame(form, bg=PANEL)
        side_frame.grid(row=1, column=3, sticky="w")
        for val, col in [("BUY", GREEN), ("SELL", RED)]:
            tk.Radiobutton(
                side_frame, text=val, variable=self.side_var, value=val,
                bg=PANEL, fg=col, selectcolor=PANEL,
                activebackground=PANEL, font=("Segoe UI", 10, "bold"),
            ).pack(side="left", padx=4)

        # Row 2: Order Type + TIF
        self._lbl(form, "Order Type:").grid(row=2, column=0, sticky="e", padx=(0,8), pady=6)
        self.type_var = tk.StringVar(value="MARKET")
        type_cb = ttk.Combobox(form, textvariable=self.type_var, width=14,
                                values=["MARKET","LIMIT","STOP_MARKET","STOP"],
                                font=("Segoe UI", 10), state="readonly")
        type_cb.grid(row=2, column=1, sticky="w", padx=(0,20))
        type_cb.bind("<<ComboboxSelected>>", lambda e: self._on_type_change())

        self._lbl(form, "Time in Force:").grid(row=2, column=2, sticky="e", padx=(0,8))
        self.tif_var = tk.StringVar(value="GTC")
        self.tif_cb = ttk.Combobox(form, textvariable=self.tif_var, width=8,
                                    values=["GTC","IOC","FOK","GTX"],
                                    font=("Segoe UI", 10), state="readonly")
        self.tif_cb.grid(row=2, column=3, sticky="w")

        # Row 3: Quantity + Price
        self._lbl(form, "Quantity:").grid(row=3, column=0, sticky="e", padx=(0,8), pady=6)
        self.qty_var = tk.StringVar(value="0.001")
        tk.Entry(form, textvariable=self.qty_var, width=16,
                 bg=BG, fg=FG, insertbackground=FG,
                 relief="flat", font=("Segoe UI", 10)).grid(row=3, column=1, sticky="w", padx=(0,20))

        self.price_lbl = self._lbl(form, "Price (USDT):")
        self.price_lbl.grid(row=3, column=2, sticky="e", padx=(0,8))
        self.price_var = tk.StringVar(value="")
        self.price_entry = tk.Entry(form, textvariable=self.price_var, width=16,
                                    bg=BG, fg=FG, insertbackground=FG,
                                    relief="flat", font=("Segoe UI", 10))
        self.price_entry.grid(row=3, column=3, sticky="w")

        # Row 4: Stop Price
        self.stop_lbl = self._lbl(form, "Stop Price:")
        self.stop_lbl.grid(row=4, column=0, sticky="e", padx=(0,8), pady=6)
        self.stop_var = tk.StringVar(value="")
        self.stop_entry = tk.Entry(form, textvariable=self.stop_var, width=16,
                                   bg=BG, fg=FG, insertbackground=FG,
                                   relief="flat", font=("Segoe UI", 10))
        self.stop_entry.grid(row=4, column=1, sticky="w")

        self.form = form  # keep reference

    def _lbl(self, parent, text):
        return tk.Label(parent, text=text, bg=PANEL if parent != self.root else BG,
                        fg=FG_DIM, font=("Segoe UI", 9))

    def _on_type_change(self):
        otype = self.type_var.get().upper()
        needs_price = otype in ("LIMIT", "STOP")
        needs_stop  = otype in ("STOP", "STOP_MARKET")

        state_price = "normal" if needs_price else "disabled"
        state_stop  = "normal" if needs_stop  else "disabled"

        self.price_entry.config(state=state_price,
                                bg=BG if needs_price else BORDER,
                                fg=FG if needs_price else FG_DIM)
        self.stop_entry.config(state=state_stop,
                               bg=BG if needs_stop else BORDER,
                               fg=FG if needs_stop else FG_DIM)
        self.tif_cb.config(state="readonly" if needs_price else "disabled")

    # ── Buttons ────────────────────────────────────────────────────────────────

    def _build_buttons(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="x", padx=16, pady=(0, 8))

        self.place_btn = tk.Button(
            frame, text="▶  Place Order",
            bg=BTN_BUY, fg="white", activebackground=BTN_HOV,
            font=("Segoe UI", 11, "bold"),
            relief="flat", cursor="hand2", padx=20, pady=8,
            command=self._on_place,
        )
        self.place_btn.pack(side="left", padx=(0, 10))

        tk.Button(
            frame, text="⚡  Ping Server",
            bg=PANEL, fg=FG, activebackground=BORDER,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            padx=14, pady=8, command=self._on_ping,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            frame, text="💰  Account Balance",
            bg=PANEL, fg=FG, activebackground=BORDER,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            padx=14, pady=8, command=self._on_account,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            frame, text="🗑  Clear",
            bg=PANEL, fg=FG_DIM, activebackground=BORDER,
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            padx=14, pady=8, command=self._clear_output,
        ).pack(side="right")

    # ── Output area ────────────────────────────────────────────────────────────

    def _build_output(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        tk.Label(frame, text="Output", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9)).pack(anchor="w")

        self.output = scrolledtext.ScrolledText(
            frame, bg=PANEL, fg=FG, insertbackground=FG,
            font=("Consolas", 9), relief="flat",
            wrap="word", state="disabled",
        )
        self.output.pack(fill="both", expand=True)

        # Colour tags
        self.output.tag_config("success", foreground=GREEN)
        self.output.tag_config("error",   foreground=RED)
        self.output.tag_config("info",    foreground=ACCENT)
        self.output.tag_config("warn",    foreground=YELLOW)

    def _build_footer(self):
        tk.Label(
            self.root,
            text="Binance Futures Testnet Bot  •  Mock mode: no real funds",
            bg=BG, fg=FG_DIM, font=("Segoe UI", 8),
        ).pack(pady=(0, 6))

    # ── Output helpers ─────────────────────────────────────────────────────────

    def _write(self, text: str, tag: str = ""):
        self.output.config(state="normal")
        if tag:
            self.output.insert("end", text + "\n", tag)
        else:
            self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.config(state="disabled")

    def _clear_output(self):
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.config(state="disabled")

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.place_btn.config(
            state=state,
            text="⏳  Placing..." if busy else "▶  Place Order"
        )

    # ── Client factory ─────────────────────────────────────────────────────────

    def _get_client(self):
        if self.mock_var.get():
            return MockBinanceClient()
        key    = self.api_key_var.get().strip()
        secret = self.api_secret_var.get().strip()
        if not key or not secret:
            raise ValueError("API Key and Secret are required for Live Testnet mode.")
        return BinanceClient(api_key=key, api_secret=secret)

    # ── Button handlers ────────────────────────────────────────────────────────

    def _on_place(self):
        self._set_busy(True)
        threading.Thread(target=self._place_worker, daemon=True).start()

    def _place_worker(self):
        try:
            client = self._get_client()
            symbol   = self.symbol_var.get().strip()
            side     = self.side_var.get()
            otype    = self.type_var.get()
            qty      = self.qty_var.get().strip()
            price    = self.price_var.get().strip() or None
            stop_px  = self.stop_var.get().strip() or None
            tif      = self.tif_var.get()

            mode_tag = "warn" if self.mock_var.get() else "info"
            mode_txt = "[MOCK]" if self.mock_var.get() else "[LIVE]"

            self._write(f"\n{mode_txt} Placing {side} {otype} order on {symbol}...", mode_tag)

            response = place_order(
                client=client,
                symbol=symbol,
                side=side,
                order_type=otype,
                quantity=qty,
                price=price,
                stop_price=stop_px,
                time_in_force=tif,
            )

            self._write(format_order_response(response))
            self._write("✓  Order placed successfully!", "success")

        except ValueError as e:
            self._write(f"✗  Validation error: {e}", "error")
        except Exception as e:
            self._write(f"✗  Error: {e}", "error")
        finally:
            self.root.after(0, lambda: self._set_busy(False))

    def _on_ping(self):
        def worker():
            try:
                client = self._get_client()
                client.ping()
                self._write("✓  Server is reachable!", "success")
            except Exception as e:
                self._write(f"✗  Ping failed: {e}", "error")
        threading.Thread(target=worker, daemon=True).start()

    def _on_account(self):
        def worker():
            try:
                client = self._get_client()
                info = client.get_account()
                assets = [a for a in info.get("assets", [])
                          if float(a.get("walletBalance", 0)) > 0]
                if not assets:
                    self._write("No assets with non-zero balance.", "warn")
                    return
                self._write("\n── Account Balances ──────────────────", "info")
                for a in assets:
                    self._write(
                        f"  {a['asset']:<8}  "
                        f"Wallet: {float(a['walletBalance']):.4f}   "
                        f"Available: {float(a['availableBalance']):.4f}"
                    )
                self._write("──────────────────────────────────────", "info")
            except Exception as e:
                self._write(f"✗  Error: {e}", "error")
        threading.Thread(target=worker, daemon=True).start()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    try:
        root.iconbitmap("")
    except Exception:
        pass

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TCombobox",
                    fieldbackground=BG, background=PANEL,
                    foreground=FG, selectbackground=ACCENT,
                    bordercolor=BORDER, arrowcolor=FG)

    app = TradingBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
