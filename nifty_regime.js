/**
 * Nifty Daily Market Regime Engine
 * 
 * Classifies market regimes based on price trends, volatility, and momentum indicators.
 */

function calculateSMA(data, period) {
  const result = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null);
      continue;
    }
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j];
    }
    result.push(sum / period);
  }
  return result;
}

function calculateATR(highs, lows, closes, period = 14) {
  const tr = [];
  for (let i = 0; i < closes.length; i++) {
    if (i === 0) {
      tr.push(highs[i] - lows[i]);
    } else {
      const hl = highs[i] - lows[i];
      const hc = Math.abs(highs[i] - closes[i - 1]);
      const lc = Math.abs(lows[i] - closes[i - 1]);
      tr.push(Math.max(hl, hc, lc));
    }
  }
  return calculateSMA(tr, period);
}

function determineRegime(close, sma50, sma200, atr, avgAtr) {
  if (close > sma50 && sma50 > sma200 && atr < avgAtr * 1.5) {
    return "Strong Bullish Trend";
  } else if (close < sma50 && sma50 < sma200 && atr < avgAtr * 1.5) {
    return "Strong Bearish Trend";
  } else if (atr >= avgAtr * 1.5) {
    return "High Volatility / Panic Regime";
  } else {
    return "Sideways / Range-Bound";
  }
}

// Sample Nifty Daily Simulation Data & Verification
const sampleCloses = [22000, 22100, 22250, 22400, 22350, 22500, 22700, 22800, 22900, 23000, 23100, 23200, 23300, 23400, 23500];
const sampleHighs = sampleCloses.map(c => c + 100);
const sampleLows = sampleCloses.map(c => c - 100);

console.log("=== Nifty Daily Market Regime Engine Checkpoint ===");
const sma50 = calculateSMA(sampleCloses, 5); // Using smaller period for sample demo
const sma200 = calculateSMA(sampleCloses, 10);
const atr = calculateATR(sampleHighs, sampleLows, sampleCloses, 5);
const avgAtr = atr[atr.length - 1];

const currentRegime = determineRegime(
  sampleCloses[sampleCloses.length - 1],
  sma50[sma50.length - 1],
  sma200[sma200.length - 1],
  atr[atr.length - 1],
  avgAtr
);

console.log(`Current Market Regime: ${currentRegime}`);
module.exports = { calculateSMA, calculateATR, determineRegime };
