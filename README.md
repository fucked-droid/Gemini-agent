# Market & IPO Intelligence Suite

An institutional-grade Indian financial market analysis and primary market (IPO) intelligence platform, accompanied by an isolated fallback AI agent.

---

## 🏛️ Project Structure

```
├── Daily-Market-Regime-Engine/  # NIFTY 50 Regime, FII/DII, CVD Order Flow, Breadth & Charts
├── IPO-Intelligence-Engine/     # Mainboard & SME IPO Scanner, GMP Live Tracking & T+0 Exit
├── standalone-agent/            # Isolated fallback Gemini AI coding agent (Node.js SDK)
├── archive/scratch-scripts/     # Archived development tests and research experiments
├── .agents/                     # Unified agent skills library (GSD Core, Roo Code, Ralph Loop)
└── package.json                 # Unified quick-launch scripts
```

---

## 📊 1. Daily Market Regime Engine

Quant system for Indian indices (NIFTY 50) and sectoral breadth.

### Key Capabilities
- **Regime Classification**: Quantifies market state (Bullish, Strong Bullish, Mixed, Bearish) with transition probabilities.
- **Institutional Flows**: Tracks FII/DII cash and derivatives positioning.
- **Intraday Order Flow (CVD)**: Cumulative Volume Delta and buyer/seller absorption trap detection.
- **Market Breadth**: Advance/Decline ratio divergence and hollow rally traps.
- **Support & Resistance**: Dynamic pivot calculation and multi-timeframe level confirmation.
- **Telegram Sentinel**: Dispatches morning briefings and market updates.

### Quick Commands
```bash
# Complete regime scan with news
npm run scan:all

# Quick Nifty regime report
npm run scan:nifty

# Live intraday scan
npm run scan:live

# Run test suite (81 tests)
npm run test:market
```

---

## 🚀 2. IPO Intelligence Engine

Primary market intelligence platform covering Mainboard (NSE/BSE) and SME (NSE Emerge/BSE SME) issues.

### Key Capabilities
- **Live GMP Scraping**: Real-time Grey Market Premium tracking from Chittorgarh and NSE.
- **T+0 Listing Day Exit Playbook**: 9:15 AM profit-locking algorithms and Upper Circuit momentum trailing.
- **4-Pillar Safety Floor**: Revenue/PAT CAGR audits, ROCE/RoNW efficiency, and CFO-to-PAT checks.
- **SME Guardrails**: Identifies client concentration risk and high promoter OFS cash-out traps.
- **Mobile & Termux Ready**: Pure Python standard library with zero third-party dependencies.

### Quick Commands
```bash
# Scan all tracked IPOs
npm run ipo:scan

# View only currently open IPOs
npm run ipo:active

# View upcoming pipeline
npm run ipo:upcoming

# View ready-to-list IPOs (listing day candidates)
npm run ipo:listing

# Run Termux / Mobile Telegram Sentinel bot
npm run ipo:sentinel

# Run test suite (14 tests)
npm run test:ipo
```

---

## 🤖 3. Standalone Fallback Agent (`standalone-agent/`)

An isolated, fully independent Node.js coding agent powered by `@google/genai` and your own `GEMINI_API_KEY` from `.env`.

If external assistants are ever unavailable, you can run this CLI agent directly:
```bash
# Launch standalone agent
npm run agent

# Or from inside the directory:
cd standalone-agent
node index.js
```
*(Detailed architecture and tool specifications are preserved in `standalone-agent/README.md`)*.

---

## 🧪 Master Test Suite

Run full regression verification across both intelligence engines:
```bash
npm test
```
