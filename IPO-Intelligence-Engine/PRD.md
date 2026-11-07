# Product Requirements Document (PRD)
# IPO Intelligence Engine: Long-Term Fundamental Wealth & SME Evaluation System

## 1. Executive Summary
The **IPO Intelligence Engine** is an institutional-grade fundamental valuation and risk intelligence platform for Indian IPOs (both **Mainboard** on NSE/BSE and **SME** on NSE Emerge / BSE SME). 

Unlike shallow retail tools that solely track Grey Market Premium (GMP) for day-one flips, this engine conducts a rigorous audit of the company's **DRHP/RHP financial statements, competitive moat, promoter governance, debt obligations, peer valuation multiples, and issue structure (Fresh Issue vs OFS)** to determine if an IPO is an enduring **Long-Term Compounder** or a **Promoter Exit Trap**.

---

## 2. Core Pillars of Analysis

### Pillar 1: Financial Quality & Growth Engine (3-Year Audit)
- **Revenue CAGR & PAT CAGR**: Consistent top-line and bottom-line scaling over 3 fiscal years.
- **Capital Efficiency (ROCE & RoNW/ROE)**: Return on Capital Employed (target > 15-20%) and Return on Net Worth.
- **Earnings Quality / Cash Flow Conversion**: $CFO / PAT$ ratio. Flags companies reporting paper profits while bleeding operating cash flow ($CFO < 0$).
- **Balance Sheet Fortification**: Debt-to-Equity ($D/E$) ratio, interest coverage ratio, and debt trajectory.

### Pillar 2: Valuation & Peer Benchmarking
- **Relative Multiples**: Post-issue P/E, P/B, and EV/EBITDA compared against verified, listed domestic peers in the same industry.
- **Price-to-Growth (PEG Ratio)**: Ensures high P/E is justified by high growth ($PEG < 1.5$).
- **Greed Premium Calculation**: Computes the percentage premium or discount demanded by promoters relative to the industry peer median.

### Pillar 3: Issue Structure & Corporate Governance
- **Fresh Issue vs. Offer for Sale (OFS)**: High fresh issue indicates expansion capital; high OFS (> 70%) suggests early investors and promoters cashing out at peak valuations.
- **Object of Issue**: Classification of capital deployment (Growth Capex / R&D / Debt Reduction vs General Corporate Purposes).
- **Promoter Skin in the Game**: Post-issue promoter holding percentage and share pledge status.
- **Litigation & Contingent Liabilities**: Material legal proceedings as a percentage of net worth.

### Pillar 4: SME-Specific Risk Guardrails (NSE Emerge / BSE SME)
- **Customer Concentration Risk**: Percentage of revenue derived from top 3/top 5 clients. (High risk if > 60%).
- **Working Capital & Debtor Days**: Stretched cash cycles in small businesses.
- **Illiquidity & Lot Size Friction**: Factoring minimum 100k+ INR ticket size and 2-way market-making spreads into risk rating.

---

## 3. Decision Framework & Scoring Model
The engine synthesizes all quantitative and qualitative metrics into a **Fundamental Score (0 - 100)**:
- **Financial Quality Score (35%)**: Revenue/PAT CAGR, ROCE, RoNW, CFO/PAT conversion.
- **Valuation & Multiples Score (30%)**: P/E discount/premium vs peers, PEG ratio.
- **Issue Structure & Governance Score (20%)**: Fresh Issue %, promoter stake, low litigation.
- **Balance Sheet & Solvency Score (15%)**: Low D/E, healthy interest coverage.

### Output Classification Verdicts:
1. 💎 **LONG-TERM COMPOUNDER (STRONG BUY)** (Score $\ge 75$): Industry leader, ROCE > 20%, low debt, fair peer valuation, strong cash conversion.
2. 📈 **CONDITIONAL BUY (WAIT FOR POST-LISTING DIP)** (Score $60 - 74$): Exceptional business fundamentals, but rich IPO valuation leaves zero margin of safety. Recommended to accumulate on post-listing cooldown.
3. ⚠️ **SPECULATIVE / HIGH RISK** (Score $45 - 59$): Acceptable growth but burdened by customer concentration, debt, or short operating history.
4. 🛑 **AVOID / PROMOTER CASH-OUT TRAP** (Score $< 45$): High OFS, negative operating cash flows, exorbitant valuation premium vs listed peers, or dubious governance.

---

## 4. Technical Architecture & Tech Stack
- **Language**: Python 3.10+
- **Data Models**: Python dataclasses with strict type validation, missing-field fallbacks, and boundary assertions.
- **Storage**: JSON schemas for normalized IPO company profiles, 3-year historical financials, and peer datasets.
- **Reporting**: Terminal ANSI color dashboard, structured Markdown reports, and Telegram Bot notifications.
- **Testing**: 100% automated unit test coverage across all analyzers and edge cases.
