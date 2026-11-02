// Safe environment loader (tries dotenv, falls back to zero-dependency native parser)
try {
  require("dotenv").config();
} catch (_) {
  // Built-in .env parser fallback
  const fsSync = require("fs");
  const envPath = require("path").resolve(process.cwd(), ".env");
  if (fsSync.existsSync(envPath)) {
    try {
      const lines = fsSync.readFileSync(envPath, "utf8").split(/\r?\n/);
      for (const line of lines) {
        const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
        if (match && !process.env[match[1]]) {
          let val = (match[2] || "").trim();
          if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
            val = val.slice(1, -1);
          }
          process.env[match[1]] = val;
        }
      }
    } catch (_) {}
  }
}

let GoogleGenAI;
try {
  ({ GoogleGenAI } = require("@google/genai"));
} catch (_) {
  // GoogleGenAI will be loaded if available or mocked in offline test mode
}

const fs = require("fs/promises");
const fsSync = require("fs");
const path = require("path");
const { execFile } = require("child_process");
const readline = require("readline");

// Autonomous execution flag: enabled via --auto, -y, --yes or AUTO_APPROVE=1
const AUTO_APPROVE =
  process.argv.includes("--auto") ||
  process.argv.includes("-y") ||
  process.argv.includes("--yes") ||
  process.env.AUTO_APPROVE === "true" ||
  process.env.AUTO_APPROVE === "1";

const WORKSPACE = path.resolve(process.cwd());
const SESSION_FILE = path.join(WORKSPACE, ".gemini_sessions.json");
const MODEL = "gemini-3.5-flash-lite";
const MAX_STEPS = 20;
const MAX_REPAIR_ATTEMPTS = 5;

// Lazy GenAI client factory to allow importing functions without requiring immediate API key
function getGenAIClient() {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || !apiKey.trim()) {
    throw new Error("[FATAL ERROR] GEMINI_API_KEY environment variable is missing or empty.");
  }
  if (!GoogleGenAI) {
    ({ GoogleGenAI } = require("@google/genai"));
  }
  return new GoogleGenAI({ apiKey: apiKey.trim() });
}

let ai = null;
try {
  if (process.env.GEMINI_API_KEY) {
    ai = getGenAIClient();
  }
} catch (_) {}

// Helper to check if an error is an authentication error (400 API_KEY_INVALID, 401, 403, or status/message matching auth failures)
function isAuthenticationError(err) {
  if (!err) return false;
  const status = err.status || err.statusCode || (err.response && err.response.status);
  const message = String(err.message || err.toString()).toUpperCase();
  
  if (status === 401 || status === 403) {
    return true;
  }
  if (status === 400 && (message.includes("API_KEY_INVALID") || (message.includes("INVALID_ARGUMENT") && message.includes("API KEY")))) {
    return true;
  }
  if (message.includes("API_KEY_INVALID") || message.includes("API KEY NOT VALID") || message.includes("AUTHENTICATION") || message.includes("UNAUTHENTICATED")) {
    return true;
  }
  return false;
}

// 1. Python Environment Discovery with cross-platform validation
function discoverPythonInterpreter() {
  const isWindows = process.platform === "win32";

  // Check explicit environment variables first
  if (process.env.PYTHON_PATH && fsSync.existsSync(process.env.PYTHON_PATH)) {
    console.log("[SECURITY] Discovered authorized Python interpreter from PYTHON_PATH:", process.env.PYTHON_PATH);
    return path.normalize(process.env.PYTHON_PATH);
  }
  if (process.env.VIRTUAL_ENV) {
    const venvPython = isWindows
      ? path.join(process.env.VIRTUAL_ENV, "Scripts", "python.exe")
      : path.join(process.env.VIRTUAL_ENV, "bin", "python");
    if (fsSync.existsSync(venvPython)) {
      console.log("[SECURITY] Discovered authorized Python interpreter from VIRTUAL_ENV:", venvPython);
      return path.normalize(venvPython);
    }
  }

  const candidates = [
    // Sub-repository virtual environments
    path.join(WORKSPACE, "Daily-Market-Regime-Engine", ".venv", isWindows ? "Scripts/python.exe" : "bin/python"),
    path.join(WORKSPACE, "Daily-Market-Regime-Engine", "venv", isWindows ? "Scripts/python.exe" : "bin/python"),
    // Workspace virtual environments
    path.join(WORKSPACE, ".venv", isWindows ? "Scripts/python.exe" : "bin/python"),
    path.join(WORKSPACE, "venv", isWindows ? "Scripts/python.exe" : "bin/python"),
    // Standard Unix / container paths
    "/root/.venv/bin/python",
    "/usr/bin/python3",
    "/usr/local/bin/python3",
  ];

  for (const candidate of candidates) {
    const normalized = path.normalize(candidate);
    if (fsSync.existsSync(normalized)) {
      console.log("[SECURITY] Discovered authorized Python interpreter:", normalized);
      return normalized;
    }
  }

  // Fallback to checking system python
  try {
    const { execSync } = require("child_process");
    const checkCmd = isWindows ? "where python" : "which python3 || which python";
    const out = execSync(checkCmd, { encoding: "utf8", windowsHide: true }).trim().split(/\r?\n/)[0];
    if (out && fsSync.existsSync(out)) {
      console.log("[SECURITY] Discovered system Python interpreter:", out);
      return path.normalize(out);
    }
  } catch (_) {}

  console.warn("[SECURITY WARNING] No authorized Python virtual environment interpreter found in standard paths!");
  return null;
}

const ALLOWED_PYTHON = discoverPythonInterpreter();

const tools = [
  {
    type: "function",
    name: "list_files",
    description: "List files and directories in the project workspace or a specific subdirectory.",
    parameters: {
      type: "object",
      properties: {
        path: {
          type: "string",
          description: "Subdirectory path to list (relative to workspace). Defaults to root.",
        },
        recursive: {
          type: "boolean",
          description: "Whether to list directory contents recursively (default false).",
        },
      },
    },
  },
  {
    type: "function",
    name: "read_file",
    description: "Read a text file inside the project workspace with optional line range pagination.",
    parameters: {
      type: "object",
      properties: {
        filePath: { type: "string", description: "Path to file to read (relative to workspace)." },
        startLine: { type: "integer", description: "Optional starting line number (1-based, inclusive)." },
        endLine: { type: "integer", description: "Optional ending line number (1-based, inclusive)." },
      },
      required: ["filePath"],
    },
  },
  {
    type: "function",
    name: "write_file",
    description: "Create or replace a text file inside the project workspace (requires user approval or autonomous mode).",
    parameters: {
      type: "object",
      properties: {
        filePath: { type: "string" },
        content: { type: "string" },
      },
      required: ["filePath", "content"],
    },
  },
  {
    type: "function",
    name: "edit_file",
    description: "Incrementally edit an existing text file by replacing an unambiguous target text block with replacement text (requires user approval or autonomous mode).",
    parameters: {
      type: "object",
      properties: {
        filePath: { type: "string", description: "Path to the file to edit (relative to workspace)." },
        target: { type: "string", description: "The exact target text to replace. Must match exactly once in the file." },
        replacement: { type: "string", description: "The replacement text." },
      },
      required: ["filePath", "target", "replacement"],
    },
  },
  {
    type: "function",
    name: "run_command",
    description: "Run a cross-platform development shell command in the project workspace (requires user approval or autonomous mode).",
    parameters: {
      type: "object",
      properties: {
        command: { type: "string" },
      },
      required: ["command"],
    },
  },
  {
    type: "function",
    name: "run_executable",
    description: "Run an explicit authorized Python executable with an argument array.",
    parameters: {
      type: "object",
      properties: {
        file: { type: "string" },
        args: {
          type: "array",
          items: { type: "string" },
        },
      },
      required: ["file", "args"],
    },
  },
  {
    type: "function",
    name: "search_code",
    description: "Search for literal text or regex pattern across workspace files, skipping excluded directories like .git and node_modules.",
    parameters: {
      type: "object",
      properties: {
        query: { type: "string", description: "Text or regex pattern to search for." },
        isRegex: { type: "boolean", description: "Whether query is a regular expression (default false)." },
      },
      required: ["query"],
    },
  },
  {
    type: "function",
    name: "search_web",
    description: "Search the web for up-to-date documentation, API specs, error solutions, and library usage.",
    parameters: {
      type: "object",
      properties: {
        query: { type: "string", description: "Web search query." },
      },
      required: ["query"],
    },
  },
  {
    type: "function",
    name: "git_status",
    description: "Get current git status and changed files in the workspace.",
    parameters: {
      type: "object",
      properties: {},
    },
  },
  {
    type: "function",
    name: "git_diff",
    description: "Get git diff of uncommitted changes.",
    parameters: {
      type: "object",
      properties: {
        cached: { type: "boolean", description: "Whether to view staged changes (default false)." },
      },
    },
  },
];

function isProtectedFile(filePath, rootDir = WORKSPACE) {
  if (typeof filePath !== "string" || !filePath.trim()) return false;
  const fullPath = path.resolve(rootDir, filePath);
  const relativePath = path.relative(rootDir, fullPath).replace(/\\/g, "/");
  const baseName = path.basename(fullPath).toLowerCase();

  return (
    baseName === ".env" ||
    baseName.startsWith(".env.") ||
    baseName === ".gemini_sessions.json" ||
    baseName.startsWith(".gemini_sessions") ||
    relativePath === ".env" ||
    relativePath.startsWith(".env.") ||
    relativePath === ".gemini_sessions.json" ||
    relativePath.startsWith(".gemini_sessions")
  );
}

function resolveWorkspacePath(filePath, rootDir = WORKSPACE) {
  if (typeof filePath !== "string" || !filePath.trim()) {
    throw new Error("Invalid file path.");
  }

  const fullPath = path.resolve(rootDir, filePath);
  const relativePath = path.relative(rootDir, fullPath);

  if (
    relativePath.startsWith("..") ||
    path.isAbsolute(relativePath)
  ) {
    throw new Error(
      `Access denied: path is outside workspace: ${filePath}`
    );
  }

  return fullPath;
}

async function listFiles(targetSubPath = "", recursive = false) {
  const targetDir = targetSubPath ? resolveWorkspacePath(targetSubPath) : WORKSPACE;

  let stats;
  try {
    stats = await fs.stat(targetDir);
  } catch (err) {
    if (err.code === "ENOENT") {
      throw new Error(`Directory not found: ${targetSubPath}`);
    }
    throw err;
  }

  if (!stats.isDirectory()) {
    throw new Error(`Path is not a directory: ${targetSubPath}`);
  }

  const excludedDirs = new Set([".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"]);

  if (recursive) {
    const results = [];
    async function walk(currentDir) {
      if (results.length >= 500) return;
      let entries;
      try {
        entries = await fs.readdir(currentDir, { withFileTypes: true });
      } catch (_) {
        return;
      }
      for (const entry of entries) {
        if (results.length >= 500) break;
        const full = path.join(currentDir, entry.name);
        const rel = path.relative(targetDir, full).replace(/\\/g, "/");
        if (entry.isDirectory()) {
          if (!excludedDirs.has(entry.name)) {
            results.push(`${rel}/`);
            await walk(full);
          }
        } else {
          results.push(rel);
        }
      }
    }
    await walk(targetDir);
    return results.join("\n") || "(empty directory)";
  }

  const entries = await fs.readdir(targetDir, {
    withFileTypes: true,
  });

  if (entries.length === 0) {
    return "(empty directory)";
  }

  return entries
    .map((entry) =>
      entry.isDirectory() ? `${entry.name}/` : entry.name
    )
    .join("\n");
}

async function readFile(filePath, startLine = null, endLine = null) {
  const fullPath = resolveWorkspacePath(filePath);
  console.log("Reading:", fullPath);
  const content = await fs.readFile(fullPath, "utf8");

  if (startLine !== null && startLine !== undefined && !isNaN(startLine)) {
    const lines = content.split(/\r?\n/);
    const totalLines = lines.length;
    const start = Math.max(1, parseInt(startLine, 10));
    const end = (endLine !== null && endLine !== undefined && !isNaN(endLine))
      ? Math.min(totalLines, Math.max(start, parseInt(endLine, 10)))
      : totalLines;

    const selectedLines = lines.slice(start - 1, end);
    const numbered = selectedLines.map((line, idx) => `${start + idx}: ${line}`).join("\n");
    const rel = path.relative(WORKSPACE, fullPath).replace(/\\/g, "/");
    return `[Viewing lines ${start}-${end} of ${totalLines} in ${rel}]\n${numbered}`;
  }

  return content;
}

async function writeFile(filePath, content, rootDir = WORKSPACE) {
  if (isProtectedFile(filePath, rootDir)) {
    throw new Error(`Access denied: writing to protected file is forbidden: ${filePath}`);
  }
  const fullPath = resolveWorkspacePath(filePath, rootDir);
  console.log("Writing:", fullPath);
  await fs.mkdir(path.dirname(fullPath), { recursive: true });
  await fs.writeFile(fullPath, content, "utf8");
  return `Successfully wrote ${fullPath}`;
}

async function editFile(filePath, target, replacement, rootDir = WORKSPACE) {
  if (typeof filePath !== "string" || !filePath.trim()) {
    throw new Error("Invalid file path: path cannot be empty.");
  }

  if (isProtectedFile(filePath, rootDir)) {
    throw new Error(`Access denied: editing protected file is forbidden: ${filePath}`);
  }

  const fullPath = resolveWorkspacePath(filePath, rootDir);

  if (target === undefined || target === null || typeof target !== "string" || target.length === 0) {
    throw new Error("Target text cannot be empty.");
  }

  if (replacement === undefined || replacement === null || typeof replacement !== "string") {
    throw new Error("Replacement text must be a string.");
  }

  let stats;
  try {
    stats = await fs.stat(fullPath);
  } catch (err) {
    if (err.code === "ENOENT") {
      throw new Error(`File not found: ${filePath}`);
    }
    throw err;
  }

  if (stats.isDirectory()) {
    throw new Error(`Cannot edit directory: ${filePath}`);
  }

  const content = await fs.readFile(fullPath, "utf8");

  let effectiveTarget = target;
  let firstIndex = content.indexOf(effectiveTarget);

  if (firstIndex === -1) {
    if (content.includes("\r\n") && !target.includes("\r\n") && target.includes("\n")) {
      const crlfTarget = target.replace(/\n/g, "\r\n");
      if (content.includes(crlfTarget)) {
        effectiveTarget = crlfTarget;
        firstIndex = content.indexOf(effectiveTarget);
      }
    } else if (!content.includes("\r\n") && target.includes("\r\n")) {
      const lfTarget = target.replace(/\r\n/g, "\n");
      if (content.includes(lfTarget)) {
        effectiveTarget = lfTarget;
        firstIndex = content.indexOf(effectiveTarget);
      }
    }
  }

  if (firstIndex === -1) {
    throw new Error(`Target text not found in ${filePath}.`);
  }

  const secondIndex = content.indexOf(effectiveTarget, firstIndex + 1);
  if (secondIndex !== -1) {
    let count = 2;
    let pos = secondIndex + 1;
    while ((pos = content.indexOf(effectiveTarget, pos)) !== -1) {
      count++;
      pos++;
    }
    throw new Error(`Ambiguous target text: found ${count} matches in ${filePath}. Target text must match exactly once.`);
  }

  const newContent = content.slice(0, firstIndex) + replacement + content.slice(firstIndex + effectiveTarget.length);
  await fs.writeFile(fullPath, newContent, "utf8");
  return `Successfully replaced target text in ${filePath}.`;
}

// 2. Robust Non-Interactive Approval Gate with Stdin Check, Timeout, and Autonomous Mode
function askApproval(questionText) {
  return new Promise((resolve) => {
    if (AUTO_APPROVE || process.env.AUTO_APPROVE === "true" || process.env.AUTO_APPROVE === "1") {
      console.log(`[SECURITY APPROVAL GATE] Auto-approved (Autonomous Mode): ${questionText.trim()}`);
      resolve(true);
      return;
    }

    if (!process.stdin.isTTY) {
      console.warn("[SECURITY] Non-interactive execution detected (stdin is not a TTY). Defaulting approval to DENY.");
      resolve(false);
      return;
    }

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    let answered = false;

    const timer = setTimeout(() => {
      if (!answered) {
        answered = true;
        rl.close();
        console.warn("\n[SECURITY] Approval prompt timed out after 30s. Defaulting to DENY.");
        resolve(false);
      }
    }, 30000);

    rl.on("close", () => {
      if (!answered) {
        answered = true;
        clearTimeout(timer);
        resolve(false);
      }
    });

    rl.question(questionText, (answer) => {
      if (!answered) {
        answered = true;
        clearTimeout(timer);
        rl.close();
        const val = answer ? answer.trim().toLowerCase() : "";
        resolve(val === "y" || val === "yes");
      }
    });
  });
}

function splitChainedCommands(command) {
  if (typeof command !== "string") return null;

  const segments = [];
  let current = "";
  let inQuote = null;

  for (let i = 0; i < command.length; i++) {
    const char = command[i];

    // Handle caret escape outside of quotes in cmd.exe
    if (!inQuote && char === "^") {
      current += char;
      i++;
      if (i < command.length) {
        current += command[i];
      }
      continue;
    }

    if (inQuote) {
      // Escaped quote handling inside quotes:
      // 1. Backslash-escaped quote: \" or \'
      if (char === "\\" && i + 1 < command.length && command[i + 1] === inQuote) {
        current += "\\" + inQuote;
        i++;
        continue;
      }
      // 2. Cmd-style doubled quote: "" inside double quotes
      if (inQuote === '"' && char === '"' && i + 1 < command.length && command[i + 1] === '"') {
        current += '""';
        i++;
        continue;
      }
      // 3. Caret-escaped quote: ^"
      if (char === "^" && i + 1 < command.length && command[i + 1] === inQuote) {
        current += "^" + inQuote;
        i++;
        continue;
      }

      if (char === inQuote) {
        inQuote = null;
      }
      current += char;
      continue;
    }

    if (char === '"' || char === "'") {
      inQuote = char;
      current += char;
      continue;
    }

    // Windows & shell chaining operators: &&, ||, &, |, ;
    if (char === "&" || char === "|") {
      if (i + 1 < command.length && command[i + 1] === char) {
        segments.push(current);
        current = "";
        i++;
        continue;
      }
      segments.push(current);
      current = "";
      continue;
    }

    if (char === ";") {
      segments.push(current);
      current = "";
      continue;
    }

    current += char;
  }

  // If a quote remains unclosed, syntax cannot be checked reliably -> fail safely
  if (inQuote !== null) {
    return null;
  }

  segments.push(current);
  return segments;
}

function isDangerousCommand(command) {
  if (typeof command !== "string" || !command.trim()) {
    return false;
  }

  const raw = command.trim();

  // POSIX destructive command patterns checked across full command string:
  // 1. Fork bomb: :(){ :|:& };:
  if (raw.includes(":(){ :|:& };:") || raw.includes(":(){:|:&};:") || raw.includes(":(){ :|:& };")) {
    return true;
  }
  // 2. Recursive root/home deletion: rm -rf /, rm -fr /, rm -rf /*
  if (
    /\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+(\/|\/\*|~\/?|\$HOME)(\s|$|;|&|\|)/i.test(raw) ||
    /\brm\s+--recursive\s+--force\s+(\/|\/\*|~\/?|\$HOME)(\s|$|;|&|\|)/i.test(raw)
  ) {
    return true;
  }
  // 3. Direct block device overwrites: dd if=..., > /dev/sd..., > /dev/nvme...
  if (
    /\bdd\s+if=/i.test(raw) ||
    />\s*\/dev\/(sd[a-z]|nvme|hd[a-z]|null\s*;|zero)/i.test(raw)
  ) {
    return true;
  }
  // 4. Recursive root permission wipe: chmod -R 777 /
  if (/\bchmod\s+(-[a-zA-Z]*R[a-zA-Z]*\s+)?(777|000)\s+(\/|\/\*)(\s|$)/i.test(raw)) {
    return true;
  }

  const segments = splitChainedCommands(command);
  if (segments === null) {
    // Unclosed quote or unparseable command syntax - fail safe
    return true;
  }

  const blockedNames = new Set([
    // Windows blocked commands
    "del",
    "erase",
    "rmdir",
    "rd",
    "format",
    "shutdown",
    "restart-computer",
    "stop-computer",
    "taskkill",
    "diskpart",
    "bcdedit",
    "takeown",
    "icacls",
    // POSIX blocked commands
    "reboot",
    "poweroff",
    "mkfs",
  ]);

  for (const rawSegment of segments) {
    const segment = rawSegment.trim();
    if (!segment) continue;

    // POSIX destructive command patterns:
    if (
      /\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+(\/|\/\*|~\/?|\$HOME)(\s|$|;|&|\|)/i.test(segment) ||
      /\brm\s+--recursive\s+--force\s+(\/|\/\*|~\/?|\$HOME)(\s|$|;|&|\|)/i.test(segment)
    ) {
      return true;
    }
    if (
      /\bdd\s+if=/i.test(segment) ||
      />\s*\/dev\/(sd[a-z]|nvme|hd[a-z]|null\s*;|zero)/i.test(segment)
    ) {
      return true;
    }
    if (segment.includes(":(){ :|:& };:") || segment.includes(":(){ :|:& };")) {
      return true;
    }
    if (/\bchmod\s+(-[a-zA-Z]*R[a-zA-Z]*\s+)?(777|000)\s+(\/|\/\*)(\s|$)/i.test(segment)) {
      return true;
    }

    // Strip leading parentheses or group wrappers: e.g. ((del foo))
    let clean = segment.replace(/^[\s()]+/, "");

    // Strip carets (cmd.exe escape character)
    clean = clean.replace(/\^/g, "");

    let targetExe = "";
    if (clean.startsWith('"') || clean.startsWith("'")) {
      const q = clean[0];
      const endQ = clean.indexOf(q, 1);
      if (endQ !== -1) {
        targetExe = clean.substring(1, endQ).trim();
      }
    }

    if (!targetExe) {
      targetExe = clean.split(/\s+/)[0];
    }

    const lower = clean.toLowerCase();

    // Check compound commands first: reg delete, reg add
    if (
      lower === "reg delete" ||
      lower.startsWith("reg delete ") ||
      lower.startsWith("reg delete/") ||
      lower.startsWith("reg delete\\") ||
      lower === "reg add" ||
      lower.startsWith("reg add ") ||
      lower.startsWith("reg add/") ||
      lower.startsWith("reg add\\")
    ) {
      return true;
    }

    // Check targetExe against blocked names
    const slashTokens = targetExe.split("/");
    for (const token of [targetExe, slashTokens[0], slashTokens[slashTokens.length - 1]]) {
      const baseWithExt = token.split(/[\\]/).pop().toLowerCase();
      const baseName = baseWithExt.replace(/\.(exe|com|bat|cmd)$/i, "");
      if (blockedNames.has(baseName) || baseWithExt.startsWith("mkfs")) {
        return true;
      }
    }

    if (lower.startsWith("mkfs")) {
      return true;
    }

    for (const name of blockedNames) {
      if (
        lower === name ||
        lower.startsWith(name + " ") ||
        lower.startsWith(name + "/") ||
        lower.startsWith(name + "\\")
      ) {
        return true;
      }
    }
  }

  return false;
}

function runCommand(command) {
  return new Promise((resolve) => {
    console.log("Running:", command);

    const isWindows = process.platform === "win32";
    const shellExe = isWindows ? "cmd.exe" : (fsSync.existsSync("/bin/bash") ? "/bin/bash" : "/bin/sh");
    const shellArgs = isWindows ? ["/d", "/s", "/c", `"${command}"`] : ["-c", command];
    const execOptions = {
      cwd: WORKSPACE,
      timeout: 30000,
      maxBuffer: 1024 * 1024,
      windowsHide: isWindows,
    };
    if (isWindows) {
      execOptions.windowsVerbatimArguments = true;
    }

    execFile(
      shellExe,
      shellArgs,
      execOptions,
      (error, stdout, stderr) => {
        const output = [];

        if (stdout) {
          output.push(`STDOUT:\n${stdout}`);
        }

        if (stderr) {
          output.push(`STDERR:\n${stderr}`);
        }

        if (error) {
          const exitCode =
            typeof error.code === "number"
              ? error.code
              : null;

          if (exitCode !== null) {
            output.push(`EXIT CODE: ${exitCode}`);
          } else {
            output.push(
              `COMMAND ERROR: ${error.message}`
            );
          }

          resolve({
            success: false,
            exitCode,
            output: output.join("\n"),
          });

          return;
        }

        resolve({
          success: true,
          exitCode: 0,
          output:
            output.length > 0
              ? output.join("\n")
              : "Command completed successfully.",
        });
      }
    );
  });
}

function runExecutable(file, args = []) {
  return new Promise((resolve) => {
    if (!ALLOWED_PYTHON) {
      resolve({
        success: false,
        exitCode: null,
        output: "No authorized Python interpreter is available in this environment.",
      });
      return;
    }

    const resolvedFile = path.resolve(WORKSPACE, file);
    const normalizedFile = path.normalize(resolvedFile);

    if (normalizedFile.toLowerCase() !== ALLOWED_PYTHON.toLowerCase()) {
      console.error("[SECURITY] Rejected unauthorized executable:", normalizedFile);
      resolve({
        success: false,
        exitCode: null,
        output: `Executable not authorized: ${file}. Expected authorized interpreter: ${ALLOWED_PYTHON}`,
      });
      return;
    }

    console.log("Running executable:", normalizedFile, args);

    execFile(
      normalizedFile,
      args,
      {
        cwd: WORKSPACE,
        timeout: 30000,
        maxBuffer: 1024 * 1024,
        windowsHide: true,
      },
      (error, stdout, stderr) => {
        const output = [];

        if (stdout) {
          output.push(`STDOUT:\n${stdout}`);
        }

        if (stderr) {
          output.push(`STDERR:\n${stderr}`);
        }

        if (error) {
          const exitCode =
            typeof error.code === "number"
              ? error.code
              : null;

          if (exitCode !== null) {
            output.push(`EXIT CODE: ${exitCode}`);
          } else {
            output.push(
              `EXECUTABLE ERROR: ${error.message}`
            );
          }

          resolve({
            success: false,
            exitCode,
            output: output.join("\n"),
          });

          return;
        }

        resolve({
          success: true,
          exitCode: 0,
          output:
            output.length > 0
              ? output.join("\n")
              : "Executable completed successfully.",
        });
      }
    );
  });
}

// 3. Code Search Tool (`search_code`) with robust exclusion & error handling
async function searchCode(query, isRegex = false, rootDir = WORKSPACE) {
  if (!query || typeof query !== "string") {
    return "Search query cannot be empty.";
  }

  const excludedDirs = new Set([
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv"
  ]);

  const maxFileSize = 1024 * 1024; // 1MB limit per file
  const results = [];
  let regex = null;

  if (isRegex) {
    try {
      regex = new RegExp(query, "g");
    } catch (e) {
      return `Invalid regular expression: ${e.message}`;
    }
  }

  async function walk(dir) {
    if (results.length >= 100) return;

    let entries;
    try {
      entries = await fs.readdir(dir, { withFileTypes: true });
    } catch (err) {
      return;
    }

    for (const entry of entries) {
      if (results.length >= 100) break;

      const resPath = path.join(dir, entry.name);
      const relPath = path.relative(rootDir, resPath);

      if (entry.isDirectory()) {
        if (excludedDirs.has(entry.name)) {
          continue;
        }
        await walk(resPath);
        if (results.length >= 100) return;
      } else if (entry.isFile()) {
        try {
          const stats = await fs.stat(resPath);
          if (stats.size > maxFileSize) {
            continue;
          }

          const ext = path.extname(entry.name).toLowerCase();
          const binaryExts = [".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".exe", ".bin", ".pyc"];
          if (binaryExts.includes(ext)) {
            continue;
          }

          const content = await fs.readFile(resPath, "utf8");
          const lines = content.split(/\r?\n/);

          for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            let matched = false;
            if (isRegex) {
              regex.lastIndex = 0;
              matched = regex.test(line);
            } else {
              matched = line.includes(query);
            }

            if (matched) {
              results.push(`${relPath}:${i + 1}: ${line.trim()}`);
              if (results.length >= 100) {
                return;
              }
            }
          }
        } catch (err) {
          // Skip unreadable files
        }
      }
    }
  }

  await walk(rootDir);

  if (results.length === 0) {
    return `No matches found for query: "${query}"`;
  }

  return results.join("\n");
}

// 5. Web Search Tool (`search_web`) with redirect handling and lite fallback
function searchWeb(query) {
  return new Promise((resolve) => {
    if (!query || typeof query !== "string") {
      resolve("Search query cannot be empty.");
      return;
    }
    const https = require("https");
    const encoded = encodeURIComponent(query);

    function fetchUrl(targetUrl, depth = 0) {
      if (depth > 3) {
        resolve("Web search error: Too many redirects.");
        return;
      }

      const req = https.get(
        targetUrl,
        {
          headers: {
            "User-Agent":
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
          },
          timeout: 10000,
        },
        (res) => {
          if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
            const nextUrl = res.headers.location.startsWith("http")
              ? res.headers.location
              : `https://html.duckduckgo.com${res.headers.location}`;
            fetchUrl(nextUrl, depth + 1);
            return;
          }

          let body = "";
          res.on("data", (chunk) => {
            if (body.length < 100000) body += chunk;
          });
          res.on("end", () => {
            const results = [];
            const snippetRegex = /<a class="result__snippet[^>]*>([\s\S]*?)<\/a>/gi;
            let m;
            while ((m = snippetRegex.exec(body)) !== null && results.length < 5) {
              const clean = m[1]
                .replace(/<[^>]+>/g, "")
                .replace(/&quot;/g, '"')
                .replace(/&amp;/g, "&")
                .replace(/&#x27;/g, "'")
                .trim();
              if (clean) results.push(clean);
            }

            // Fallback parsing for DuckDuckGo Lite snippet structure
            if (results.length === 0) {
              const liteRegex = /<td class="result-snippet">([\s\S]*?)<\/td>/gi;
              while ((m = liteRegex.exec(body)) !== null && results.length < 5) {
                const clean = m[1]
                  .replace(/<[^>]+>/g, "")
                  .replace(/&quot;/g, '"')
                  .replace(/&amp;/g, "&")
                  .replace(/&#x27;/g, "'")
                  .trim();
                if (clean) results.push(clean);
              }
            }

            if (results.length > 0) {
              resolve(results.map((r, i) => `[Result ${i + 1}] ${r}`).join("\n\n"));
            } else if (targetUrl.includes("html.duckduckgo.com")) {
              // Try lite interface fallback
              fetchUrl(`https://lite.duckduckgo.com/lite/?q=${encoded}`, depth + 1);
            } else {
              resolve(`Search completed for "${query}". No direct text snippets returned.`);
            }
          });
        }
      );
      req.on("error", (err) => resolve(`Web search error: ${err.message}`));
      req.on("timeout", () => {
        req.destroy();
        resolve("Web search request timed out.");
      });
    }

    fetchUrl(`https://html.duckduckgo.com/html/?q=${encoded}`);
  });
}

// 6. Git Status and Git Diff Tools
function getGitStatus() {
  return new Promise((resolve) => {
    execFile("git", ["status", "--short"], { cwd: WORKSPACE, timeout: 10000 }, (err, stdout, stderr) => {
      if (err) {
        resolve(`Git status error: ${stderr || err.message}`);
      } else {
        resolve(stdout.trim() || "Working tree is clean.");
      }
    });
  });
}

function getGitDiff(cached = false) {
  return new Promise((resolve) => {
    const args = ["diff"];
    if (cached) args.push("--cached");
    execFile("git", args, { cwd: WORKSPACE, timeout: 10000 }, (err, stdout, stderr) => {
      if (err) {
        resolve(`Git diff error: ${stderr || err.message}`);
      } else {
        resolve(stdout.trim() || "No git diff found (working tree clean).");
      }
    });
  });
}

// 4. Session Persistence Management with Validation & Corruption Handling
async function loadSessions() {
  try {
    if (fsSync.existsSync(SESSION_FILE)) {
      const data = await fs.readFile(SESSION_FILE, "utf8");
      const parsed = JSON.parse(data);
      if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
        const validSessions = {};
        for (const [id, record] of Object.entries(parsed)) {
          if (record && typeof record === "object" && typeof record.sessionId === "string") {
            validSessions[id] = record;
          }
        }
        return validSessions;
      }
    }
  } catch (err) {
    console.error("[WARNING] Could not load or parse sessions file (corrupted or malformed JSON):", err.message);
  }
  return {};
}

async function saveSession(sessionId, title = "Session") {
  try {
    const cleanTitle = String(title).replace(/api_key|password|secret/gi, "[REDACTED]");
    const sessions = await loadSessions();
    sessions[sessionId] = {
      sessionId,
      title: cleanTitle,
      updatedAt: new Date().toISOString(),
    };
    await fs.writeFile(SESSION_FILE, JSON.stringify(sessions, null, 2), "utf8");
  } catch (err) {
    console.error("[WARNING] Could not save session:", err.message);
  }
}

async function executeTool(functionCall) {
  const args = functionCall.arguments || {};

  console.log("\n================================================");
  console.log("TOOL:", functionCall.name);
  console.log("ARGUMENTS:", args);
  console.log("================================================");

  try {
    if (functionCall.name === "list_files") {
      const targetSubPath = args.path || args.subPath || args.directoryPath || "";
      const recursive = Boolean(args.recursive);
      return {
        success: true,
        result: await listFiles(targetSubPath, recursive),
      };
    }

    if (functionCall.name === "read_file") {
      return {
        success: true,
        result: await readFile(args.filePath, args.startLine, args.endLine),
      };
    }

    if (functionCall.name === "write_file") {
      console.log(`\n[SECURITY APPROVAL GATE] Agent requested to write/modify file: ${args.filePath}`);
      const approved = await askApproval(`Allow writing to ${args.filePath}? (y/N): `);

      if (!approved) {
        console.log("[SECURITY] User rejected write_file request.");
        return {
          success: false,
          blocked: true,
          result: `Write operation rejected by user approval gate for file: ${args.filePath}`,
        };
      }

      return {
        success: true,
        result: await writeFile(
          args.filePath,
          args.content
        ),
      };
    }

    if (functionCall.name === "edit_file" || functionCall.name === "replace_block") {
      const targetPath = args.filePath || args.path || args.file;
      const target = args.target !== undefined ? args.target : (args.targetText !== undefined ? args.targetText : args.oldText);
      const replacement = args.replacement !== undefined ? args.replacement : (args.replacementText !== undefined ? args.replacementText : args.newText);

      console.log(`\n[SECURITY APPROVAL GATE] Agent requested to edit file: ${targetPath}`);
      const approved = await askApproval(`Allow editing ${targetPath}? (y/N): `);

      if (!approved) {
        console.log("[SECURITY] User rejected edit_file request.");
        return {
          success: false,
          blocked: true,
          result: `Edit operation rejected by user approval gate for file: ${targetPath}`,
        };
      }

      return {
        success: true,
        result: await editFile(targetPath, target, replacement),
      };
    }

    if (functionCall.name === "run_command") {
      const command = String(args.command || "").trim();

      if (!command) {
        return {
          success: false,
          result: "Command cannot be empty.",
        };
      }

      if (isDangerousCommand(command)) {
        return {
          success: false,
          blocked: true,
          result: `Command blocked by security blacklist: ${command}`,
        };
      }

      console.log(`\n[SECURITY APPROVAL GATE] Agent requested to run command: ${command}`);
      const approved = await askApproval(`Allow executing shell command: "${command}"? (y/N): `);

      if (!approved) {
        console.log("[SECURITY] User rejected run_command request.");
        return {
          success: false,
          blocked: true,
          result: `Command execution rejected by user approval gate: ${command}`,
        };
      }

      return await runCommand(command);
    }

    if (functionCall.name === "run_executable") {
      const file = String(args.file || "").trim();
      const execArgs = Array.isArray(args.args) ? args.args : [];

      if (!file) {
        return {
          success: false,
          result: "Executable file cannot be empty.",
        };
      }

      return await runExecutable(file, execArgs);
    }

    if (functionCall.name === "search_code") {
      const query = String(args.query || "").trim();
      const isRegex = Boolean(args.isRegex);
      return {
        success: true,
        result: await searchCode(query, isRegex),
      };
    }

    if (functionCall.name === "search_web") {
      const query = String(args.query || "").trim();
      return {
        success: true,
        result: await searchWeb(query),
      };
    }

    if (functionCall.name === "git_status") {
      return {
        success: true,
        result: await getGitStatus(),
      };
    }

    if (functionCall.name === "git_diff") {
      return {
        success: true,
        result: await getGitDiff(Boolean(args.cached)),
      };
    }

    return {
      success: false,
      result: `Unknown tool: ${functionCall.name}`,
    };
  } catch (error) {
    return {
      success: false,
      result: `TOOL ERROR: ${error.message}`,
    };
  }
}

function ask(question) {
  return new Promise((resolve) => {
    if (!process.stdin.isTTY) {
      resolve("");
      return;
    }

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

// Helper to consume a streaming interaction and accumulate state / output text
async function consumeInteractionStream(stream) {
  let interactionId = null;
  let outputText = "";
  let steps = [];

  function addStep(step, index = null) {
    if (!step || typeof step !== "object") return;

    if (step.id) {
      const existingIndex = steps.findIndex(
        existing => existing && existing.id === step.id
      );

      if (existingIndex !== -1) {
        steps[existingIndex] = { ...steps[existingIndex], ...step };
        return;
      }
    }

    if (typeof index === "number" && steps[index]) {
      steps[index] = { ...steps[index], ...step };
      return;
    }

    steps.push(step);
  }

  try {
    for await (const event of stream) {
      if (!event) continue;

      if (event.event_type === "interaction.created" || event.event_type === "interaction.completed") {
        if (event.interaction && event.interaction.id) {
          interactionId = event.interaction.id;
        }
      }

      if (event.event_type === "step.delta" && event.delta) {
        const delta = event.delta;
        if (delta.type === "text" && typeof delta.text === "string") {
          process.stdout.write(delta.text);
          outputText += delta.text;
        } else if (delta.text && typeof delta.text === "string") {
          process.stdout.write(delta.text);
          outputText += delta.text;
        }
      }

      if (event.step) {
        addStep(event.step, event.index);
      }

      if (event.interaction) {
        if (event.interaction.id) interactionId = event.interaction.id;
        if (event.interaction.output_text) {
          outputText = event.interaction.output_text;
        }
        if (Array.isArray(event.interaction.steps)) {
          for (let i = 0; i < event.interaction.steps.length; i++) {
            addStep(event.interaction.steps[i], i);
          }
        }
      }

      if (event.output_text && !outputText) {
        outputText = event.output_text;
      }
      if (Array.isArray(event.steps)) {
        for (let i = 0; i < event.steps.length; i++) {
          addStep(event.steps[i], i);
        }
      }
    }
  } catch (streamError) {
    if (isAuthenticationError(streamError)) {
      console.error("\n[AUTHENTICATION ERROR] Authentication failed during stream iteration.");
      throw streamError;
    }
    throw streamError;
  }

  if (outputText && !outputText.endsWith("\n")) {
    console.log();
  }

  return {
    id: interactionId || "unknown_stream_id",
    output_text: outputText,
    steps: steps,
  };
}

async function runAgent(
  userTask,
  previousInteractionId = null,
  client = null
) {
  const activeClient = client || ai || getGenAIClient();
  const isWin = process.platform === "win32";
  const instructions = `
You are an autonomous coding agent.

Current project workspace:
${WORKSPACE}
Host Platform: ${process.platform} (${isWin ? "Windows" : "Linux/POSIX"})
Autonomous Mode: ${AUTO_APPROVE ? "ACTIVE (Operations auto-approved without prompts)" : "Interactive Approval Required"}

Complete the user's task instead of merely explaining it.

Available tools:
- list_files (list files in workspace or specific subdirectory; supports recursive listing)
- read_file (read text file with optional startLine/endLine range pagination)
- write_file (requires approval or autonomous mode; automatically creates directories)
- edit_file (incrementally replace unambiguous text block)
- run_command (cross-platform shell commands)
- run_executable (authorized Python interpreter: ${ALLOWED_PYTHON || "python3"})
- search_code (search codebase for literal text or regex)
- search_web (search the web for documentation, APIs, and error solutions)
- git_status (inspect workspace git status)
- git_diff (view unstaged or staged git diff)

ENVIRONMENT & PLATFORM RULES:
You are running on ${isWin ? "Windows" : "Linux/POSIX"}.
${isWin ? `For command execution, commands run via cmd.exe (use standard Windows syntax like dir, type, copy; do NOT use PowerShell-specific cmdlets).
For Python virtual environments, prefer:\n${ALLOWED_PYTHON || "python"}\nFor pip, prefer:\n${ALLOWED_PYTHON ? ALLOWED_PYTHON + " -m pip" : "python -m pip"}` : `Use bash / standard Linux utilities and python3 (${ALLOWED_PYTHON || "python3"}).`}

Avoid complicated nested quoting in commands.
Prefer existing test files or scripts over inline execution.

WORKFLOW:
1. Inspect relevant files.
2. Read relevant code.
3. Make the smallest necessary change.
4. Run the appropriate tests.
5. Diagnose failures.
6. Make targeted repairs.
7. Run tests again.
8. Verify the result.
9. Do not claim success without verification.

Maximum steps: ${MAX_STEPS}
Maximum repair attempts: ${MAX_REPAIR_ATTEMPTS}

WORKSPACE SAFETY:

Only access files inside:
${WORKSPACE}

Never intentionally access files outside the workspace.
Never use ../ to escape the workspace.

Do not modify unrelated files.

Do not run destructive operating-system commands.

FINAL VERIFICATION:

Before claiming completion:
- run the relevant test
- inspect the result
- verify requested behavior
- report what changed
- report verification result
`;

  let interaction;
  const input =
    instructions +
    "\n\nUser request:\n" +
    userTask;

  try {
    const requestParams = {
      model: MODEL,
      tools,
      input,
      stream: true,
    };

    if (previousInteractionId) {
      requestParams.previous_interaction_id = previousInteractionId;
    }

    console.log("\n--- GEMINI (Streaming) ---");
    const stream = await activeClient.interactions.create(requestParams);
    interaction = await consumeInteractionStream(stream);
  } catch (apiError) {
    if (isAuthenticationError(apiError)) {
      console.error("\n[AUTHENTICATION ERROR] HTTP 400 API_KEY_INVALID / Authentication failed. Please verify your GEMINI_API_KEY environment variable.");
      throw apiError;
    }

    const errMessage = String(apiError.message || apiError.toString()).toUpperCase();
    const isInteractionExpired = previousInteractionId && (errMessage.includes("INTERACTION") || errMessage.includes("NOT_FOUND") || errMessage.includes("EXPIRED") || errMessage.includes("PREVIOUS"));

    if (isInteractionExpired) {
      console.error("\n[WARNING] Previous interaction session expired or was not found. Starting a fresh interaction session...");
      const freshParams = {
        model: MODEL,
        tools,
        input: "Previous session expired or was invalid. " + input,
        stream: true,
      };
      const freshStream = await activeClient.interactions.create(freshParams);
      interaction = await consumeInteractionStream(freshStream);
    } else {
      throw apiError;
    }
  }

  let repairAttempts = 0;
  const executedCallIds = new Set();

  for (let step = 1; step <= MAX_STEPS; step++) {
    console.log(`\n========== AGENT STEP ${step}/${MAX_STEPS} ==========`);

    const stepsList = interaction.steps || [];
    const functionCalls = stepsList.filter(
      (item) => item && item.type === "function_call" && item.id && !executedCallIds.has(item.id)
    );

    if (functionCalls.length === 0) {
      if (stepsList.length === 0) {
        console.log("\n--- GEMINI ---");
        console.log(
          interaction.output_text ||
            "No response returned."
        );
      }

      if (interaction.id && interaction.id !== "unknown_stream_id") {
        await saveSession(interaction.id, userTask.substring(0, 50));
        return interaction.id;
      }
      return null;
    }

    const functionResults = [];

    for (const functionCall of functionCalls) {
      executedCallIds.add(functionCall.id);
      const result = await executeTool(functionCall);

      console.log("\n--- TOOL RESULT ---");
      console.log(JSON.stringify(result, null, 2));
      console.log("--- END TOOL RESULT ---");

      if (
        (functionCall.name === "run_command" || functionCall.name === "run_executable") &&
        result.success === false
      ) {
        if (repairAttempts >= MAX_REPAIR_ATTEMPTS) {
          console.log("\nMaximum repair attempts reached.");
          if (interaction.id && interaction.id !== "unknown_stream_id") {
            await saveSession(interaction.id, userTask.substring(0, 50));
            return interaction.id;
          }
          return null;
        }

        repairAttempts++;
        console.log(
          `EXECUTION FAILED - repair attempt ${repairAttempts}/${MAX_REPAIR_ATTEMPTS}`
        );
      }

      functionResults.push({
        type: "function_result",
        name: functionCall.name,
        call_id: functionCall.id,
        result: [
          {
            type: "text",
            text: JSON.stringify(result),
          },
        ],
      });
    }

    try {
      console.log("\n--- GEMINI (Streaming Tool Feedback) ---");
      const stepStream = await activeClient.interactions.create({
        model: MODEL,
        previous_interaction_id: interaction.id,
        tools,
        input: functionResults,
        stream: true,
      });
      interaction = await consumeInteractionStream(stepStream);
    } catch (stepApiError) {
      if (isAuthenticationError(stepApiError)) {
        console.error("\n[AUTHENTICATION ERROR] HTTP 400 API_KEY_INVALID / Authentication failed during step interaction.");
        throw stepApiError;
      }

      const stepErrMessage = String(stepApiError.message || stepApiError.toString()).toUpperCase();
      const isStepInteractionExpired = stepApiError && (stepErrMessage.includes("INTERACTION") || stepErrMessage.includes("NOT_FOUND") || stepErrMessage.includes("EXPIRED") || stepErrMessage.includes("PREVIOUS"));

      if (isStepInteractionExpired) {
        console.error("\n[WARNING] Step interaction creation failed (interaction ID expired). Restarting fresh session...");
        const freshStepStream = await activeClient.interactions.create({
          model: MODEL,
          tools,
          input: "Previous step interaction expired. " + JSON.stringify(functionResults),
          stream: true,
        });
        interaction = await consumeInteractionStream(freshStepStream);
      } else {
        throw stepApiError;
      }
    }
  }

  console.log("\nMaximum agent steps reached.");
  if (interaction.id && interaction.id !== "unknown_stream_id") {
    await saveSession(interaction.id, userTask.substring(0, 50));
    return interaction.id;
  }
  return null;
}

async function main() {
  console.log("========================================");
  console.log("       GEMINI CODING AGENT");
  console.log("       CROSS-PLATFORM STREAMING MODE");
  console.log("========================================");
  console.log("Project:", WORKSPACE);
  console.log("Platform:", process.platform);
  console.log("Model:", MODEL);
  console.log("Autonomous Mode:", AUTO_APPROVE ? "ENABLED (auto-approves permissions)" : "DISABLED (prompts for approvals)");
  console.log("Python Interpreter:", ALLOWED_PYTHON || "None detected");

  const sessions = await loadSessions();
  const sessionIds = Object.keys(sessions);
  if (sessionIds.length > 0) {
    console.log(`Loaded ${sessionIds.length} saved session(s) from .gemini_sessions.json`);
  }

  let interactionId = null;

  while (true) {
    const userTask = await ask("\nYou > ");

    if (!userTask) {
      continue;
    }

    const command = userTask.toLowerCase();

    if (command === "exit" || command === "quit") {
      console.log("\nGoodbye bro.");
      break;
    }

    if (command === "sessions") {
      const loaded = await loadSessions();
      console.log("\n--- SAVED SESSIONS ---");
      for (const [id, info] of Object.entries(loaded)) {
        console.log(`ID: ${id} | Title: "${info.title}" | Updated: ${info.updatedAt}`);
      }
      console.log("----------------------");
      continue;
    }

    if (command.startsWith("resume ")) {
      const targetId = userTask.substring(7).trim();
      const loaded = await loadSessions();
      if (loaded[targetId]) {
        interactionId = targetId;
        console.log(`\nResumed session: ${targetId} ("${loaded[targetId].title}")`);
      } else {
        console.log(`\nSession ID not found: ${targetId}. Note: Starting fresh or use valid ID.`);
      }
      continue;
    }

    console.log("\nStarting task...");

    try {
      interactionId = await runAgent(
        userTask,
        interactionId
      );
    } catch (error) {
      console.error("\nERROR:");
      console.error(error);
    }
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error("\nFATAL ERROR:");
    console.error(error);
  });
}

module.exports = {
  runAgent,
  isAuthenticationError,
  consumeInteractionStream,
  runCommand,
  isDangerousCommand,
  searchCode,
  editFile,
  isProtectedFile,
  searchWeb,
  getGitStatus,
  getGitDiff,
  listFiles,
  readFile,
  writeFile,
  discoverPythonInterpreter,
  AUTO_APPROVE,
};
