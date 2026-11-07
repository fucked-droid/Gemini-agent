# Project Roadmap — IPO Intelligence Engine

## Phase 1: Core Domain Schemas & Test Fixtures
- Task 1.1: Implement `src/models/ipo_schema.py` dataclasses with validation and normalization.
- Task 1.2: Construct verified test datasets in `data/`:
  - `sample_mainboard_ipo.json` (High-quality compounder: Jyoti CNC / Premier Energies style)
  - `sample_sme_ipo.json` (High-growth SME: Tech/Engineering niche)
  - `sample_avoid_trap_ipo.json` (Promoter cash-out: 100% OFS, negative CFO, high debt)

## Phase 2: Fundamental Analysis Engines
- Task 2.1: `src/analyzers/financial_analyzer.py` (CAGR, ROCE, RoNW, CFO/PAT, Margin stability).
- Task 2.2: `src/analyzers/valuation_analyzer.py` (P/E, P/B, EV/EBITDA peer premium/discount, PEG).
- Task 2.3: `src/analyzers/governance_issue_analyzer.py` (Fresh vs OFS, promoter holding, pledge, litigation).
- Task 2.4: `src/analyzers/sme_risk_analyzer.py` (Customer concentration, working capital, liquidity penalty).

## Phase 3: Composite Scoring & Decision Synthesis
- Task 3.1: `src/scoring_engine.py` (Multi-pillar weighted score, tier verdict, investment thesis, risks).
- Task 3.2: `src/report_generator.py` (Rich terminal dashboard with ANSI colors, tables, and warnings).
- Task 3.3: `src/telegram_bot.py` (Telegram alert formatter for long-term fundamental investors).

## Phase 4: CLI & End-to-End Test Suite
- Task 4.1: Build `cli.py` for scan, inspect, and evaluate modes.
- Task 4.2: Write comprehensive test suite in `tests/` and `run_all_tests.py`.
- Task 4.3: Verify 100% test pass rate and validate on real-world Indian IPO scenarios.
