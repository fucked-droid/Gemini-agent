const fs = require('fs');
const path = require('path');
const ENGINE_DIR = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine";

console.log("--- 1. SOURCE FILES ---");
['src/engine.py', 'src/universe.py', 'src/volatility.py', 'src/test_universe.py'].forEach(f => {
  const full = path.join(ENGINE_DIR, f);
  console.log(`\n=== FILE: ${f} ===`);
  console.log(fs.readFileSync(full, 'utf8').substring(0, 1500) + "\n... [truncated] ...");
});

console.log("\n--- 2. DATA DIRECTORY ---");
const dataDir = path.join(ENGINE_DIR, 'data');
if (fs.existsSync(dataDir)) {
  const files = fs.readdirSync(dataDir);
  console.log("Files in data/:", files);
  files.forEach(file => {
    const filePath = path.join(dataDir, file);
    const stats = fs.statSync(filePath);
    console.log(` - ${file} (${stats.size} bytes)`);
  });
} else {
  console.log("Data directory not found.");
}
