const fs = require('fs');
const path = require('path');

const srcPath = path.resolve('propose_multi_timeframe.py');
const destDir = path.resolve('H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\src');
const destPath = path.join(destDir, 'multi_timeframe.py');

console.log("Reading proposal module:", srcPath);
const code = fs.readFileSync(srcPath, 'utf8');

console.log("Writing to market engine src:", destPath);
fs.writeFileSync(destPath, code, 'utf8');

console.log("Successfully integrated multi_timeframe.py into Daily-Market-Regime-Engine src directory!");
