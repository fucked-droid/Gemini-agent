# 🏛️ IPO Intelligence Engine

> Short-Term Listing Gain, Quick Profit Booking & T+0 Exit Strategy System for **Mainboard** & **SME** IPOs.

## 🎯 Purpose & Strategy: "Apply, Book Profit, and Sell"
Retail traders don't want to get stuck bagholding overpriced IPOs. 
The **IPO Intelligence Engine** evaluates live Grey Market Premium (GMP), Institutional QIB subscription rushes, and float dynamics to answer:
1. **Should you apply for quick listing gain?**
2. **What is the expected listing profit per lot (₹)?**
3. **Exact Listing Day (T+0) 9:15 AM Sell Strategy: When and how to exit to lock in 100% gains.**

---

## 🔍 Core Evaluation Pillars

1. **📊 Financial Health & Growth Engine (3-Year Audit)**:
   - 3-Year Revenue CAGR & PAT CAGR.
   - Operating Margin (EBITDA) expansion / contraction trends.
   - Capital Efficiency: Return on Capital Employed (ROCE) and Return on Net Worth (RoNW/ROE).
   - Cash Flow Conversion ($CFO / PAT$): Flags paper profits with negative operating cash flows.
   - Balance Sheet Fortification: Debt-to-Equity ($D/E$) ratio.

2. **🏷️ Valuation & Peer Multiples Benchmarking**:
   - Implied Post-Issue P/E & P/B vs listed industry peers.
   - Promoter Greed Premium/Discount calculation vs Sector Median.
   - PEG Ratio (Price/Earnings Growth).

3. **🏛️ Issue Structure & Corporate Governance**:
   - Fresh Issue % vs. Offer for Sale (OFS) %.
   - Promoter Post-Issue Skin in the Game & Share Pledge %.
   - Pending litigations and contingent liabilities as % of Net Worth.
   - Statutory Auditor Qualifications.

4. **🏭 SME Operational & Liquidity Guardrails (NSE Emerge / BSE SME)**:
   - Customer concentration risk (Top 3 clients % of revenue).
   - Working Capital & Debtor Days cycle.
   - Minimum ticket size (₹1,00,000+ per lot) & market-maker spread friction.

---

## ⚡ Quick Start

### 1. Scan All Active & Sample IPOs
```bash
python cli.py scan
```

### 2. Analyze a Specific IPO
```bash
python cli.py analyze data/sample_mainboard_ipo.json
```

### 3. Send Telegram Notification
```bash
python cli.py scan --telegram
```

### 4. Run Test Suite
```bash
python run_all_tests.py
```

---

## 📱 Termux Mobile Compatibility
Built purely on Python standard library (`dataclasses`, `urllib`, `argparse`, `math`, `json`). Zero binary C-extension dependencies, making it 100% plug-and-play on **Android Termux**!
