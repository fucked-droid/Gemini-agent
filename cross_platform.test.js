const assert = require("assert");
const fs = require("fs");
const path = require("path");
const {
  isDangerousCommand,
  runCommand,
  isProtectedFile,
  editFile,
  searchCode,
  getGitStatus,
  getGitDiff,
  listFiles,
  readFile,
  writeFile,
  discoverPythonInterpreter,
} = require("./index.js");

console.log("=== RUNNING GEMINI-AGENT CROSS-PLATFORM & CAPABILITY SUITE ===\n");

async function runTests() {
  // Test 1: POSIX & Windows Dangerous Command Defense
  console.log("Test 1: Dangerous Command Defense (POSIX & Windows)");
  // Windows blocked commands
  assert.strictEqual(isDangerousCommand("del file.txt"), true);
  assert.strictEqual(isDangerousCommand("erase secret.doc"), true);
  assert.strictEqual(isDangerousCommand("rmdir /s /q temp"), true);
  assert.strictEqual(isDangerousCommand("rd /s build"), true);
  assert.strictEqual(isDangerousCommand("format c:"), true);
  assert.strictEqual(isDangerousCommand("shutdown"), true);
  assert.strictEqual(isDangerousCommand("taskkill /f /im node.exe"), true);
  assert.strictEqual(isDangerousCommand("^d^e^l file.txt"), true);
  assert.strictEqual(isDangerousCommand("echo hi && del file.txt"), true);

  // POSIX blocked commands
  assert.strictEqual(isDangerousCommand("rm -rf /"), true, "Must block rm -rf /");
  assert.strictEqual(isDangerousCommand("rm -fr /*"), true, "Must block rm -fr /*");
  assert.strictEqual(isDangerousCommand("rm -rf ~/"), true, "Must block rm -rf ~/");
  assert.strictEqual(isDangerousCommand("echo 1 && rm -rf /"), true, "Must block chained rm -rf /");
  assert.strictEqual(isDangerousCommand("dd if=/dev/zero of=/dev/sda"), true, "Must block dd if= block overwrite");
  assert.strictEqual(isDangerousCommand(":(){ :|:& };:"), true, "Must block fork bomb");
  assert.strictEqual(isDangerousCommand("reboot"), true, "Must block reboot");
  assert.strictEqual(isDangerousCommand("poweroff"), true, "Must block poweroff");
  assert.strictEqual(isDangerousCommand("mkfs.ext4 /dev/sda1"), true, "Must block mkfs");
  assert.strictEqual(isDangerousCommand("chmod -R 777 /"), true, "Must block recursive root chmod 777");

  // Safe commands must NOT be blocked
  assert.strictEqual(isDangerousCommand("git status"), false);
  assert.strictEqual(isDangerousCommand("node --version"), false);
  assert.strictEqual(isDangerousCommand("npm test"), false);
  assert.strictEqual(isDangerousCommand("ls -la src/"), false);
  assert.strictEqual(isDangerousCommand("python3 -m unittest"), false);
  console.log("✓ Dangerous command defenses passed (both POSIX and Windows verified).\n");

  // Test 2: Cross-Platform runCommand Execution
  console.log("Test 2: Cross-Platform Shell Execution");
  const res = await runCommand("echo 'Agent shell is operational'");
  assert.strictEqual(res.success, true);
  assert.ok(res.output.includes("Agent shell is operational"));
  console.log("✓ Cross-platform runCommand execution verified.\n");

  // Test 3: Protected File Defense
  console.log("Test 3: Protected File Shielding");
  assert.strictEqual(isProtectedFile(".env"), true);
  assert.strictEqual(isProtectedFile(".env.local"), true);
  assert.strictEqual(isProtectedFile(".gemini_sessions.json"), true);
  assert.strictEqual(isProtectedFile("src/engine.py"), false);
  assert.strictEqual(isProtectedFile("package.json"), false);
  console.log("✓ Protected file shield verified.\n");

  // Test 4: Git Status & Diff Tools
  console.log("Test 4: Git Status & Diff Introspection");
  const status = await getGitStatus();
  assert.strictEqual(typeof status, "string");
  console.log("Current git status snippet:", status.slice(0, 100));
  const diff = await getGitDiff();
  assert.strictEqual(typeof diff, "string");
  console.log("✓ Git tools operational.\n");

  // Test 5: Incremental Block Editing
  console.log("Test 5: Incremental File Editing");
  const tmpEditFile = path.resolve(process.cwd(), "test_edit_sample.tmp");
  fs.writeFileSync(tmpEditFile, "line1\nTARGET_BLOCK_V1\nline3\n", "utf8");
  await editFile("test_edit_sample.tmp", "TARGET_BLOCK_V1", "TARGET_BLOCK_V2");
  const updated = fs.readFileSync(tmpEditFile, "utf8");
  assert.ok(updated.includes("TARGET_BLOCK_V2"));
  assert.ok(!updated.includes("TARGET_BLOCK_V1"));
  fs.unlinkSync(tmpEditFile);
  console.log("✓ editFile precision verified.\n");

  // Test 6: Recursive writeFile with Parent Directory Creation
  console.log("Test 6: Recursive writeFile Directory Creation");
  const nestedRelPath = path.join(".test_tmp_dir", "sub1", "sub2", "test_out.txt");
  await writeFile(nestedRelPath, "Hello nested directory!");
  const writtenContent = fs.readFileSync(path.resolve(process.cwd(), nestedRelPath), "utf8");
  assert.strictEqual(writtenContent, "Hello nested directory!");
  // Cleanup test folder
  fs.rmSync(path.resolve(process.cwd(), ".test_tmp_dir"), { recursive: true, force: true });
  console.log("✓ writeFile parent directory auto-creation verified.\n");

  // Test 7: Subdirectory & Recursive listFiles
  console.log("Test 7: Subdirectory & Recursive listFiles");
  const rootListing = await listFiles();
  assert.ok(rootListing.includes("package.json"));
  assert.ok(rootListing.includes("index.js"));

  const recursiveListing = await listFiles("", true);
  assert.ok(recursiveListing.includes("package.json"));
  console.log("✓ listFiles root & recursive inspection verified.\n");

  // Test 8: Paginated Line Range readFile
  console.log("Test 8: Paginated Line Range readFile");
  const pagedContent = await readFile("package.json", 1, 5);
  assert.ok(pagedContent.includes("[Viewing lines 1-5 of"));
  assert.ok(pagedContent.includes("1: {"));
  console.log("✓ readFile line range pagination verified.\n");

  // Test 9: Python Discovery Resilience
  console.log("Test 9: Python Interpreter Discovery Resilience");
  const discovered = discoverPythonInterpreter();
  console.log("Discovered interpreter:", discovered || "None (valid in minimal environments)");
  // Ensure function executes cleanly without throwing
  assert.ok(discovered === null || typeof discovered === "string");
  console.log("✓ Python discovery resilience verified.\n");

  console.log("==================================================");
  console.log("ALL TESTS COMPLETED SUCCESSFULLY! 100% PASS.");
  console.log("==================================================");
}

runTests().catch((err) => {
  console.error("Test suite failed:", err);
  process.exit(1);
});
