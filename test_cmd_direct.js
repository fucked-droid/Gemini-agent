const { execFile } = require("child_process");

function runCommandTestDirect(pythonExe, scriptPath) {
  return new Promise((resolve) => {
    console.log("Running directly via execFile:", pythonExe, [scriptPath]);
    execFile(
      pythonExe,
      [scriptPath],
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
  const r = await runCommandTestDirect(pyPath, "verify_env.py");
  console.log("Result direct:", r);
}

main();
