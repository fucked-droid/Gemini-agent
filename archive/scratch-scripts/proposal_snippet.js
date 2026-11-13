const { exec } = require("child_process");

function runCommand(command) {
  return new Promise((resolve) => {
    console.log("Running:", command);

    // To support complex shell features (pipes, redirects, builtins) while correctly
    // handling Windows command strings and paths with spaces when invoked via cmd.exe,
    // we use `exec` (which spawns cmd.exe /s /c under the hood on Windows with proper shell evaluation)
    // while preserving all outputs, exit codes, and robust error handling.
    exec(
      command,
      {
        cwd: WORKSPACE,
        timeout: 30000,
        maxBuffer: 1024 * 1024,
        windowsHide: true,
      },
      (error, stdout, stderr) => {
        const output = [];

        if (stdout) {
          output.push(`STDOUT:\n${stdout}`);
        }

        if (stderr) {
          output.push(`STDERR:\n${stderr}`);
        }

        if (error) {
          const exitCode =
            typeof error.code === "number"
              ? error.code
              : null;

          if (exitCode !== null) {
            output.push(`EXIT CODE: ${exitCode}`);
          } else {
            output.push(
              `COMMAND ERROR: ${error.message}`
            );
          }

          resolve({
            success: false,
            exitCode,
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
      }
    );
  });
}
