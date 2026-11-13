const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const WORKSPACE = ".";

console.log("Running final targeted audit of all multi-timeframe and weekly alignment tests...");

execFile(PYTHON, ["-m", "unittest", "test_multi_timeframe.py", "test_mtf_rigor.py", "test_mtf_robustness.py", "test_weekly_alignment_exact.py"], { cwd: WORKSPACE }, (err, stdout, stderr) => {
  console.log("ERR:", err);
  console.log("STDOUT:", stdout);
  console.log("STDERR:", stderr);
});
