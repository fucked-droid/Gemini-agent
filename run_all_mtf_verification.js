const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const WORKSPACE = ".";

console.log("Running all multi-timeframe verification tests...");

execFile(PYTHON, ["-m", "unittest", "test_multi_timeframe.py", "test_mtf_rigor.py"], { cwd: WORKSPACE }, (err, stdout, stderr) => {
  console.log("ERR:", err);
  console.log("STDOUT:", stdout);
  console.log("STDERR:", stderr);
});
