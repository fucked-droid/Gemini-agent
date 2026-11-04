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
