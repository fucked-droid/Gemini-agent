const assert = require("assert");
const { analyzeBearishRegime } = require("./bearish_regime");

console.log("Running automated tests for bearish regime...");

assert.strictEqual(
  analyzeBearishRegime(90, 95, 100, 3.5, 2),
  "Strong_Bearish (High Volatility / Panic)"
);

assert.strictEqual(
  analyzeBearishRegime(92, 95, 100, 2, 2),
  "Bearish (Established Downtrend)"
);

assert.strictEqual(
  analyzeBearishRegime(105, 102, 100, 2, 2),
  "Not currently in Bearish regime"
);

console.log("All bearish regime tests passed successfully!");
