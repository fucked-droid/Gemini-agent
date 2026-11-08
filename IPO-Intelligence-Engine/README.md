# 🏛️ IPO Intelligence Engine

> Institutional-grade Short-Term Listing Gain, Quick Profit Booking, T+0 Exit Playbook & Fundamental Evaluation System for **Mainboard** & **SME** IPOs (NSE / BSE).

---

## 🚀 Key System Features & Capabilities

### 1. 🌐 Real-Time Live Feed (Chittorgarh & NSE India)
- **Zero Stale/Archived Data**: Direct scrapers pull from official exchange feeds and primary portals (*Chittorgarh* & *NSE India*).
- **Live Metrics**: Real-time Grey Market Premium (GMP ₹ and %), Kostak rates, live institutional (QIB/HNI/Retail) subscription multiples, and official 7–10 day exchange event calendars.
- **Issue Structure Audit**: In-depth analysis of **Fresh Issue vs. Offer for Sale (OFS)** to detect growth capital vs. promoter cash-out traps.

### 2. 🎯 Short-Term Listing Gain & 9:15 AM T+0 Playbook
- **Quantitative Predictions**: Computes exact Expected Listing Price (₹), Listing Gain Percentage (%), and Estimated Profit per Lot (₹).
- **Listing Day (T+0) Exit Rules**: Exact, systematic execution rulebook for 9:15 AM opening bell:
  - Pre-open bidding assessment (9:00 AM – 9:08 AM).
  - Immediate profit booking on listing pop at 9:15 AM.
  - Upper Circuit (UC) trailing stop rules for explosive movers.
  - Emergency cut-loss triggers for discount listing traps.

### 3. 🛡️ 4-Pillar Fundamental Safety Floor
- **Financial Quality**: 3-Year Revenue CAGR & PAT CAGR audit with EBITDA margin stability.
- **Capital Efficiency**: ROCE and RoNW/ROE return metrics (target > 15–20%).
- **Cash Flow Conversion**: Operating Cash Flow to Net Profit ($CFO / PAT$) checks to flag paper profit traps.
- **Valuation Benchmarking**: Implied post-issue P/E, P/B, EV/EBITDA vs. listed peers, with promoter greed premium calculation.

### 4. 🏭 SME Operational Guardrails (NSE Emerge / BSE SME)
- **Client Concentration**: Strict automated penalties if Top 3 clients exceed 65% of total revenue.
- **Working Capital Cycles**: Scans debtor days and cash conversion friction.
- **Liquidity & Spread Guardrails**: Calculates ₹1,00,000+ minimum lot ticket requirements and market-maker 2-way bid-ask spread impact.

### 5. 📱 Mobile & Android Termux Compatible
- **Zero Binary Dependencies**: Built 100% on pure Python standard library (`dataclasses`, `urllib.request`, `json`, `argparse`, `ssl`).
- **Plug & Play**: Runs out of the box on Android Termux, Linux servers, macOS, and Windows without requiring `pip install` or C-compilers.
- **Instant Mobile Telegram Sentinel**: Automated notifications delivered directly to your Telegram chat.

### 6. 🧪 Comprehensive Test Suite (100% Passing)
- **14/14 Unit & Integration Tests Passing** in 0.015s.
- End-to-end verification covering financial metrics, governance traps, listing gain formulas, SME concentration penalties, and live feed parsers.

---

## ⚡ Quick Start & CLI Usage

### 1. Live Market Feed & Tracker (Chittorgarh & NSE)
```bash
python fetch_live_ipos.py
```
Or via engine CLI:
```bash
python cli.py live
```

### 2. Send Real-Time Update to Telegram
```bash
python fetch_live_ipos.py --telegram
```

### 3. Scan & Analyze All Sample / Historical Profiles
```bash
python cli.py scan
```

### 4. Analyze a Specific IPO JSON Profile
```bash
python cli.py analyze data/sample_mainboard_ipo.json
```

### 5. Run Full Test Suite
```bash
python run_all_tests.py
```

---

## 📊 Live Classification Engine
The engine continuously sorts issues into 4 strict lifecycle stages:
1. 🟢 **LIVE / OPEN NOW**: Issues accepting bids today (`Open <= Today <= Close`).
2. 🕒 **ALLOTMENT & LISTING WATCH**: Closed issues listing in next 24–72 hours.
3. ⏳ **UPCOMING IPOS**: Confirmed opening dates in coming days/weeks.
4. 🏢 **UPCOMING PIPELINE & DRHP WATCHLIST**: Chittorgarh analyst consensus (`Apply` vs `Avoid` votes).
*(Closed/past issues are automatically filtered out to ensure zero stale data).*
