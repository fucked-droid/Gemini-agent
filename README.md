# Gemini AI Coding Agent (`gemini-agent`)

A robust, autonomous coding assistant built with Node.js and the official Google Gen AI SDK (`@google/genai`), powered by `gemini-3.5-flash-lite` via the Google GenAI Interactions API (`ai.interactions.create`).

The agent features progressive token streaming, multi-turn conversational memory with persistent session storage, automated self-repair execution loops, cross-platform terminal execution, and strict security sandboxing.

---

## Architecture & Core Capabilities

- **Model & API Runtime:** `gemini-3.5-flash-lite` utilizing the Interactions API with progressive streaming (`stream: true`) and interaction delta aggregation.
- **Conversational Memory:** Preserves multi-turn state via `previous_interaction_id` chaining across turns.
- **Session Persistence:** Saves session metadata to `.gemini_sessions.json`, allowing sessions to be listed and resumed across restarts.
- **Autonomous Workflow & Auto-Repair Loop:** Executes autonomous multi-step tasks (up to 20 steps) with an automated repair counter (`MAX_REPAIR_ATTEMPTS = 5`) that captures diagnostic outputs and refines subsequent commands.
- **Cross-Platform Compatibility:** Runs on both Windows (`cmd.exe`) and Linux/macOS (`bash` / `sh`) with platform-aware path resolution and shell invocation.
- **Security Sandboxing:** Enforces workspace boundary containment, protected secrets isolation, dangerous command blacklisting (both POSIX and Windows), and authorized executable verification.

---

## Tool Ecosystem

The agent exposes 10 specialized developer tools:

1. **`list_files`**  
   Enumerates files and directories within the project workspace or any specified subdirectory (`path`), with optional `recursive` traversal and directory indicator formatting.

2. **`read_file`**  
   Reads text files inside the project workspace with path traversal validation and optional line-range pagination (`startLine`, `endLine`) for inspectable token-safe viewing.

3. **`write_file`**  
   Creates or completely replaces a file in the workspace with automatic recursive parent directory creation (`fs.mkdir({ recursive: true })`). Protected by safety validation and approval gate.

4. **`edit_file`** (Incremental Editing Tool)  
   Performs targeted, unambiguous text replacements in existing files:
   - Replaces target text blocks without rewriting unrelated file contents.
   - Enforces unique matching (rejects missing or ambiguous matches without modifying the file).
   - Preserves surrounding indentation, unrelated lines, and line-ending styles (`\r\n` vs `\n`).
   - Prevents modifications to protected secret/session files (`.env`, `.gemini_sessions.json`).
   - Also accepts tool alias `replace_block`.

5. **`run_command`**  
   Executes cross-platform shell commands (`bash` on Linux/macOS, `cmd.exe` on Windows) with strict command blacklisting and chained-command syntax defense.

6. **`run_executable`**  
   Executes explicitly whitelisted executables (e.g., Python virtual environment binaries or system `python3`) using direct `child_process.execFile` argument arrays.

7. **`search_code`**  
   Searches the codebase for literal strings or regular expressions:
   - Recursively traverses directories with automatic early-exit when reaching the 100-match cap.
   - Skips excluded directories (`.git`, `node_modules`, `dist`, `build`, `__pycache__`, `.venv`, `venv`).
   - Skips binary file extensions (`.png`, `.jpg`, `.pdf`, `.zip`, `.exe`, etc.).

8. **`search_web`**  
   Searches the web for up-to-date documentation, API changes, and solutions to cryptic runtime errors with automatic redirect following and DuckDuckGo Lite fallback.

9. **`git_status`**  
   Inspects working tree status and uncommitted modified/untracked files.

10. **`git_diff`**  
   Inspects granular line-by-line diffs of uncommitted changes (both staged and unstaged).

---

## Security Model & Sandboxing

The agent implements four layers of local development security:

1. **Workspace Boundary Isolation (`resolveWorkspacePath`):**  
   Resolves all paths against the project root and throws an access denied error on path traversal attempts (`../`) or absolute path escapes.

2. **Protected Secret & Session Files (`isProtectedFile`):**  
   Blocks `write_file` and `edit_file` from touching:
   - Environment and credential files: `.env`, `.env.*`
   - Session data stores: `.gemini_sessions.json`, `.gemini_sessions*.json`

3. **Command Blacklist & Obfuscation Filter (`isDangerousCommand`):**  
   Blocks destructive commands across Windows and POSIX:
   - File deletion and directory removal: `del`, `rmdir`, `rd`, `erase`, `rm -rf /`, `rm -fr /*`
   - Disk operations: `format`, `diskpart`, `mkfs`, `dd if=/dev/...`
   - System disruption: `shutdown`, `taskkill`, `reboot`, `poweroff`, fork bombs (`:(){ :|:& };:`)
   - Registry & permission modification: `reg delete`, `reg add`, `chmod -R 777 /`
   - Shell obfuscation attacks: Caret-escaped tokens (`^d^e^l`), executable extensions (`format.com`, `shutdown.exe`), and absolute path invocations (`C:\Windows\System32\del`).

4. **Authorized Python Discovery (`discoverPythonInterpreter`):**  
   Dynamically identifies authorized Python interpreters via:
   - `PYTHON_PATH` environment variable
   - `VIRTUAL_ENV` active environment
   - Subproject virtual environments (`Daily-Market-Regime-Engine/.venv`, `venv`)
   - Workspace virtual environments (`.venv`, `venv`)
   - System Python fallbacks (`python3`, `python`)

---

## Prerequisites & Configuration

### Prerequisites
- **Node.js:** v18.0.0 or higher
- **npm:** v9.0.0 or higher
- **Python (Optional):** Authorized virtual environment interpreter for Python script tasks

### Environment Variables
Configure the following variable in a local `.env` file in the project root:

```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

> **Security Note:** Never commit `.env` or print secret values in logs. `.env` is excluded by `.gitignore`.

---

## Installation & Startup

1. **Clone / Navigate to Project:**
   ```bash
   cd C:\projects\gemini-agent
   ```

2. **Install Dependencies:**
   ```bash
   npm install
   ```

3. **Launch the Agent:**
   - **Interactive Mode:**
     ```bash
     node index.js
     ```
   - **Autonomous Mode (Auto-Approve):**
     ```bash
     node index.js --auto
     # or: node index.js -y
     # or: export AUTO_APPROVE=1 && node index.js
     ```
     *In Autonomous Mode, file modifications and safe commands proceed automatically without stopping for interactive prompts.*

### CLI Session Commands
While running in interactive mode, you can enter tasks or use the following commands:
- `sessions`: Lists all saved sessions stored in `.gemini_sessions.json`.
- `resume <session_id>`: Resumes context from an earlier conversation interaction ID.
- `exit` or `quit`: Exits the agent session.

---

## Test Execution

The project provides comprehensive unit and capability test suites.

### Run Comprehensive Test Suite
```bash
npm test
```
*Executes the full cross-platform and capability suite (`cross_platform.test.js`), verifying:*
1. Dangerous command defense (Windows & POSIX)
2. Cross-platform shell command execution
3. Protected secret/session file shielding
4. Git status & diff introspection
5. Incremental block editing
6. Parent directory auto-creation on file write
7. Subdirectory and recursive file listing
8. Paginated line-range file reading
9. Python interpreter discovery resilience

### Run Calculator Unit Test
```bash
npm run test:calculator
```

---

## Workspace Classification & File Inventory

The workspace currently contains core agent files, test suites, historical milestones, and co-located external practice scripts. All files are documented below and preserved intact:

| Component Group | Files | Description |
| :--- | :--- | :--- |
| **Agent Core & Config** | `index.js`, `package.json`, `package-lock.json`, `.gitignore`, `README.md` | Primary application runtime, dependency configurations, and documentation. |
| **Verified Test Suites** | `cross_platform.test.js`, `phase_a.test.js`, `phase_b.test.js`, `search_code.test.js`, `edit_file.test.js`, `calculator.test.js`, `broken.test.js`, `repair-demo.test.js`, `auth_test.js` | Official automated regression test suites verifying agent capabilities. |
| **Agent Test Fixtures** | `calculator.js`, `broken.js`, `repair-demo.js`, `math.js`, `app.js` | Fixture modules used by the agent during self-repair and tool verification loops. |
| **Documentation & Reference** | `GEMINI_AGENT_AUDIT.md`, `phase_b_sdk_types.txt` | Complete technical audit report and GenAI SDK interaction typing reference. |
| **Historical Snapshots** | `index-backup.js`, `index-step20.js`, `test.txt` | Milestone backups and test text outputs preserved for historical reference. |
| **Exploratory & Diagnostics** | `agent_test.js`, `check_*.js`, `proposal_*.js`, `test_cmd_*.js`, `test_spawn_*.js`, `verify_*.js`, etc. (22 scripts) | Experimental shell, spawn, and path exploration scripts developed during earlier milestones. |
| **External Practice Scripts** | `bearish_regime.js`, `nifty_regime.js`, `run_all_mtf_verification.js`, `test_mtf_*.py`, etc. (35 scripts) | Co-located practice scripts for the Daily-Market-Regime-Engine project, preserved in their current untracked state. |
