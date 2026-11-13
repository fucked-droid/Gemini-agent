# Antigravity Supercharged Agent Instructions

This workspace operates under an advanced agentic stack combining **GSD Core**, **Roo Code Nightly**, **Ralph Loop for Antigravity**, and **CodeRabbit**. All agent sessions must adhere to these unified directives.

---

## 1. GSD Core — Spec-Driven Architecture & Context Hygiene
- **Never "Vibe Code"**: Always understand the phase, requirements, and acceptance criteria before modifying code.
- **Persistent State**: Read from and maintain state in `.planning/` (`STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md`) during complex features.
- **Anti-Context Rot**: Delegate deep exploration, research, or lengthy diagnostics to subagents or discrete task cycles so the main conversational context remains clean.
- **Phase Verification**: Every milestone or phase must pass validation tests before being declared complete.

---

## 2. Roo Code Nightly — Multi-Mode Engineering Protocols
- **Architect Mode**: When designing new features or refactoring modules, outline system boundaries, schemas, and interfaces first without premature coding.
- **Code Mode**: Make surgical, precise edits. Adhere to existing code conventions. Never rewrite working files unnecessarily.
- **Ask Mode**: Explain logic and explore files without introducing unwanted changes.
- **Debug Mode**: Follow scientific diagnosis: Reproduce -> Hypothesize -> Inspect -> Minimal Fix -> Verify.
- **Test Mode**: Maintain high test coverage for edge cases, null states, and error handling.

---

## 3. Ralph Loop for Antigravity (Updated) — Autonomous Iteration
- **Task Tracking**: Use `PRD.md` (or `tasks.md`) for discrete task lists and `progress.txt` for audit logging.
- **Continuous Execution**: In autonomous mode, self-direct through pending tasks without stalling for human approval on routine steps.
- **Hard Test Gates**: Run test commands (`npm test`, `pytest`, etc.) after every change. If tests fail, automatically self-correct until green.
- **Atomic Commits**: Commit changes after each successful verified task.

---

## 4. CodeRabbit — Automated Code Review & Quality Gates
- **Pre-Merge Audit**: Review all modified files against CodeRabbit quality standards before concluding tasks:
  1. **Correctness**: Zero off-by-one errors, proper async/await handling, no unhandled exceptions.
  2. **Security**: Zero SQL/Command injections, no exposed secrets or API keys, sanitization of inputs.
  3. **Robustness**: Graceful error handling and meaningful error messages.
  4. **Performance**: Avoid memory leaks, unclosed handles, and inefficient nested loops.
- Adhere to rules defined in `.coderabbit.yaml`.

---

## 5. Institutional Trading System Mandates (Market Engine Guardrails)
- **Automated Regression Testing**: Changes to any single module must NEVER break another. All test suites (`run_all_tests.py` and `npm test`) must maintain 100% pass rate before concluding any work.
- **Live vs Backtest Parity**: The live scanner (`live_scanner.py`, `scan_nifty.py`) and historical backtest/validation engines (`walk_forward.py`, `engine.py`) MUST calculate signals using identical mathematical formulas, thresholds, and indicators. Zero logic drift permitted.
- **Failure Recovery & Resilience**: All external interfaces must gracefully recover from Yahoo Finance / NSE API failures, network timeouts, stale/frozen data feeds, process crashes, and deduplicate live alert dispatches.
- **Paper Trading Validation**: Full system execution must support paper trading validation during live market hours (09:15 to 15:30 IST), verifying realistic fills, spread friction, and order flow delta.
- **Continuous Performance Monitoring**: Persistently monitor system edge over time: mathematical expectancy ($E$), profit factor ($PF$), maximum drawdown ($DD$), volatility slippage drag, and signal confidence calibration ($ECE$ & Brier score).
