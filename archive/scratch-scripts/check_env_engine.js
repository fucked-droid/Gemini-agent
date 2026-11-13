const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const ENGINE_DIR = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine";

// 1. Env check
execFile(PYTHON, ["-c", "import sys; print(sys.executable); import pandas, pyarrow; print('pandas:', pandas.__version__); print('pyarrow:', pyarrow.__version__)"], { cwd: ENGINE_DIR }, (err1, out1, err1_stderr) => {
  console.log("--- 1. ENV CHECK ---");
  console.log("ERR:", err1);
  console.log("OUT:", out1);
  console.log("STDERR:", err1_stderr);

  // 2. Import check
  execFile(PYTHON, ["-c", "import sys; sys.path.insert(0, '.'); from src.engine import loadniftymaster, buildcoreengine, addregimelayer; print('ENGINE IMPORT OK')"], { cwd: ENGINE_DIR }, (err2, out2, err2_stderr) => {
    console.log("\n--- 2. ENGINE IMPORT CHECK ---");
    console.log("ERR:", err2);
    console.log("OUT:", out2);
    console.log("STDERR:", err2_stderr);
  });
});
