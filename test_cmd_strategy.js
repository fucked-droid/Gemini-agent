const { runCommand } = require("./index.js");
const assert = require("assert");

async function main() {
  console.log("Testing command execution strategies...");

  // Test 1: Python executable path containing spaces
  const pyPath = `H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe`;
  const testCmd1 = `"${pyPath}" verify_env.py`;
  console.log("Running test 1 with cmd:", testCmd1);
  const r1 = await runCommand(testCmd1);
  console.log("Result 1:", r1);
  assert.strictEqual(r1.success, true, "Command with spaces in executable path should succeed");
  assert.strictEqual(r1.exitCode, 0, "Exit code should be 0");
  assert.ok(r1.output.includes("Python executable"), "Output should contain expected script output");

  // Test 2: Local executable path containing spaces (Program Files)
  const nodePath = "C:\\Program Files\\nodejs\\node.exe";
  const testCmd2 = `"${nodePath}" -v`;
  console.log("Running test 2 with cmd:", testCmd2);
  const r2 = await runCommand(testCmd2);
  console.log("Result 2:", r2);
  assert.strictEqual(r2.success, true, "Local path with spaces should succeed");
  assert.strictEqual(r2.exitCode, 0, "Exit code should be 0");

  // Test 3: Piping support
  const testCmd3 = "echo test-pipe | findstr test-pipe";
  console.log("Running test 3 with cmd:", testCmd3);
  const r3 = await runCommand(testCmd3);
  console.log("Result 3:", r3);
  assert.strictEqual(r3.success, true, "Piped shell command should succeed");
  assert.strictEqual(r3.exitCode, 0, "Exit code should be 0");

  console.log("\nAll command strategy tests passed successfully!");
}

main().catch((err) => {
  console.error("Test failure:", err);
  process.exit(1);
});
