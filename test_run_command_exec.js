const { exec } = require("child_process");

function runCommand(command) {
  return new Promise((resolve) => {
    console.log("Running:", command);

    exec(
      command,
      {
        cwd: process.cwd(),
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

async function main() {
  const pyPath = `H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe`;
  const res = await runCommand(`"${pyPath}" verify_env.py`);
  console.log("RunCommand test result:", res);
}

main();
