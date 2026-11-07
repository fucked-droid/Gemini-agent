# System Requirements — IPO Intelligence Engine

## Functional Requirements
- **FR-1 [Data Schema & Validation]**: Define strictly typed schemas (`IPOMeta`, `FinancialHistory`, `IssueStructure`, `PeerComparison`, `RiskMetrics`).
- **FR-2 [Financial Engine]**: Compute 3-year Revenue CAGR, PAT CAGR, ROCE, RoNW, CFO/PAT ratio, and debt solvency metrics.
- **FR-3 [Valuation Engine]**: Benchmark P/E, P/B, EV/EBITDA against industry peers, compute PEG ratio, and calculate promoter greed premium/discount.
- **FR-4 [Governance & Structure Engine]**: Audit Fresh Issue vs. OFS split, post-issue promoter holding, share pledging, and legal/tax contingent risks.
- **FR-5 [SME Risk Engine]**: Detect client concentration traps, working capital cycles, and apply SME exchange risk adjustments.
- **FR-6 [Institutional Composite Scorer]**: Produce 0-100 score and 4-tier verdict (`STRONG_BUY`, `BUY_ON_DIPS`, `SPECULATIVE`, `AVOID_TRAP`).
- **FR-7 [Report & Notification Engine]**: Generate CLI executive terminal report and formatted Telegram alerts formatted for long-term investors.

## Non-Functional Requirements
- **NFR-1 [Zero Division / Safe Fallbacks]**: Gracefully handle missing fiscal years, negative earnings (loss-making startups), and zero-revenue scenarios.
- **NFR-2 [High Test Coverage]**: 100% unit test coverage for all financial formulas, scoring bounds, and edge cases.
- **NFR-3 [Fast Execution]**: Complete full fundamental analysis of an IPO in $< 100$ milliseconds.
