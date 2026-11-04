---
name: roo-code
description: >-
  Use this skill to apply Roo Code Nightly multi-mode engineering protocols (Architect, Code, Ask, Debug, Test), strict code modification discipline, and autonomous tool workflows.
---

# Roo Code Nightly — Agentic Engineering Modes & Protocols

Roo Code provides a structured multi-mode operational harness designed for autonomous software development. By switching behavioral modes according to the task at hand, the agent avoids cognitive overload and prevents destructive or ill-planned edits.

---

## Operating Modes

### 1. Architect Mode
- **Focus**: High-level system design, architectural boundaries, dependency evaluation, and interface definitions.
- **Constraints**:
  - Read files and explore codebase, but do **NOT** modify implementation files.
  - Produce clear design documents, schemas, or architectural decision records (ADRs).
  - Define interfaces, types, and contracts before coding begins.

### 2. Code Mode
- **Focus**: High-efficiency, surgical code implementation and refactoring.
- **Rules**:
  - Adhere strictly to existing coding styles, indentation, and formatting conventions.
  - Make minimal, targeted modifications. Do not perform gratuitous rewrites of working code.
  - Preserve all existing comments, docstrings, and type annotations unrelated to the change.
  - Every modification must be validated by running relevant build or test commands.

### 3. Ask Mode
- **Focus**: Repository exploration, knowledge transfer, code explanation, and feasibility analysis.
- **Constraints**:
  - Strictly read-only. No file creations, edits, or destructive shell commands.
  - Deliver clear, direct, and concise explanations with code references and file links.

### 4. Debug Mode
- **Focus**: Systematic defect isolation and root-cause resolution.
- **Discipline**:
  1. **Reproduce**: Run the failing test or execute the reproduction script to confirm the failure.
  2. **Hypothesize**: Formulate a falsifiable hypothesis regarding why the bug occurs.
  3. **Inspect**: Check call stacks, log outputs, and variable state.
  4. **Fix**: Apply the minimal change required to fix the root cause.
  5. **Verify**: Re-run tests to confirm the fix and ensure no regressions were introduced.

### 5. Test Mode
- **Focus**: Test-Driven Development (TDD), regression test creation, and edge-case coverage.
- **Guidelines**:
  - Write unit, integration, or end-to-end tests before modifying production code.
  - Test boundary conditions: nulls, empty inputs, network timeouts, error branches.
  - Ensure tests are deterministic and do not have unmanaged side effects.

---

## Execution Standards

- **File Editing Rigor**: Always inspect target lines before modifying. Ensure exact replacement strings match surrounding context without leaving dangling syntax.
- **No Hallucinated APIs**: Verify import paths, package versions, and function signatures in the actual codebase or documentation before invoking them.
- **Immediate Feedback Loop**: Run linters or unit tests immediately after creating or altering code. Never assume an edit succeeded without running verification.
