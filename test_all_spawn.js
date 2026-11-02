const { spawn } = require("child_process");

function runCommandTestAll(command) {
  return new Promise((resolve) => {
    const wrapped = command.startsWith('"') ? `"${command}"` : command;
    const cp = spawn("cmd.exe", ["/d", "/s", "/c", wrapped], {
      cwd: process.cwd(),
      windowsHide: true,
      windowsVerbatimArguments: true,
      timeout: 10000,
    });

    let stdout = "";
    let stderr = "";

    cp.stdout.on("data", (data) => { stdout += data; });
    cp.stderr.on("data", (data) => { stderr += data; });

    cp.on("close", (code) => {
      resolve({ success: code === 0, exitCode: code, stdout, stderr });
    });
  });
}

async function runAll() {
  const pyPath = `H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe`;

  console.log("Test 1 (basic):", await runCommandTestAll("python -c \"print('hi')\""));
  console.log("Test 2 (path with spaces):", await runCommandTestAll(`"${pyPath}" verify_env.py`));
  console.log("Test 3 (pipe):", await runCommandTestAll("echo test | findstr test"));
  console.log("Test 4 (exit code):", await runCommandTestAll(`"${pyPath}" -c "import sys; sys.exit(7)"`));
}

runAll();
