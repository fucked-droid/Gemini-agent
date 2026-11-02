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
  getGitDiff
} = require("./index.js");

console.log("=== RUNNING GEMINI-AGENT CROSS-PLATFORM & CAPABILITY SUITE ===\n");

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
runCommand("echo 'Agent shell is operational'")
  .then((res) => {
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
    return getGitStatus().then((status) => {
      assert.strictEqual(typeof status, "string");
      console.log("Current git status snippet:", status.slice(0, 100));
      return getGitDiff().then((diff) => {
        assert.strictEqual(typeof diff, "string");
        console.log("✓ Git tools operational.\n");

        // Test 5: Incremental Block Editing
        console.log("Test 5: Incremental File Editing");
        const tmpFile = path.resolve(process.cwd(), "test_edit_sample.tmp");
        fs.writeFileSync(tmpFile, "line1\nTARGET_BLOCK_V1\nline3\n", "utf8");
        return editFile("test_edit_sample.tmp", "TARGET_BLOCK_V1", "TARGET_BLOCK_V2")
          .then((editRes) => {
            const updated = fs.readFileSync(tmpFile, "utf8");
            assert.ok(updated.includes("TARGET_BLOCK_V2"));
            assert.ok(!updated.includes("TARGET_BLOCK_V1"));
            fs.unlinkSync(tmpFile);
            console.log("✓ editFile precision verified.\n");

            console.log("==================================================");
            console.log("ALL TESTS COMPLETED SUCCESSFULLY! 100% PASS.");
            console.log("==================================================");
          });
      });
    });
  })
  .catch((err) => {
    console.error("Test failed:", err);
    process.exit(1);
  });
