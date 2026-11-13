const { spawn } = require("child_process");

function runCommand(command) {
  return new Promise((resolve) => {
    console.log("Running:", command);

    // Ensure proper quoting for Windows cmd.exe /s /c when paths contain spaces
    const wrapped = command.startsWith('"') ? `"${command}"` : command;

    const cp = spawn("cmd.exe", ["/d", "/s", "/c", wrapped], {
      cwd: WORKSPACE,
      windowsHide: true,
      windowsVerbatimArguments: true,
      timeout: 30000,
    });

    let stdout = "";
    let stderr = "";

    cp.stdout.on("data", (data) => {
      stdout += data;
    });

    cp.stderr.on("data", (data) => {
      stderr += data;
    });

    cp.on("error", (error) => {
      resolve({
        success: false,
        exitCode: null,
        output: `COMMAND ERROR: ${error.message}`,
      });
    });

    cp.on("close", (code, signal) => {
      const output = [];

      if (stdout) {
        output.push(`STDOUT:\n${stdout}`);
      }

      if (stderr) {
        output.push(`STDERR:\n${stderr}`);
      }

      if (code !== 0) {
        output.push(`EXIT CODE: ${code}`);
        resolve({
          success: false,
          exitCode: code,
          output: output.join("\n"),
        });
        return;
      }

      resolve({
        success: true,
        exitCode: 0,
        output:
          output.length > 0
            ? output.join("\n")
            : "Command completed successfully.",
      });
    });
  });
}
