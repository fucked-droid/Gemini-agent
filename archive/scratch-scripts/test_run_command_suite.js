const { exec } = require("child_process");

function runCommandTest(command, cwd = process.cwd()) {
  return new Promise((resolve) => {
    exec(
      command,
      {
        cwd,
        timeout: 10000,
        windowsHide: true,
      },
      (error, stdout, stderr) => {
        const exitCode = error && typeof error.code === "number" ? error.code : (error ? 1 : 0);
        resolve({ success: !error, exitCode, stdout, stderr, error });
      }
    );
  });
}

async function runTests() {
  console.log("=== RUNNING FOCUSED TESTS FOR runCommand FIX ===");

  // Test 1: Basic Python script execution
  console.log("\n[Test 1] Basic python script execution:");
  const t1 = await runCommandTest("python -c \"print('basic test')\"");
  console.log("Result 1:", t1);

  // Test 2: Python executable path containing spaces
  console.log("\n[Test 2] Python executable path containing spaces:");
  const pyPath = `H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe`;
  const t2 = await runCommandTest(`"${pyPath}" verify_env.py`);
  console.log("Result 2:", t2);

  // Test 3: Script path containing spaces (simulate with a test script in a path with spaces or quoted script path)
  console.log("\n[Test 3] Script path containing spaces:");
  const t3 = await runCommandTest(`"${pyPath}" "verify_env.py"`);
  console.log("Result 3:", t3);

  // Test 4: Shell command using a pipe
  console.log("\n[Test 4] Shell command using a pipe:");
  const t4 = await runCommandTest("echo hello world | findstr hello");
  console.log("Result 4:", t4);

  // Test 5: Correct reporting of nonzero exit codes
  console.log("\n[Test 5] Nonzero exit code reporting:");
  const t5 = await runCommandTest(`"${pyPath}" -c "import sys; sys.exit(42)"`);
  console.log("Result 5:", t5);

  console.log("\n=== ALL TESTS COMPLETED ===");
}

runTests();
