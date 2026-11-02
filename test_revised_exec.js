const { execFile } = require("child_process");
const path = require("path");
const fs = require("fs");

const WORKSPACE = path.resolve(process.cwd());
const ALLOWED_PYTHON = path.normalize("H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe");

function runCommand(command) {
  return new Promise((resolve) => {
    execFile(
      "cmd.exe",
      ["/d", "/s", "/c", command],
      {
        cwd: WORKSPACE,
        timeout: 30000,
        maxBuffer: 1024 * 1024,
        windowsHide: true,
      },
      (error, stdout, stderr) => {
        const output = [];
        if (stdout) output.push(`STDOUT:\n${stdout}`);
        if (stderr) output.push(`STDERR:\n${stderr}`);
        if (error) {
          const exitCode = typeof error.code === "number" ? error.code : null;
          if (exitCode !== null) output.push(`EXIT CODE: ${exitCode}`);
          else output.push(`COMMAND ERROR: ${error.message}`);
          return resolve({ success: false, exitCode, output: output.join("\n") });
        }
        resolve({ success: true, exitCode: 0, output: output.join("\n") || "Success" });
      }
    );
  });
}

function runExecutable(file, args = []) {
  return new Promise((resolve) => {
    const normalizedFile = path.normalize(path.resolve(WORKSPACE, file));
    if (normalizedFile.toLowerCase() !== ALLOWED_PYTHON.toLowerCase()) {
      return resolve({
        success: false,
        exitCode: null,
        output: `Executable not authorized: ${file}`
      });
    }

    execFile(
      file,
      args,
      {
        cwd: WORKSPACE,
        timeout: 30000,
        maxBuffer: 1024 * 1024,
        windowsHide: true,
      },
      (error, stdout, stderr) => {
        const output = [];
        if (stdout) output.push(`STDOUT:\n${stdout}`);
        if (stderr) output.push(`STDERR:\n${stderr}`);
        if (error) {
          const exitCode = typeof error.code === "number" ? error.code : null;
          if (exitCode !== null) output.push(`EXIT CODE: ${exitCode}`);
          else output.push(`EXECUTABLE ERROR: ${error.message}`);
          return resolve({ success: false, exitCode, output: output.join("\n") });
        }
        resolve({ success: true, exitCode: 0, output: output.join("\n") || "Success" });
      }
    );
  });
}

async function runTests() {
  console.log("--- TEST 1: Shell command with a pipe ---");
  const res1 = await runCommand("echo hello | findstr hello");
  console.log(res1);

  console.log("\n--- TEST 2: Unauthorized executable ---");
  const res2 = await runExecutable("notepad.exe", ["README.md"]);
  console.log(res2);

  console.log("\n--- TEST 3: Authorized Python executable with space path & script with space path ---");
  // Let's create a script path with spaces in workspace if needed, or use inspect_data.py
  const scriptPath = "inspect data.py";
  fs.writeFileSync(scriptPath, "import sys; print('PYTHON OK:', sys.argv[1:])");
  const res3 = await runExecutable(ALLOWED_PYTHON, [scriptPath, "hello world", "foo\"bar"]);
  console.log(res3);
  try { fs.unlinkSync(scriptPath); } catch(e) {}

  console.log("\n--- TEST 4: Nonzero exit code ---");
  const res4 = await runExecutable(ALLOWED_PYTHON, ["-c", "import sys; sys.exit(42)"]);
  console.log(res4);

  console.log("\n--- TEST 5: Timeout handling ---");
  // Test timeout with very short timeout
  const res5 = await new Promise((resolve) => {
    execFile(ALLOWED_PYTHON, ["-c", "import time; time.sleep(2)"], { timeout: 200, cwd: WORKSPACE }, (error, stdout, stderr) => {
      resolve({ error, stdout, stderr });
    });
  });
  console.log("Timeout test result:", res5);
}

runTests();
