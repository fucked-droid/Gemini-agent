# Product Requirements Document (PRD)
# IPO Intelligence Engine: Short-Term Listing Gain, T+0 Exit & 4-Pillar Fundamental System

## 1. Executive Summary
The **IPO Intelligence Engine** is an institutional-grade primary market intelligence platform for Indian IPOs (both **Mainboard** on NSE/BSE and **SME** on NSE Emerge / BSE SME). 

The system unifies real-time live market scraping (Chittorgarh & NSE India) with a disciplined Short-Term Listing Gain (T+0 9:15 AM exit) playbook and a 4-Pillar Fundamental Safety Floor, ensuring retail investors capture listing pops while systematically avoiding promoter exit traps.

---

## 2. Core Pillars & Architecture

### Pillar 1: Real-Time Live Feed & Issue Structure Audit
- **Direct Scraping**: Real-time integration with Chittorgarh and NSE India with zero stale data filtering.
- **Metrics Tracked**: Live Grey Market Premium (GMP ₹ and %), Kostak/Sauda rates, QIB/HNI/Retail subscriptions, and official 7-10 day market event calendars.
- **Issue Structure Audit**: Strict breakdown of Fresh Issue vs Offer for Sale (OFS). Flags offerings with > 70% OFS as promoter cash-out risks.

### Pillar 2: Short-Term Listing Gain & 9:15 AM T+0 Playbook
- **Expected Listing Pop**: Calculates expected listing price (₹), listing gain (%), and profit per lot (₹).
- **Listing Day (T+0) Rules**:
  - 9:00 AM – 9:08 AM discovery assessment.
  - 9:15 AM bell market sell to secure 100% allotment gains.
  - Upper Circuit trailing stop trigger for momentum runners.
  - Cut-loss emergency execution for discount listing traps.

### Pillar 3: 4-Pillar Fundamental Safety Floor
- **Financial Quality**: 3-Year Revenue CAGR & PAT CAGR audit with EBITDA margin stability.
- **Capital Efficiency**: ROCE and RoNW/ROE efficiency (benchmarked against > 15-20% institutional standards).
- **Cash Flow Conversion**: Operating Cash Flow to Net Profit ($CFO / PAT$) checks to flag paper profit traps.
- **Valuation Benchmarking**: Implied post-issue P/E, P/B, EV/EBITDA vs listed peers, with promoter greed premium calculation.

### Pillar 4: SME-Specific Operational Guardrails (NSE Emerge / BSE SME)
- **Customer Concentration Risk**: Automated risk rating if Top 3 clients exceed 65% of revenue.
- **Working Capital Cycles**: Scans debtor days and cash conversion friction.
- **Liquidity & Spread Guardrails**: Calculates ₹1,00,000+ minimum lot ticket requirements and market-maker 2-way bid-ask spread impact.

### Pillar 5: Mobile & Android Termux Compatibility
- **Zero Binary Dependencies**: Built 100% on pure Python standard library (`dataclasses`, `urllib.request`, `json`, `argparse`, `ssl`).
- **Universal Execution**: Instant execution on Android Termux, Linux servers, macOS, and Windows without `pip install` or compilation.
- **Telegram Bot Sentinel**: Automated mobile alerts with HTML formatting and multi-endpoint failover.

### Pillar 6: Test Suite & Verification
- **14/14 Unit & Integration Tests**: 100% test pass rate across financial analysis, governance audits, SME risks, and listing playbooks.

---

## 3. Decision Framework & Short-Term Tiers
1. 🚀 **APPLY FOR LISTING POP (STRONG BUY & SELL)** (Score $\ge 75$): Explosive QIB rush, high GMP (> 20%), strong fresh issue, clean governance.
2. ⚡ **APPLY FOR SPECULATIVE FLIP** (Score $60 - 74$): Decent GMP (10-20%), acceptable subscription, strict 9:15 AM cut rule.
3. ✋ **AVOID / LOW LISTING GAIN** (Score $45 - 59$): Flat GMP (< 10%), weak institutional demand, high float.
4. 🛑 **STRICT AVOID / DISCOUNT TRAP** (Score $< 45$): Negative GMP, heavy OFS, negative CFO, high debtor days.
