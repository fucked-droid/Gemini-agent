const { exec } = require("child_process");

function runCommandTestShell(command) {
  return new Promise((resolve) => {
    console.log("Running via exec shell:", command);
    exec(
      command,
      {
        cwd: process.cwd(),
        timeout: 10000,
        windowsHide: true,
      },
      (error, stdout, stderr) => {
        resolve({ error, stdout, stderr });
      }
    );
  });
}

async function main() {
  const pyPath = `H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe`;
  const testCmd1 = `"${pyPath}" verify_env.py`;
  const r = await runCommandTestShell(testCmd1);
  console.log("Result shell:", r);
}

main();
