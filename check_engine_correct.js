const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const ENGINE_DIR = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine";

execFile(PYTHON, ["-c", "import sys; sys.path.insert(0, '.'); from src.engine import load_nifty_master, build_core_engine, add_regime_layer; print('ENGINE IMPORT OK')"], { cwd: ENGINE_DIR }, (err, out, stderr) => {
  console.log("ERR:", err);
  console.log("OUT:", out);
  console.log("STDERR:", stderr);
});
