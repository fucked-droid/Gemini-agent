---
name: coderabbit
description: >-
  Use this skill to run AI-powered code reviews, security vulnerability audits, static logic verification, and pre-commit checks using CodeRabbit guidelines and CLI.
---

# CodeRabbit — AI Code Review & Quality Guardrails

CodeRabbit provides rigorous automated code reviews, catching logic bugs, security vulnerabilities, edge-case regressions, and architectural anti-patterns before code is committed or merged.

---

## Code Review Pillars

When reviewing or writing code under CodeRabbit standards, evaluate all diffs across six dimensions:

### 1. Correctness & Logic
- Off-by-one errors in loops, slices, and index operations.
- Unhandled null, undefined, or empty data states.
- Race conditions, missing async/await handling, or unhandled promise rejections.
- State mutation side effects in pure functions or shared data stores.

### 2. Security (OWASP Top 10)
- Injection vulnerabilities (SQL, Command, Shell injection via unsanitized strings).
- Insecure deserialization or eval-like constructs.
- Hardcoded secrets, API tokens, or credentials (always enforce environment variables).
- Insecure direct object references or missing permission checks.

### 3. Error Handling & Robustness
- Are error boundaries properly placed?
- Do catch blocks log contextually meaningful error messages rather than silently swallowing errors?
- Graceful degradation on network or third-party service failures.

### 4. Performance & Resource Leaks
- Unnecessary N+1 query patterns or repeated nested loops over large datasets.
- Unclosed file descriptors, open network sockets, or uncancelled timers.
- Excessive memory consumption or duplicate array allocations.

### 5. API & Documentation Integrity
- Preserving backwards compatibility of public interfaces.
- Updating or preserving relevant function comments, docstrings, and type definitions.

### 6. Test Completeness
- Did the change add or update corresponding test cases?
- Are edge cases covered (empty arrays, boundary numbers, error responses)?

---

## CodeRabbit CLI Commands

- `coderabbit review` or `cr review`: Run an in-depth code review on staged or uncommitted local changes.
- `coderabbit review --base main`: Review local branch changes against the main branch.
- `coderabbit auth login`: Authenticate with CodeRabbit account.
- `coderabbit config`: Validate or inspect active review settings.

---

## Review Output Format

When delivering a CodeRabbit-style review:
1. **Summary**: High-level overview of the change.
2. **Key Findings**: Ranked by severity (`Critical`, `Warning`, `Suggestion`).
3. **Actionable Recommendations**: Precise diff suggestions with file path and line numbers.
