# Product Requirements Document (PRD) — Market Intelligence & Live Terminal Overhaul

## Objective
Implement critical fixes and high-priority trading intelligence capabilities for the Live Indian Market Terminal, Daily Market Regime Engine, and web/CLI interfaces:

### Critical — Must Fix First
1. [x] **Task 1: Fix Live NIFTY, BANKNIFTY and INDIA VIX Feeds**
   - Correct parquet paths (`nifty_df_master.parquet`, `banknifty_df_master.parquet`, `india_vix_master.parquet`).
   - Implement live quote and candle fetching for NIFTY, BANKNIFTY, and INDIA VIX via Yahoo Finance / NSE with graceful fallback.
   - Map INDIA VIX correctly in configs, cache, and WebSocket broadcasts.
   - Fix ticker mappings (`val-vix`, `chg-vix`, `ticker-vix`) in web UI and CLI layout height.

2. [x] **Task 2: Implement Proper Market-Open/Closed Detection**
   - Implement precise IST session time detection (09:00 Pre-Market, 09:15-15:30 Regular Session, 15:30-16:00 Post-Market, Closed/Weekend/Holiday).
   - Accurate 2026 NSE exchange holiday calendar & last verified trading session date calculation.
   - Update operational states across backend and UI pills/banners with countdown to open/close.

3. [x] **Task 3: Display Data Source and Last-Updated Timestamps**
   - Display data source (e.g. `DhanHQ Official v2 API (Live)`, `Yahoo Finance Live`, `NSE India API`, `Historical Parquet Master`) and exact timestamp across web header, footer, terminal table, and decision envelopes.

4. [x] **Task 4: Remove Placeholder Values from Live Trading Signals**
   - Eliminate hardcoded HTML numbers, `--.--` unpopulated states, and fake trade levels on `WAIT` signals.
   - In `WAIT` / `STAND ASIDE` state, set stop-loss and targets to `None` / `N/A`, displaying dynamic Watch Levels instead.

5. [x] **Task 5: Verify Option-Chain Data Against Actual Exchange/Provider**
   - Verify option-chain underlying price matches live spot (within ±2%).
   - Verify standard strike intervals (50 for NIFTY, 100 for BANKNIFTY) and active expiry dates.
   - Add verification status badges (`VERIFIED_EXCHANGE`, `VERIFIED_SNAPSHOT`, `UNAVAILABLE`).

6. [x] **Task 6: Resolve Contradictory Signals and Price Levels**
   - Ensure strict directional confluence: do not allow BUY signals when higher-timeframe and intraday internals are bearish without confirmed structural reversal.
   - Ensure strict mathematical price level geometry ($SL < Entry < T1 < T2$ for BUY; $SL > Entry > T1 > T2$ for SELL; None for WAIT).

### P1 — Trading Intelligence (High Priority)
7. [x] **Task 7: Add Proper Multi-Timeframe Analysis (5m, 15m, 1h, Daily)**
   - Analyze 5m (tactical entry), 15m (intraday swing), 1h (session bias), and Daily (macro regime).
   - Evaluate composite alignment and confluence classifications across all 4 specific tiers.

8. [x] **Task 8: Add Option Greeks, IV, and OI Analysis**
   - Implement Black-Scholes Greeks (Delta, Gamma, Theta, Vega) for index options.
   - Compute ATM Implied Volatility (IV) and IV Skew.
   - Calculate Put-Call Ratio (OI & Volume), net OI changes, Call Wall, Put Floor, and Max Pain.
   - Provide strike-by-strike derivatives radar table.

9. [x] **Task 9: Add Entry, Stop-Loss, Targets, and Invalidation Levels**
   - Dynamic structural entry anchored to Order Blocks / FVGs / VWAP.
   - Dynamic stop-loss anchored to ATR and structural pivots.
   - Target 1 (1.5R) and Target 2 (2.5R) with risk/reward calculation.
   - Explicit invalidation levels and cancellation trigger conditions.

10. [x] **Task 10: Add Market Regime Detection (Trending, Sideways, Volatile)**
    - Implement `MarketRegimeDetector` synthesizing ADX, +DI/-DI, Bollinger Bandwidth, Choppiness Index, ATR ratio, and India VIX.
    - Classify into Trending Bullish, Trending Bearish, Sideways Consolidation, Volatile Expansion, and Low-Volatility Compression.
    - Provide tactical strategy guidance and regime conviction score.

11. [x] **Task 11: Add News and Event Risk Detection**
    - Ingest top Indian financial market news headlines via RSS feeds.
    - Compute headline sentiment and macro theme scoring.
    - Detect high-impact macro risk events (Union Budget, RBI MPC, NSE Expiry, US CPI, FOMC).
    - Provide Event Risk Rating and recommended position sizing haircut.

12. [x] **Task 12: Comprehensive Integration, Testing & Verification**
    - Run full test suites (`python live-market-terminal/run_tests.py`, `python Daily-Market-Regime-Engine/run_all_tests.py`, `python IPO-Intelligence-Engine/run_all_tests.py`, `npm test`).
    - Verify 100% test pass rate across all suites.
    - CodeRabbit quality audit and atomic commit.
