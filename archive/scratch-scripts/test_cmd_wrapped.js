const { execFile } = require("child_process");

function runCommandTestWrapped(command) {
  return new Promise((resolve) => {
    // According to cmd.exe documentation, if you use enclosing quotes around the whole command string:
    // cmd.exe /d /c ""path with spaces\python.exe" script.py"
    // The outer quotes are stripped by cmd.exe, leaving the inner quoted path intact!
    const wrapped = `"${command}"`;
    console.log("Wrapped command passed to cmd /c:", wrapped);
    
    execFile(
      "cmd.exe",
      ["/d", "/c", wrapped],
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
  const r1 = await runCommandTestWrapped(testCmd1);
  console.log("Result 1 wrapped:", r1);
}

main();
