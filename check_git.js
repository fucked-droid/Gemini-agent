const { execFile } = require("child_process");
execFile("git", ["status", "--short"], {
  cwd: "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine"
}, (err, stdout, stderr) => {
  console.log("ERR:", err);
  console.log("STDOUT:", stdout);
  console.log("STDERR:", stderr);
});
