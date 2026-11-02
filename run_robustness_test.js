const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const WORKSPACE = ".";

console.log("Running robustness tests...");

execFile(PYTHON, ["test_mtf_robustness.py"], { cwd: WORKSPACE }, (err, stdout, stderr) => {
  console.log("ERR:", err);
  console.log("STDOUT:", stdout);
  console.log("STDERR:", stderr);
});
