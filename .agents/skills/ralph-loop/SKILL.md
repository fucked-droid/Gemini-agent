---
name: ralph-loop
description: >-
  Use this skill to run or manage the Ralph Loop autonomous agent execution harness in Antigravity, including PRD task tracking, progress.txt state externalization, test verification gates, and continuous iterative self-correction loops.
---

# Ralph Loop for Antigravity (Updated)

The Ralph Loop is an autonomous execution methodology designed for Google Antigravity and VS Code. It solves the LLM context window degradation problem and removes the need for constant manual prompting by driving continuous, self-correcting development loops against persistent on-disk state.

---

## Core Operational Mechanics

Instead of keeping all history in the AI conversational memory, the Ralph Loop externalizes state into two files:
1. **`PRD.md`** (or `tasks.md`): Defines the goal, requirements, and an ordered list of atomic tasks with acceptance criteria.
2. **`progress.txt`**: Logs every completed iteration, test run result, and Git commit hash.

### Iterative Cycle Architecture

```text
       ┌───────────────────────────────┐
       │   Read PRD.md & progress.txt  │
       └──────────────┬────────────────┘
                      ▼
       ┌───────────────────────────────┐
       │  Identify Next Pending Task   │
       └──────────────┬────────────────┘
                      ▼
       ┌───────────────────────────────┐
       │      Implement Changes        │
       └──────────────┬────────────────┘
                      ▼
       ┌───────────────────────────────┐
       │     Run Automated Tests       │
       └──────────────┬────────────────┘
                      │
            ┌─────────┴─────────┐
         Passed               Failed
            │                   │
            ▼                   ▼
 ┌─────────────────────┐  ┌─────────────────────┐
 │ 1. Log to progress  │  │ 1. Read test errors │
 │ 2. Atomic Git commit│  │ 2. Apply fix        │
 │ 3. Check if all done│  │ 3. Re-run test gate │
 └──────────┬──────────┘  └─────────────────────┘
            ▼
   Next Iteration or Done
```

---

## File Formats

### 1. `PRD.md` Format

```markdown
# Product Requirements Document

## Objective
Build and verify the multi-timeframe regime detector.

## Acceptance Criteria
- [ ] Task 1: Create regime classifier utility in `lib/regime.js`
- [ ] Task 2: Implement volatility filter with 14-day ATR
- [ ] Task 3: Add unit tests in `test/regime.test.js`
- [ ] Task 4: Verify full test suite passes with 100% assertions
```

### 2. `progress.txt` Format

```text
[Ralph Loop Run Started: 2026-11-03 23:00:00]
[ITERATION 1] Task 1: Completed regime classifier utility. Tests passing. Commit: abc1234
[ITERATION 2] Task 2: Implemented volatility filter. Tests passing. Commit: def5678
```

---

## Autonomous Loop Rules for Antigravity

1. **Uninterrupted Execution**: When running in Ralph Loop mode, do not halt to ask the user permission for trivial step-by-step approvals. Continue executing tasks until either:
   - All tasks in `PRD.md` are checked off `[x]`.
   - A critical unresolvable blocker is reached.
   - The safety max iteration limit (default: 25) is reached.
2. **Strict Verification Gate**: Never mark a task as completed in `progress.txt` or `PRD.md` without running the test command (e.g., `npm test`, `pytest`) and confirming exit code 0.
3. **Atomic Commits**: Every task must be committed independently so changes can be audited or rolled back cleanly.
4. **Context Reset**: If memory or context starts growing large, write current status to `progress.txt`, summarize blockers, and resume from a clean state reading directly from disk.

---

## Helper Script

A PowerShell helper script is available at:
`C:\projects\gemini-agent\.agents\skills\ralph-loop\scripts\ralph-loop.ps1`
Use it to initialize the PRD template, check progress, or run automated verification cycles.
