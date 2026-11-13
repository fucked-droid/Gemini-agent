const assert = require("assert");
const { calculateSMA, calculateATR, determineRegime } = require("./nifty_regime");

console.log("Running Nifty Regime Tests...");

const prices = [100, 102, 104, 106, 108, 110];
const sma = calculateSMA(prices, 3);
assert.strictEqual(sma[5], (106 + 108 + 110) / 3);

const regime = determineRegime(110, 105, 100, 2, 3);
assert.strictEqual(regime, "Strong Bullish Trend");

console.log("All tests passed successfully!");
