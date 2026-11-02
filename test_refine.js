const { spawn } = require("child_process");

function runCommandTestAllFixed(command) {
  return new Promise((resolve) => {
    // If command already starts and ends with quotes, wrapping it in another set of quotes 
    // makes cmd.exe /s /c strip the outer pair and keep the inner pair.
    // However, if the command does NOT start with a quote, wrapping it might interfere with complex commands or pipes.
    // Actually, let's check: if command starts with `"`, wrapping it with `"${command}"` works for paths with spaces.
    // What if command is a regular command like `python -c ...`? It does not start with `"`, so we don't wrap it.
    // Let's refine:
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
