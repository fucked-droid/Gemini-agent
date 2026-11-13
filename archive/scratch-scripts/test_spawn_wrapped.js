const { spawn } = require("child_process");

function runCommandTestSpawnWrapped(command, cwd = process.cwd()) {
  return new Promise((resolve) => {
    // When using windowsVerbatimArguments: true with cmd.exe /s /c, 
    // wrapping the entire command string in quotes causes cmd.exe to strip the outer quotes correctly
    // and preserve internal quotes around paths with spaces.
    const wrapped = `"${command}"`;
    const cp = spawn("cmd.exe", ["/d", "/s", "/c", wrapped], {
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
  console.log("=== RUNNING SPAWN WRAPPED WINDOWSVERBATIMARGUMENTS TESTS ===");
  const pyPath = `H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe`;
  
  const t2 = await runCommandTestSpawnWrapped(`"${pyPath}" verify_env.py`);
  console.log("Result 2 (spawn wrapped):", t2);
}

runTests();
