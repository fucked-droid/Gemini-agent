/**
 * Nifty Daily Market Regime Engine - Bearish Focus
 */

function analyzeBearishRegime(close, sma50, sma200, atr, avgAtr) {
  if (close < sma50 && sma50 < sma200 && atr >= avgAtr * 1.3) {
    return "Strong_Bearish (High Volatility / Panic)";
  } else if (close < sma50 && sma50 < sma200) {
    return "Bearish (Established Downtrend)";
  } else {
    return "Not currently in Bearish regime";
  }
}

// Test cases demonstrating Bearish regimes
const testCases = [
  { c: 90, s50: 95, s200: 100, atr: 3.5, avgAtr: 2, expected: "Strong_Bearish (High Volatility / Panic)" },
  { c: 92, s50: 95, s200: 100, atr: 2, avgAtr: 2, expected: "Bearish (Established Downtrend)" },
  { c: 105, s50: 102, s200: 100, atr: 2, avgAtr: 2, expected: "Not currently in Bearish regime" }
];

console.log("=== Bearish Regime Analysis ===");
testCases.forEach((tc, index) => {
  const result = analyzeBearishRegime(tc.c, tc.s50, tc.s200, tc.atr, tc.avgAtr);
  console.log(`Test ${index + 1}: ${result}`);
});

module.exports = { analyzeBearishRegime };
