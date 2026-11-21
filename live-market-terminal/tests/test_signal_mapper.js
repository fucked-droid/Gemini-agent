/**
 * Unit Test for SignalMapper (Node.js runner).
 * Tests mapping dictionary, edge cases, action classification, 5 signal states,
 * Market Intelligence indicators, and key watch levels.
 */

const assert = require('assert');
const SignalMapper = require('../static/signal_mapper.js');

console.log('Testing SignalMapper...');

// 1. Test Human-Readable Label Mapping (No Raw SNAKE_CASE)
assert.strictEqual(
    SignalMapper.formatEnumLabel('CAPITAL_PRESERVATION'),
    'Capital Preservation Mode',
    'CAPITAL_PRESERVATION must map to Capital Preservation Mode'
);

assert.strictEqual(
    SignalMapper.formatEnumLabel('STRUCTURAL_SWING_PULLBACK'),
    'Pullback in Uptrend',
    'STRUCTURAL_SWING_PULLBACK must map to Pullback in Uptrend'
);

assert.strictEqual(
    SignalMapper.formatEnumLabel('BULLISH_ORDER_BLOCK_RETEST'),
    'Bullish Order Block Retest'
);

assert.strictEqual(
    SignalMapper.formatEnumLabel('NEUTRAL_CONSOLIDATION'),
    'Neutral Consolidation'
);

// 2. Test Classification for All 5 Signal States
// A. STRONG BUY
const strongBuySig = SignalMapper.classifySignal({
    decision: 'BUY',
    clean_recommendation: 'STRONG BUY',
    confidence_pct: 88.0,
});
assert.strictEqual(strongBuySig.recommendation, 'STRONG BUY');
assert.strictEqual(strongBuySig.hasValidSetup, true);
assert.strictEqual(strongBuySig.badgeColorClass, 'text-green');
assert.strictEqual(strongBuySig.themeColor, '#00e676');
assert.strictEqual(strongBuySig.confidence, 88);

// B. BUY
const buySig = SignalMapper.classifySignal({
    decision: 'BUY',
    clean_recommendation: 'BUY',
    confidence_pct: 72.0,
});
assert.strictEqual(buySig.recommendation, 'BUY');
assert.strictEqual(buySig.hasValidSetup, true);
assert.strictEqual(buySig.badgeColorClass, 'text-green');

// C. WAIT FOR CONFIRMATION (Default Wait State)
const waitSig = SignalMapper.classifySignal({
    decision: 'WAIT',
    clean_recommendation: 'WAIT FOR CONFIRMATION',
    confidence_pct: 50.0,
});
assert.strictEqual(waitSig.recommendation, 'WAIT FOR CONFIRMATION');
assert.strictEqual(waitSig.hasValidSetup, false);
assert.strictEqual(waitSig.badgeColorClass, 'text-yellow');
assert.strictEqual(waitSig.themeColor, '#ffd600');

// D. SELL
const sellSig = SignalMapper.classifySignal({
    decision: 'SELL',
    clean_recommendation: 'SELL',
    confidence_pct: 68.0,
});
assert.strictEqual(sellSig.recommendation, 'SELL');
assert.strictEqual(sellSig.hasValidSetup, true);
assert.strictEqual(sellSig.badgeColorClass, 'text-red');

// E. STRONG SELL
const strongSellSig = SignalMapper.classifySignal({
    decision: 'SELL',
    clean_recommendation: 'STRONG SELL',
    confidence_pct: 85.0,
});
assert.strictEqual(strongSellSig.recommendation, 'STRONG SELL');
assert.strictEqual(strongSellSig.hasValidSetup, true);
assert.strictEqual(strongSellSig.badgeColorClass, 'text-red');
assert.strictEqual(strongSellSig.themeColor, '#ff1744');

// 3. Test Market Intelligence Resolvers
// Market Structure (Bullish / Bearish / Neutral)
assert.strictEqual(SignalMapper.resolveMarketStructure({ market_structure: { structure_state: 'BULLISH_EXPANSION' } }).label, 'Bullish');
assert.strictEqual(SignalMapper.resolveMarketStructure({ market_structure: { structure_state: 'BEARISH_EXPANSION' } }).label, 'Bearish');
assert.strictEqual(SignalMapper.resolveMarketStructure({ market_structure: { structure_state: 'NEUTRAL_CONSOLIDATION' } }).label, 'Neutral');

// VWAP Position (Above VWAP / Below VWAP / At VWAP)
assert.strictEqual(SignalMapper.resolveVwapPosition(25200.0, 25000.0).label, 'Above VWAP');
assert.strictEqual(SignalMapper.resolveVwapPosition(24800.0, 25000.0).label, 'Below VWAP');
assert.strictEqual(SignalMapper.resolveVwapPosition(25002.0, 25000.0).label, 'At VWAP');

// Order Flow (Buyers Dominating / Sellers Dominating / Balanced)
assert.strictEqual(SignalMapper.resolveOrderFlow({ buyer_percentage: 58.0 }).label, 'Buyers Dominating');
assert.strictEqual(SignalMapper.resolveOrderFlow({ buyer_percentage: 42.0 }).label, 'Sellers Dominating');
assert.strictEqual(SignalMapper.resolveOrderFlow({ buyer_percentage: 50.0 }).label, 'Balanced');

// Options Sentiment (Bullish / Bearish / Neutral / Unavailable)
assert.strictEqual(SignalMapper.resolveOptionsSentiment({ sentiment: 'Bullish' }, 'NIFTY').label, 'Bullish');
assert.strictEqual(SignalMapper.resolveOptionsSentiment({ sentiment: 'Bearish' }, 'BANKNIFTY').label, 'Bearish');
assert.strictEqual(SignalMapper.resolveOptionsSentiment({ sentiment: 'Neutral' }, 'NIFTY').label, 'Neutral');
assert.strictEqual(SignalMapper.resolveOptionsSentiment({ sentiment: 'Bullish' }, 'UNKNOWN').label, 'Bullish');
assert.strictEqual(SignalMapper.resolveOptionsSentiment(null, 'NIFTY').label, 'Unavailable');

// 4. Test Key Watch Levels
const watchLevels = SignalMapper.resolveKeyWatchLevels({
    spot_price: 24150.0,
    bullish_reclaim_trigger: 24200.0,
    downside_liquidity_zone: 24080.0,
}, 24150.0);

assert.strictEqual(watchLevels.bullishReclaimTrigger, 24200.0);
assert.strictEqual(watchLevels.downsideLiquidityZone, 24080.0);
assert.strictEqual(watchLevels.tradeStatus, 'Execution Locked — Waiting for Confirmation');
assert.strictEqual(watchLevels.positionSizing, '0% (100% Cash)');

// 4B. Test Market Closed Execution Lock
const watchLevelsClosed = SignalMapper.resolveKeyWatchLevels({
    spot_price: 24150.0,
    bullish_reclaim_trigger: 24200.0,
    downside_liquidity_zone: 24080.0,
}, 24150.0, true);
assert.strictEqual(watchLevelsClosed.tradeStatus, 'Execution Locked (Market Closed)');

// 5. Test 5 Required Signal Consistency Scenarios
// Case 1: Neutral market with no confirmed signal
const neutralCase = SignalMapper.classifySignal({
    decision: 'WAIT',
    clean_recommendation: 'WAIT FOR CONFIRMATION',
    confidence_pct: null,
});
assert.strictEqual(neutralCase.recommendation, 'WAIT FOR CONFIRMATION');
assert.strictEqual(neutralCase.hasValidSetup, false);

// Case 2: Confirmed bullish signal
const bullishCase = SignalMapper.classifySignal({
    decision: 'BUY',
    clean_recommendation: 'BUY',
    confidence_pct: 78.0,
});
assert.strictEqual(bullishCase.recommendation, 'BUY');
assert.strictEqual(bullishCase.hasValidSetup, true);
assert.strictEqual(bullishCase.confidence, 78);

// Case 3: Confirmed bearish signal
const bearishCase = SignalMapper.classifySignal({
    decision: 'SELL',
    clean_recommendation: 'STRONG SELL',
    confidence_pct: 88.0,
});
assert.strictEqual(bearishCase.recommendation, 'STRONG SELL');
assert.strictEqual(bearishCase.hasValidSetup, true);
assert.strictEqual(bearishCase.confidence, 88);

// Case 4: Market closed with historical data
const closedHistoricalCase = SignalMapper.classifySignal({
    decision: 'EXECUTION LOCKED',
    clean_recommendation: 'EXECUTION LOCKED',
    confidence_pct: 0,
});
assert.strictEqual(closedHistoricalCase.recommendation, 'EXECUTION LOCKED');
assert.strictEqual(closedHistoricalCase.hasValidSetup, false);

// Case 5: Missing or invalid signal inputs
const missingInputsCase = SignalMapper.classifySignal({});
assert.strictEqual(missingInputsCase.recommendation, 'WAIT FOR CONFIRMATION');
assert.strictEqual(missingInputsCase.hasValidSetup, false);

console.log('All SignalMapper 5-state and intelligence unit tests PASSED successfully!');
