"""
Institutional Live Indian Market Terminal — Professional CLI Interface.
Built with Python Rich for non-flickering 30-second live refreshes,
multi-timeframe signals, order flow analytics, and trading decisions.
"""

import os
import sys
import time
import signal
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any

# Ensure live-market-terminal is on sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live

from config import (
    DEFAULT_REFRESH_INTERVAL_SECONDS,
    MONITORED_INSTRUMENTS,
    TOP_NIFTY_CONSTITUENTS,
    get_ist_now,
)
from data import DhanClient, HistoricalDataManager, get_global_cache
from analytics import (
    TechnicalIndicators,
    OrderFlowAnalyzer,
    MarketStructureAnalyzer,
    MarketBreadthAnalyzer,
    MultiTimeframeEngine,
)
from prediction import ForecastOrchestrator
from signals import TradingDecisionEngine, RiskManager

console = Console()

class LiveTerminalApp:
    """
    Terminal UI Application orchestrating real-time data polling,
    quantitative analytics, and Rich layout rendering.
    """

    def __init__(self, refresh_interval: int = DEFAULT_REFRESH_INTERVAL_SECONDS, primary_symbol: str = "NIFTY"):
        self.refresh_interval = refresh_interval
        self.primary_symbol = primary_symbol.upper()
        self.client = DhanClient()
        self.cache = get_global_cache()
        self.is_running = True
        self.last_refresh_time = 0.0
        self.next_refresh_countdown = self.refresh_interval

        # Setup graceful signal handler
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_exit(self, signum, frame):
        """Graceful shutdown handler for CTRL+C."""
        self.is_running = False
        console.print("\n[bold yellow]Shutting down Live Market Terminal... Clean exit guaranteed.[/bold yellow]")
        sys.exit(0)

    def refresh_market_data(self):
        """
        Polls quotes, refreshes candles, computes quantitative models,
        and synchronizes the central cache.
        """
        now = time.time()
        market_status = self.client.get_market_status()
        self.cache.update_market_status(market_status)

        # 1. Fetch quotes for all monitored instruments
        quotes = {}
        for sym in MONITORED_INSTRUMENTS:
            q = self.client.get_quote(sym)
            quotes[sym] = q
            self.cache.update_quote(sym, q)

        # 2. Fetch candles and build timeframes for primary symbol
        candles_1m = self.client.get_historical_candles(self.primary_symbol, interval="1m", days=3)
        tf_suite = HistoricalDataManager.build_timeframe_suite(candles_1m)
        self.cache.set_candles(self.primary_symbol, tf_suite)

        # 3. Compute Technicals on 5m
        candles_5m = tf_suite.get("5m", candles_1m)
        df_enriched, indicators_sc = TechnicalIndicators.calculate_all(candles_5m)

        # 4. Order Flow & CVD
        order_flow_data = OrderFlowAnalyzer.analyze_order_flow(candles_5m)

        # 5. Market Structure
        market_structure_data = MarketStructureAnalyzer.analyze_structure(candles_5m)

        # 6. Market Breadth & Institutional Flow
        breadth_data = MarketBreadthAnalyzer.compute_breadth_from_constituents(TOP_NIFTY_CONSTITUENTS)
        inst_flow = MarketBreadthAnalyzer.get_institutional_flow()

        # 7. Multi-Timeframe Alignment
        mtf_data = MultiTimeframeEngine.evaluate_multi_timeframe_suite(tf_suite)

        # 8. Predictive Movement Forecasts
        spot_price = quotes[self.primary_symbol]["price"]
        atr = indicators_sc.get("atr", spot_price * 0.005)
        forecast_suite = ForecastOrchestrator.run_prediction_pipeline(df_enriched, spot_price, atr)

        # 9. Trading Decision
        decision_data = TradingDecisionEngine.evaluate(
            spot_price=spot_price,
            indicators=indicators_sc,
            mtf_data=mtf_data,
            order_flow=order_flow_data,
            market_structure=market_structure_data,
            market_breadth=breadth_data,
        )

        # Update cache
        self.cache.update_analytics(self.primary_symbol, {
            "indicators": indicators_sc,
            "order_flow": order_flow_data,
            "market_structure": market_structure_data,
            "market_breadth": breadth_data,
            "institutional_flow": inst_flow,
            "mtf": mtf_data,
        })
        self.cache.update_forecasts(self.primary_symbol, forecast_suite)
        self.cache.update_signals(self.primary_symbol, decision_data)

        # System status
        api_state = "LIVE_AUTHENTICATED" if self.client.is_authenticated else "OFFLINE_SIMULATION"
        self.cache.update_system_status(api_state, "Data feeds successfully synchronized.")
        self.cache.save_to_snapshot()

        self.last_refresh_time = now
        self.next_refresh_countdown = self.refresh_interval

    def build_layout(self) -> Layout:
        """Constructs Rich Layout Grid."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="cards", size=7),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=7),
        )
        layout["main"].split_row(
            Layout(name="left_col", ratio=1),
            Layout(name="right_col", ratio=1),
        )
        return layout

    def render_header(self) -> Panel:
        """Renders header banner with market hours, API status, and refresh countdown."""
        snap = self.cache.get_snapshot()
        m_stat = snap.get("market_status", {})
        sys_stat = snap.get("system_status", {})

        phase = m_stat.get("phase", "UNKNOWN")
        phase_color = "green" if m_stat.get("is_open") else "yellow"

        api_status = sys_stat.get("api_status", "UNKNOWN")
        api_color = "green" if "LIVE" in api_status else "cyan"

        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=2)
        grid.add_column(justify="center", ratio=3)
        grid.add_column(justify="right", ratio=2)

        left = Text.from_markup(f"[bold white]LIVE INDIAN MARKET TERMINAL[/bold white] | [cyan]{self.primary_symbol}[/cyan]")
        mid = Text.from_markup(f"Status: [{phase_color}]{phase}[/{phase_color}] | Feed: [{api_color}]{api_status}[/{api_color}]")
        right = Text.from_markup(
            f"Updated: [bold]{get_ist_now().strftime('%H:%M:%S')}[/bold] | "
            f"Next: [bold yellow]{int(self.next_refresh_countdown)}s[/bold yellow]"
        )

        grid.add_row(left, mid, right)
        return Panel(grid, style="bold blue on #11111b")

    def render_instrument_cards(self) -> Table:
        """Renders quick-glance cards for NIFTY, BANKNIFTY, and INDIA VIX."""
        table = Table(expand=True, box=None, padding=(0, 1))
        table.add_column("Instrument", justify="left")
        table.add_column("Price", justify="right")
        table.add_column("Change", justify="right")
        table.add_column("Change %", justify="right")
        table.add_column("High / Low", justify="center")
        table.add_column("Feed Source", justify="right")

        for sym in ["BTC", "NIFTY", "BANKNIFTY", "INDIAVIX"]:
            q = self.cache.quotes.get(sym, {})
            price = q.get("price", 0.0)
            chg = q.get("change", 0.0)
            chg_pct = q.get("change_pct", 0.0)
            h = q.get("high", price)
            l = q.get("low", price)
            src = q.get("source", "OFFLINE")
            curr = "$" if sym == "BTC" else ("" if sym == "INDIAVIX" else "₹")

            color = "green" if chg >= 0 else "red"
            sign = "+" if chg >= 0 else ""

            table.add_row(
                f"[bold white]{sym}[/bold white]",
                f"[bold]{curr}{price:,.2f}[/bold]",
                f"[{color}]{sign}{chg:,.2f}[/{color}]",
                f"[{color}]{sign}{chg_pct:.2f}%[/{color}]",
                f"[dim]{h:,.1f} / {l:,.1f}[/dim]",
                f"[dim cyan]{src}[/dim cyan]",
            )

        return table

    def render_internals_panel(self) -> Panel:
        """Renders Market Internals (Breadth, Order Flow, Structure, VWAP/EMA)."""
        snap = self.cache.get_snapshot()
        analytics = snap.get("analytics", {}).get(self.primary_symbol, {})

        ind = analytics.get("indicators", {})
        flow = analytics.get("order_flow", {})
        struct = analytics.get("market_structure", {})
        breadth = analytics.get("market_breadth", {})
        inst = analytics.get("institutional_flow", {})

        tbl = Table(expand=True, box=None)
        tbl.add_column("Metric", style="dim white")
        tbl.add_column("Reading / Status", style="bold")

        # VWAP & EMA
        vwap = ind.get("vwap", 0.0)
        ema10 = ind.get("ema10", 0.0)
        ema20 = ind.get("ema20", 0.0)
        close = ind.get("close", 0.0)
        vwap_status = "[green]ABOVE VWAP[/green]" if close > vwap else "[red]BELOW VWAP[/red]"
        tbl.add_row("Session VWAP", f"₹{vwap:,.2f} ({vwap_status})")
        tbl.add_row("Moving Averages", f"EMA10: ₹{ema10:,.2f} | EMA20: ₹{ema20:,.2f}")
        tbl.add_row("RSI (14) / ATR", f"{ind.get('rsi', 50.0):.1f} | ATR: {ind.get('atr', 0.0):.1f} pts")

        # Order Flow & CVD
        cvd_state = flow.get("order_flow_state", "NEUTRAL")
        flow_color = "green" if "BULLISH" in cvd_state else ("red" if "BEARISH" in cvd_state else "yellow")
        tbl.add_row("Order Flow & CVD", f"[{flow_color}]{cvd_state}[/{flow_color}] (CVD: {flow.get('cvd', 0):+d})")
        tbl.add_row("Buyer vs Seller Pressure", f"Buyers {flow.get('buyer_percentage', 50.0):.1f}% | Sellers {flow.get('seller_percentage', 50.0):.1f}%")

        # Market Structure
        struct_state = struct.get("structure_state", "CONSOLIDATION")
        struct_color = "green" if "BULLISH" in struct_state else ("red" if "BEARISH" in struct_state else "yellow")
        tbl.add_row("Market Structure", f"[{struct_color}]{struct_state}[/{struct_color}]")
        tbl.add_row("Nearest Levels", f"Support: ₹{struct.get('nearest_support', 0.0):,.1f} | Resist: ₹{struct.get('nearest_resistance', 0.0):,.1f}")

        # Market Regime & Volatility
        regime_data = analytics.get("market_regime", {})
        regime_label = regime_data.get("regime", "SIDEWAYS_CONSOLIDATION")
        regime_color = "green" if "BULLISH" in regime_label else ("red" if "BEARISH" in regime_label else ("yellow" if "SIDEWAYS" in regime_label else "cyan"))
        adx_val = regime_data.get("adx", 0.0)
        chop_val = regime_data.get("chop_index", 50.0)
        tbl.add_row("Market Regime", f"[{regime_color}]{regime_label}[/{regime_color}] (ADX: {adx_val:.1f} | Chop: {chop_val:.1f})")

        # News & Event Risk
        news_data = analytics.get("news_and_events", {})
        event_risk = news_data.get("event_risk_level", "LOW")
        risk_color = "red" if event_risk == "HIGH" else ("yellow" if event_risk == "MODERATE" else "green")
        news_sent = news_data.get("market_sentiment_label", "NEUTRAL")
        tbl.add_row("News & Event Risk", f"[{risk_color}]Risk: {event_risk}[/{risk_color}] | Sentiment: [dim]{news_sent}[/dim]")

        # Breadth & Institutions
        adv = breadth.get("advances", 25)
        dec = breadth.get("declines", 25)
        tbl.add_row("Market Breadth (NIFTY)", f"[green]{adv} Adv[/green] / [red]{dec} Dec[/red] (ADR: {breadth.get('adr', 1.0):.2f})")
        tbl.add_row("Institutional Flow", f"[dim]{inst.get('interpretation', 'Unavailable')[:42]}[/dim]")

        return Panel(tbl, title=f"[bold]Market Internals ({self.primary_symbol})[/bold]", border_style="blue")

    def render_forecasts_panel(self) -> Panel:
        """Renders Multi-Timeframe Alignment and Predictive Forecasts."""
        snap = self.cache.get_snapshot()
        analytics = snap.get("analytics", {}).get(self.primary_symbol, {})
        mtf = analytics.get("mtf", {})
        forecasts = snap.get("forecasts", {}).get(self.primary_symbol, {})

        # MTF Table
        mtf_table = Table(expand=True, box=None, padding=(0, 1))
        mtf_table.add_column("Timeframe", style="bold")
        mtf_table.add_column("Direction")
        mtf_table.add_column("Momentum")
        mtf_table.add_column("Confidence")

        for tf, data in mtf.get("timeframes", {}).items():
            d = data.get("direction", "SIDEWAYS")
            d_color = "green" if d == "BULLISH" else ("red" if d == "BEARISH" else "yellow")
            mtf_table.add_row(
                tf,
                f"[{d_color}]{d}[/{d_color}]",
                f"[dim]{data.get('momentum', 'NEUTRAL')}[/dim]",
                f"{data.get('confidence_pct', 50.0):.0f}%",
            )

        # Forecast Table
        f_table = Table(expand=True, box=None, padding=(0, 1))
        f_table.add_column("Horizon", style="bold")
        f_table.add_column("Forecast")
        f_table.add_column("Target Range")
        f_table.add_column("Prob (UP)")

        for h, f_data in forecasts.get("horizons", {}).items():
            f_dir = f_data.get("direction", "FLAT")
            f_color = "green" if f_dir == "UP" else ("red" if f_dir == "DOWN" else "yellow")
            low = f_data.get("target_lower", 0.0)
            high = f_data.get("target_upper", 0.0)
            p_up = f_data.get("probability_up", 0.5)

            f_table.add_row(
                h,
                f"[{f_color}]{f_dir}[/{f_color}]",
                f"₹{low:,.1f} - ₹{high:,.1f}",
                f"{p_up * 100:.1f}%",
            )

        layout_col = Table.grid(expand=True)
        layout_col.add_row(mtf_table)
        layout_col.add_row(Text.from_markup("\n[bold]Directional Movement Forecasts[/bold]"))
        layout_col.add_row(f_table)

        return Panel(layout_col, title="[bold]Multi-Timeframe & Forecast Models[/bold]", border_style="magenta")

    def render_decision_footer(self) -> Panel:
        """Renders BUY / SELL / WAIT Decision Banner with SMC Setup, Fixed Entry Anchor, and Reversal Risk."""
        snap = self.cache.get_snapshot()
        sig = snap.get("signals", {}).get(self.primary_symbol, {})

        dec = sig.get("decision", "WAIT")
        color = "bold white on green" if dec == "BUY" else ("bold white on red" if dec == "SELL" else "bold black on yellow")

        entry = sig.get("entry_zone", "N/A")
        sl = sig.get("stop_loss")
        t1 = sig.get("target_1")
        t2 = sig.get("target_2")
        rr = sig.get("risk_reward_ratio", "1:2.0")
        conf = sig.get("confidence_pct", 50.0)
        curr = "$" if self.primary_symbol == "BTC" else "₹"

        sl_str = f"{curr}{sl:,.2f}" if sl is not None else "N/A"
        t1_str = f"{curr}{t1:,.2f}" if t1 is not None else "N/A"
        t2_str = f"{curr}{t2:,.2f}" if t2 is not None else "N/A"

        # SMC Details
        smc_meta = sig.get("smc_setup", {})
        smc_type = smc_meta.get("setup_type", "SMC / Structural")
        rev_data = smc_meta.get("reversal_risk", {})
        rev_chance = rev_data.get("chance_pct", 25.0)
        rev_level = rev_data.get("risk_level", "LOW")

        rev_color = "green" if rev_level == "LOW" else ("yellow" if rev_level == "MODERATE" else "red")

        grid = Table.grid(expand=True)
        grid.add_column(ratio=3)
        grid.add_column(ratio=5)

        decision_banner = (
            f"[{color}]  DECISION: {dec}  [/{color}]  (Confidence: [bold]{conf:.0f}%[/bold])\n"
            f"Setup: [cyan bold]{smc_type}[/cyan bold]\n"
            f"Fixed Entry: [bold yellow]{entry.replace('₹', curr)}[/bold yellow] | SL: [red]{sl_str}[/red]\n"
            f"Targets: [green]T1: {t1_str} | T2: {t2_str}[/green] (R:R {rr})\n"
            f"Reversal Risk: [{rev_color}]{rev_level} ({rev_chance:.0f}% chance)[/{rev_color}]"
        )

        # Reasons summary (show first 3 key drivers)
        reasons = sig.get("reasons", [])
        reasons_text = "\n".join([f"• {r.replace('₹', curr)}" for r in reasons[:3]]) if reasons else "Evaluating internals..."

        grid.add_row(decision_banner, Text.from_markup(f"[dim]{reasons_text}\n[yellow]Mandate: Analytical signal only. No automated orders.[/yellow][/dim]"))

        return Panel(grid, title="[bold]Trader's Action Playbook (SMC & Institutional Flow)[/bold]", border_style="green" if dec == "BUY" else ("red" if dec == "SELL" else "yellow"))

    def render(self) -> Layout:
        """Assembles full terminal dashboard layout."""
        layout = self.build_layout()
        layout["header"].update(self.render_header())
        layout["cards"].update(self.render_instrument_cards())
        layout["left_col"].update(self.render_internals_panel())
        layout["right_col"].update(self.render_forecasts_panel())
        layout["footer"].update(self.render_decision_footer())
        return layout

    def run(self, once: bool = False):
        """Main execution loop with smooth in-place refresh."""
        self.refresh_market_data()

        if once:
            console.print(self.render())
            return

        with Live(self.render(), console=console, refresh_per_second=2, screen=False) as live:
            while self.is_running:
                now = time.time()
                elapsed = now - self.last_refresh_time
                self.next_refresh_countdown = max(0.0, self.refresh_interval - elapsed)

                if elapsed >= self.refresh_interval:
                    self.refresh_market_data()

                live.update(self.render())
                time.sleep(0.5)

def main():
    parser = argparse.ArgumentParser(description="Live Indian Market Terminal (CLI)")
    parser.add_argument("--interval", type=int, default=DEFAULT_REFRESH_INTERVAL_SECONDS, help="Refresh interval (seconds)")
    parser.add_argument("--symbol", type=str, default="NIFTY", help="Primary instrument (NIFTY, BANKNIFTY)")
    parser.add_argument("--once", action="store_true", help="Render single snapshot and exit")
    args = parser.parse_args()

    app = LiveTerminalApp(refresh_interval=args.interval, primary_symbol=args.symbol)
    app.run(once=args.once)

if __name__ == "__main__":
    main()
