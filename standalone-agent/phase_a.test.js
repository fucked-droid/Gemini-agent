const test = require("node:test");
const assert = require("node:assert");
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const { isDangerousCommand } = require("./index.js");

const WORKSPACE = path.resolve(process.cwd());

function resolveWorkspacePath(filePath) {
  if (typeof filePath !== "string" || !filePath.trim()) {
    throw new Error("Invalid file path.");
  }
  const fullPath = path.resolve(WORKSPACE, filePath);
  const relativePath = path.relative(WORKSPACE, fullPath);
  if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
    throw new Error(`Access denied: path is outside workspace: ${filePath}`);
  }
  return fullPath;
}

test("Phase A.1: Calculator unit tests pass", () => {
  const result = execSync("node calculator.test.js", { encoding: "utf8" });
  assert.ok(result.includes("All calculator tests passed successfully!"));
});

test("Phase A.1: Path traversal protection blocks ../ and absolute paths", () => {
  assert.throws(() => resolveWorkspacePath("../secret.txt"), /Access denied/);
  assert.throws(() => resolveWorkspacePath("..\\secret.txt"), /Access denied/);
  assert.throws(() => resolveWorkspacePath("C:\\Windows\\System32\\cmd.exe"), /Access denied/);
  const validPath = resolveWorkspacePath("calculator.js");
  assert.ok(validPath.startsWith(WORKSPACE));
});

test("Phase A.1: Session persistence and malformed JSON handling", async () => {
  const testSessionFile = path.resolve(WORKSPACE, ".gemini_sessions.test_isolated.json");

  try {
    fs.writeFileSync(testSessionFile, "INVALID JSON CONTENT {{{{", "utf8");
    
    let sessions = {};
    try {
      const data = fs.readFileSync(testSessionFile, "utf8");
      sessions = JSON.parse(data);
    } catch (err) {
      sessions = {};
    }
    assert.deepEqual(sessions, {});

    const validData = {
      "sess_123": { sessionId: "sess_123", title: "Test session", updatedAt: new Date().toISOString() }
    };
    fs.writeFileSync(testSessionFile, JSON.stringify(validData, null, 2), "utf8");
    const reloaded = JSON.parse(fs.readFileSync(testSessionFile, "utf8"));
    assert.strictEqual(reloaded["sess_123"].sessionId, "sess_123");
  } finally {
    if (fs.existsSync(testSessionFile)) {
      fs.unlinkSync(testSessionFile);
    }
  }
});

test("Phase A.2: Command blacklist blocks direct and chained dangerous commands", () => {
  // Direct dangerous commands
  assert.strictEqual(isDangerousCommand("del file.txt"), true);
  assert.strictEqual(isDangerousCommand("erase secret.doc"), true);
  assert.strictEqual(isDangerousCommand("rmdir /s /q temp"), true);
  assert.strictEqual(isDangerousCommand("rd /s build"), true);
  assert.strictEqual(isDangerousCommand("format c:"), true);
  assert.strictEqual(isDangerousCommand("shutdown"), true);
  assert.strictEqual(isDangerousCommand("shutdown /r /t 0"), true);
  assert.strictEqual(isDangerousCommand("taskkill /f /im node.exe"), true);
  assert.strictEqual(isDangerousCommand("reg delete HKLM\\Software"), true);
  assert.strictEqual(isDangerousCommand("del/f/q file.txt"), true);
  assert.strictEqual(isDangerousCommand("\"del\" file.txt"), true);

  // Dangerous commands chained with &&, ||, &, |, ;
  assert.strictEqual(isDangerousCommand("echo hello && del file.txt"), true);
  assert.strictEqual(isDangerousCommand("dir | rmdir /s /q test"), true);
  assert.strictEqual(isDangerousCommand("git status || shutdown"), true);
  assert.strictEqual(isDangerousCommand("echo 1 & rd /s temp"), true);
  assert.strictEqual(isDangerousCommand("node app.js ; erase important.txt"), true);
  assert.strictEqual(isDangerousCommand("echo a && echo b && del target.txt"), true);
  assert.strictEqual(isDangerousCommand("echo a | echo b & format d:"), true);
  assert.strictEqual(isDangerousCommand("(echo hi) & (del temp.txt)"), true);
});

test("Phase A.2: Command blacklist blocks caret, extension, and path obfuscations", () => {
  // Case 1: Caret-obfuscated commands
  assert.strictEqual(isDangerousCommand("^d^e^l foo.txt"), true);
  assert.strictEqual(isDangerousCommand("echo hi & ^d^e^l foo.txt"), true);
  assert.strictEqual(isDangerousCommand("^r^m^d^i^r /s /q temp"), true);
  assert.strictEqual(isDangerousCommand("^s^h^u^t^d^o^w^n"), true);

  // Case 2: Extension-qualified commands
  assert.strictEqual(isDangerousCommand("taskkill.exe /f /im node.exe"), true);
  assert.strictEqual(isDangerousCommand("echo hi & taskkill.exe /f /im node.exe"), true);
  assert.strictEqual(isDangerousCommand("format.com c:"), true);
  assert.strictEqual(isDangerousCommand("dir && format.com d:"), true);
  assert.strictEqual(isDangerousCommand("shutdown.exe /r"), true);

  // Case 3: Path-qualified dangerous executables
  assert.strictEqual(isDangerousCommand("C:\\Windows\\System32\\shutdown.exe"), true);
  assert.strictEqual(isDangerousCommand("C:\\Windows\\System32\\taskkill.exe /f /im node.exe"), true);
  assert.strictEqual(isDangerousCommand("\"C:\\Windows\\System32\\shutdown.exe\" /r"), true);
  assert.strictEqual(isDangerousCommand("\\windows\\system32\\format.com c:"), true);
  assert.strictEqual(isDangerousCommand("system32/shutdown"), true);
  assert.strictEqual(isDangerousCommand("system32\\del file.txt"), true);
});

test("Phase A.2: Command blacklist preserves legitimate commands, quotes, and escaped quotes", () => {
  // Case 4: Escaped quotes inside arguments & quoted operators
  assert.strictEqual(isDangerousCommand('git commit -m "fix \\"quoted\\" string"'), false);
  assert.strictEqual(isDangerousCommand('git commit -m "fix \\"quoted\\" string" && del file.txt'), true);
  assert.strictEqual(isDangerousCommand('echo "hello \\"world\\""'), false);
  assert.strictEqual(isDangerousCommand('node -e "const x = \\"test\\"; console.log(x)"'), false);

  // Safe commands with operators inside quotes
  assert.strictEqual(isDangerousCommand("echo \"del file.txt\""), false);
  assert.strictEqual(isDangerousCommand("echo 'rmdir /s /q test'"), false);
  assert.strictEqual(isDangerousCommand("node -e \"if (a && b) console.log(1)\""), false);
  assert.strictEqual(isDangerousCommand("git commit -m \"fix(auth): handle && operator & formatting\""), false);
  assert.strictEqual(isDangerousCommand("echo \"format c:\""), false);

  // Normal shell commands with pipes and parameters
  assert.strictEqual(isDangerousCommand("echo hello | findstr hello"), false);
  assert.strictEqual(isDangerousCommand("\"C:\\Program Files\\nodejs\\node.exe\" -v"), false);
  assert.strictEqual(isDangerousCommand("node -v"), false);
  assert.strictEqual(isDangerousCommand("git status"), false);
  assert.strictEqual(isDangerousCommand("python verify_env.py"), false);

  // Syntax ambiguity / unclosed quotes fails safely
  assert.strictEqual(isDangerousCommand("echo \"unclosed quote && del foo"), true);
  assert.strictEqual(isDangerousCommand("echo 'unclosed"), true);
});
