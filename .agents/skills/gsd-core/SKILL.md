---
name: gsd-core
description: >-
  Use this skill when initializing or executing spec-driven development (SDD), managing project roadmaps, preventing LLM context rot, and running phased development loops (discuss, plan, verify, execute, ship).
---

# GSD Core (Git. Ship. Done.) — Spec-Driven Agentic Development

GSD Core is a context-engineering and spec-driven development framework designed to eliminate context degradation ("context rot") in long-running agent tasks. Instead of ad-hoc unconstrained coding, GSD Core organizes all software engineering work into structured, test-verified phases with persistent external state.

## Core Architectural Principles

1. **State Externalization**: Never rely on conversational memory for long-term project status. Keep ground truth in `.planning/` (`STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md`).
2. **Context Hygiene**: Split heavy research, planning, and validation into clean subagent contexts so the main coding context stays lean and accurate.
3. **Phase-Gated Discipline**: Every task follows: **Discuss / Clarify** -> **Plan** -> **Validate Plan** -> **Execute (Atomic Commits)** -> **Verify**.
4. **Autonomous Atomic Progress**: Every completed unit of work produces tested, passing code and an atomic Git commit.

---

## Directory Schema (`.planning/`)

When working with GSD Core on a project, maintain the following directory layout:

```text
.planning/
├── STATE.md          # Current active phase, blocker status, milestone progress
├── ROADMAP.md        # Sequential phases (e.g. Phase 1: Engine, Phase 2: API, Phase 3: Tests)
├── REQUIREMENTS.md   # Functional and non-functional requirements
└── PROJECT.md        # High-level architecture, tech stack, and core goals
```

### `STATE.md` Template

```markdown
# Project State

## Current Position
- **Active Phase**: Phase 1: Foundation
- **Current Task**: Task 1.2
- **Status**: IN_PROGRESS

## Phase Progress
- [x] Phase 1.1: Environment & Dependency Setup
- [ ] Phase 1.2: Core Domain Logic
- [ ] Phase 1.3: Verification & Test Suite

## Blockers / Decisions
- None
```

---

## Standard Workflows & Commands

### 1. Project Onboarding (`/gsd:onboard` or `/gsd:new-project`)
1. Inspect the repository root, existing dependencies, build scripts, and test suites.
2. Initialize `.planning/` directory if missing.
3. Write `PROJECT.md`, `REQUIREMENTS.md`, and initial `ROADMAP.md`.
4. Create `STATE.md` tracking Phase 1.

### 2. Phase Clarification (`/gsd:discuss-phase`)
1. Before writing code for a new phase, review requirements and identify architectural ambiguities.
2. Formulate focused design options or trade-offs.
3. Document decisions in `.planning/CONTEXT.md` or update `REQUIREMENTS.md`.

### 3. Plan & Validate (`/gsd:plan-phase`)
1. Break down the phase into atomic, testable steps.
2. Define explicit verification criteria for each step (command to run, expected output).
3. Self-review or delegate to a research/verification subagent to spot potential regression risks before coding.

### 4. Execute Phase (`/gsd:execute-phase`)
1. Execute one task at a time.
2. Follow strict code discipline: minimal invasive diffs, preserve docstrings/comments.
3. Immediately run the project's test suite or validation script.
4. On pass: update `STATE.md`, commit atomically (`git commit -m "feat(phase): completed task"`).
5. On fail: immediately isolate and fix the defect before proceeding.

### 5. Ship (`/gsd:ship`)
1. Run complete end-to-end regression tests and linters.
2. Update `ROADMAP.md` marking the phase complete.
3. Prepare summary of changes and tag or commit the release milestone.

---

## CLI Integration

When installed globally, GSD Core provides the following binaries:
- `gsd-core`: Core CLI orchestration command.
- `gsd-tools`: Utility functions for state inspection and validation.
- `gsd_run`: Headless agent runner for automated batch phases.
- `gsd-mcp-server`: MCP server exposing GSD workflow tools to AI agents.
