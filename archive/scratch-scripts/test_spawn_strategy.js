const { spawn } = require("child_process");

function runCommandTestSpawn(command, cwd = process.cwd()) {
  return new Promise((resolve) => {
    // Split command into cmd and args or run via cmd.exe /s /c with proper quoting
    // Or even better, use spawn("cmd.exe", ["/d", "/s", "/c", command], { shell: false, windowsVerbatimArguments: true })
    const cp = spawn("cmd.exe", ["/d", "/s", "/c", command], {
      cwd,
      windowsHide: true,
      windowsVerbatimArguments: true,
    });

    let stdout = "";
    let stderr = "";

    cp.stdout.on("data", (data) => { stdout += data; });
    cp.stderr.on("data", (data) => { stderr += data; });

    cp.on("close", (code, signal) => {
      resolve({ success: code === 0, exitCode: code, stdout, stderr });
    });
  });
}

async function runTests() {
  console.log("=== RUNNING SPAWN WINDOWSVERBATIMARGUMENTS TESTS ===");
  const pyPath = `H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe`;
  
  const t2 = await runCommandTestSpawn(`"${pyPath}" verify_env.py`);
  console.log("Result 2 (spawn):", t2);
}

runTests();
