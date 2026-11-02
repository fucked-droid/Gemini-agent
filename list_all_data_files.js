const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const ENGINE_DIR = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine";

const script = `
import pandas as pd
from pathlib import Path

data_dir = Path("data")
for p in data_dir.glob("**/*"):
    if p.is_file():
        print(p, p.stat().st_size)
`;

execFile(PYTHON, ["-c", script], { cwd: ENGINE_DIR }, (err, stdout, stderr) => {
  console.log("OUT:\n", stdout);
});
