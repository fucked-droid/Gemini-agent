/**
 * Extended Nifty Daily Market Regime Engine
 * Supports: Bearish, Bullish, Mixed, Strong_Bearish, Strong_Bullish
 */

function determineRegimeDetailed(close, sma50, sma200, atr, avgAtr) {
  if (close > sma50 && sma50 > sma200 && atr < avgAtr * 1.3) {
    return "Strong_Bullish";
  } else if (close > sma50 && sma50 > sma200) {
    return "Bullish";
  } else if (close < sma50 && sma50 < sma200 && atr < avgAtr * 1.3) {
    return "Strong_Bearish";
  } else if (close < sma50 && sma50 < sma200) {
    return "Bearish";
  } else {
    return "Mixed";
  }
}

// Verification test cases
const testCases = [
  { c: 110, s50: 105, s200: 100, atr: 2, avgAtr: 2, expected: "Strong_Bullish" },
  { c: 106, s50: 105, s200: 100, atr: 3, avgAtr: 2, expected: "Bullish" },
  { c: 90, s50: 95, s200: 100, atr: 2, avgAtr: 2, expected: "Strong_Bearish" },
  { c: 94, s50: 95, s200: 100, atr: 3, avgAtr: 2, expected: "Bearish" },
  { c: 102, s50: 105, s200: 100, atr: 2, avgAtr: 2, expected: "Mixed" },
];

console.log("=== Testing Detailed Market Regimes ===");
testCases.forEach((tc, index) => {
  const result = determineRegimeDetailed(tc.c, tc.s50, tc.s200, tc.atr, tc.avgAtr);
  console.log(`Test ${index + 1}: Expected '${tc.expected}', Got '${result}'`);
  if (result !== tc.expected) {
    throw new Error(`Test ${index + 1} failed!`);
  }
});
console.log("All regime classifications verified successfully!");

module.exports = { determineRegimeDetailed };
