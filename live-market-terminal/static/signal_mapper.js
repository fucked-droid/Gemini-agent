/**
 * Live Indian Market Terminal — Signal Mapper & Display Formatting Engine.
 * Converts backend enum states, raw uppercase strings, and SMC tags
 * into institutional-grade human-readable display labels and safe visual states.
 */

(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.SignalMapper = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {

    const SIGNAL_LABEL_MAP = {
        // Core Actions & Recommendations (Strict 5-State Support)
        'STRONG BUY': 'STRONG BUY',
        'BUY': 'BUY',
        'WAIT FOR CONFIRMATION': 'WAIT FOR CONFIRMATION',
        'SELL': 'SELL',
        'STRONG SELL': 'STRONG SELL',

        // Human-Readable Mappings
        'ACTIVE_LONG': 'STRONG BUY',
        'ACTIVE_SHORT': 'STRONG SELL',
        'STRONG_BUY': 'STRONG BUY',
        'STRONG_SELL': 'STRONG SELL',
        'BUY_ON_PULLBACK': 'BUY',
        'WAIT': 'WAIT FOR CONFIRMATION',
        'AVOID_SHORT': 'STAND ASIDE — DO NOT SHORT',
        'AVOID_LONG': 'STAND ASIDE — DO NOT LONG',
        'CAPITAL_PRESERVATION': 'Capital Preservation Mode',
        'AVOID_SHORT (CAPITAL_PRESERVATION)': 'STAND ASIDE — DO NOT SHORT',
        'STAND_ASIDE': 'STAND ASIDE',

        // Execution Types
        'FIXED_STRUCTURAL_ENTRY': 'Fixed Structural Entry',
        'PULLBACK_REQUIRED': 'Pullback Required (Limit Entry)',
        'CAPITAL_SHIELD_ACTIVE': 'Capital Preservation Shield Active',
        'SHORT_CONTINUATION': 'Short Continuation Entry',
        'NO_ENTRY_CHOP': 'No Entry — Range Consolidation',

        // Smart Money Concepts (SMC) Setup Types
        'STRUCTURAL_SWING_PULLBACK': 'Pullback in Uptrend',
        'BULLISH_ORDER_BLOCK_RETEST': 'Bullish Order Block Retest',
        'BEARISH_ORDER_BLOCK_RETEST': 'Bearish Order Block Retest',
        'BULLISH_FVG_RETEST': 'Bullish Fair Value Gap Retest',
        'BEARISH_FVG_RETEST': 'Bearish Fair Value Gap Retest',
        'FAIR_VALUE_GAP_FILL': 'Fair Value Gap Retest',
        'LIQUIDITY_SWEEP_REVERSAL': 'Liquidity Sweep Reversal',
        'BULLISH_LIQUIDITY_SWEEP': 'Bullish Liquidity Sweep',
        'BEARISH_LIQUIDITY_SWEEP': 'Bearish Liquidity Sweep',
        'TECHNICAL_STRUCTURE': 'Technical Structure Aligned',
        'STRUCTURE_ALIGNED': 'Structure Aligned',
        'SMC: STRUCTURE ALIGNED': 'Structure Aligned',
        'SMC: DETECTING STRUCTURE': 'Detecting Structure',
        'NO_SMC_SETUP': 'Awaiting Setup Structure',

        // Market Regimes & Trends
        'BULLISH_EXPANSION': 'Bullish Expansion',
        'BEARISH_EXPANSION': 'Bearish Expansion',
        'NEUTRAL_CONSOLIDATION': 'Neutral Consolidation',
        'STRONG_BULLISH': 'Strong Bullish',
        'BULLISH': 'Bullish',
        'NEUTRAL_BULLISH': 'Neutral Bullish',
        'SIDEWAYS': 'Sideways / Range',
        'NEUTRAL_BEARISH': 'Neutral Bearish',
        'BEARISH': 'Bearish',
        'STRONG_BEARISH': 'Strong Bearish',
        'CHOP': 'Chop / Range',
        'BOS_BULLISH_CONTINUATION': 'Break of Structure (Bullish Continuation)',
        'BOS_BEARISH_CONTINUATION': 'Break of Structure (Bearish Continuation)',
        'CHOCH_BULLISH_REVERSAL': 'Change of Character (Bullish Reversal)',
        'CHOCH_BEARISH_REVERSAL': 'Change of Character (Bearish Reversal)',

        // Order Flow & Divergences
        'AGGRESSIVE_BUYING': 'Aggressive Buying',
        'ABSORPTION_BUYING': 'Absorption Buying',
        'NEUTRAL': 'Neutral',
        'ABSORPTION_SELLING': 'Absorption Selling',
        'AGGRESSIVE_SELLING': 'Aggressive Selling',
        'NEUTRAL_CHOP_FLOW': 'Neutral Range Flow',
        'NO_DIVERGENCE': 'No Divergence',
        'BULLISH_ABSORPTION': 'Bullish Absorption',
        'BEARISH_ABSORPTION': 'Bearish Absorption',
        'BULLISH_DIVERGENCE': 'Bullish Divergence',
        'BEARISH_DIVERGENCE': 'Bearish Divergence',

        // Reversal Threats
        'LOW': 'Low Risk',
        'MODERATE': 'Moderate Risk',
        'HIGH': 'High Risk',

        // Trade Status & Position Sizing
        'EXECUTION_LOCKED': 'Execution Locked',
        'EXECUTION_PERMITTED': 'Execution Permitted',
        'CASH_ONLY': '0% (100% Cash)',
    };

    /**
     * Format Price helper to never display ₹NaN or undefined
     */
    function formatPrice(val, prefix = '₹', decimals = 2) {
        if (val === null || val === undefined || val === '') return '--';
        const num = Number(val);
        if (isNaN(num) || !isFinite(num)) return '--';
        return `${prefix}${num.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
    }

    /**
     * Converts any raw SNAKE_CASE or enum string into clean human-readable text.
     */
    function formatEnumLabel(value) {
        if (!value) return '';
        const str = String(value).trim();
        if (SIGNAL_LABEL_MAP[str]) return SIGNAL_LABEL_MAP[str];

        const upper = str.toUpperCase();
        if (SIGNAL_LABEL_MAP[upper]) return SIGNAL_LABEL_MAP[upper];

        if (upper === 'BROADENING_RANGE') return 'Broadening Range';
        if (upper === 'COMPRESSION_TRIANGLE') return 'Compression Triangle';
        if (upper === 'VOLATILITY_EXPANSION') return 'Range Expanding (No Breakout)';
        if (upper === 'BULLISH_EXPANSION_BREAKOUT') return 'Bullish Breakout Confirmed';
        if (upper === 'BEARISH_EXPANSION_BREAKDOWN') return 'Bearish Breakdown Confirmed';
        if (upper === 'TRIANGLE_UPPER_BREAKOUT') return 'Ascending Breakout Confirmed';
        if (upper === 'TRIANGLE_LOWER_BREAKDOWN') return 'Descending Breakdown Confirmed';
        if (upper === 'RANGE_CONTRACTION') return 'Range Contracting (No Breakout)';

        if (upper.includes('AVOID_SHORT') || upper.includes('AVOID SHORT')) {
            return 'STAND ASIDE — DO NOT SHORT';
        }
        if (upper.includes('AVOID_LONG') || upper.includes('AVOID LONG')) {
            return 'STAND ASIDE — DO NOT LONG';
        }
        if (upper.includes('CAPITAL_PRESERVATION')) {
            return 'Capital Preservation Mode';
        }
        if (upper.includes('STRUCTURAL_SWING_PULLBACK')) {
            return 'Pullback in Uptrend';
        }
        if (upper.includes('WAIT')) {
            return 'WAIT FOR CONFIRMATION';
        }
        if (upper.startsWith('SMC:')) {
            const stripped = upper.replace(/^SMC:\s*/, '').trim();
            return formatEnumLabel(stripped);
        }

        // Generic cleaner: removes underscores, replaces parens, converts to clean title case
        return str
            .replace(/[()_]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim()
            .toLowerCase()
            .replace(/\b\w/g, c => c.toUpperCase());
    }

    /**
     * Classifies the signal strictly into the 5 target states:
     * - STRONG BUY (Green)
     * - BUY (Green)
     * - WAIT FOR CONFIRMATION (Yellow/Orange default)
     * - SELL (Red)
     * - STRONG SELL (Red)
     */
    function classifySignal(signals) {
        signals = signals || {};
        const rawDec = String(signals.decision || 'WAIT').trim().toUpperCase();
        const rawRec = String(signals.signal_recommendation || '').trim().toUpperCase();
        const rawExec = String(signals.execution_type || '').trim().toUpperCase();
        const cleanRecFromBackend = String(signals.clean_recommendation || '').trim().toUpperCase();

        const confidence = parseFloat(signals.confidence_pct != null ? signals.confidence_pct : 50);

        // Check if state is explicitly avoid/preserve/wait
        const isAvoidOrWait =
            rawDec.includes('AVOID') ||
            rawDec.includes('WAIT') ||
            rawDec.includes('CAPITAL_PRESERVATION') ||
            rawRec.includes('AVOID') ||
            rawRec.includes('WAIT') ||
            rawRec.includes('CAPITAL_PRESERVATION') ||
            rawExec.includes('CAPITAL_SHIELD') ||
            rawExec.includes('NO_ENTRY');

        let recommendation = 'WAIT FOR CONFIRMATION';
        let badgeColorClass = 'text-yellow';
        let themeColor = '#ffd600';
        let hasValidSetup = false;
        let actionState = 'STAND_ASIDE';

        if (cleanRecFromBackend === 'EXECUTION LOCKED' || rawDec === 'EXECUTION LOCKED') {
            return {
                recommendation: 'EXECUTION LOCKED',
                displayDecision: 'EXECUTION LOCKED',
                actionState: 'EXECUTION_LOCKED',
                isActiveTrade: false,
                hasValidSetup: false,
                badgeColorClass: 'text-cyan',
                themeColor: '#00e5ff',
                confidence: 0,
            };
        } else if (cleanRecFromBackend === 'DATA UNAVAILABLE' || rawDec === 'DATA UNAVAILABLE') {
            return {
                recommendation: 'DATA UNAVAILABLE',
                displayDecision: 'DATA UNAVAILABLE',
                actionState: 'DATA_UNAVAILABLE',
                isActiveTrade: false,
                hasValidSetup: false,
                badgeColorClass: 'text-muted',
                themeColor: '#8b949e',
                confidence: 0,
            };
        } else if (cleanRecFromBackend === 'STRONG BUY') {
            recommendation = 'STRONG BUY';
            badgeColorClass = 'text-green';
            themeColor = '#00e676';
            hasValidSetup = true;
            actionState = 'ACTIVE_LONG';
        } else if (cleanRecFromBackend === 'BUY') {
            recommendation = 'BUY';
            badgeColorClass = 'text-green';
            themeColor = '#00e676';
            hasValidSetup = true;
            actionState = 'ACTIVE_LONG';
        } else if (cleanRecFromBackend === 'STRONG SELL') {
            recommendation = 'STRONG SELL';
            badgeColorClass = 'text-red';
            themeColor = '#ff1744';
            hasValidSetup = true;
            actionState = 'ACTIVE_SHORT';
        } else if (cleanRecFromBackend === 'SELL') {
            recommendation = 'SELL';
            badgeColorClass = 'text-red';
            themeColor = '#ff1744';
            hasValidSetup = true;
            actionState = 'ACTIVE_SHORT';
        } else if (!isAvoidOrWait) {
            if (rawDec === 'BUY' || rawDec === 'ACTIVE_LONG' || rawDec.startsWith('BUY')) {
                recommendation = confidence >= 80 ? 'STRONG BUY' : 'BUY';
                badgeColorClass = 'text-green';
                themeColor = '#00e676';
                hasValidSetup = true;
                actionState = 'ACTIVE_LONG';
            } else if (rawDec === 'SELL' || rawDec === 'ACTIVE_SHORT' || rawDec.startsWith('SELL')) {
                recommendation = confidence >= 80 ? 'STRONG SELL' : 'SELL';
                badgeColorClass = 'text-red';
                themeColor = '#ff1744';
                hasValidSetup = true;
                actionState = 'ACTIVE_SHORT';
            }
        }

        if (!hasValidSetup) {
            recommendation = 'WAIT FOR CONFIRMATION';
            badgeColorClass = 'text-yellow';
            themeColor = '#ffd600';
            actionState = 'STAND_ASIDE';
        }

        return {
            recommendation,
            displayDecision: recommendation,
            actionState,
            isActiveTrade: hasValidSetup,
            hasValidSetup,
            badgeColorClass,
            themeColor,
            confidence: Math.round(confidence),
        };
    }

    /**
     * Resolves the Market Structure indicator (Bullish / Bearish / Neutral / Insufficient / Unavailable).
     */
    function resolveMarketStructure(analytics) {
        if (!analytics) return { label: 'Neutral', badgeClass: 'text-yellow' };
        const status = (analytics.market_structure && analytics.market_structure.status) ||
                       (analytics.smc && analytics.smc.status);
        if (status === 'INSUFFICIENT HISTORICAL DATA') {
            return { label: 'INSUFFICIENT HISTORICAL DATA', badgeClass: 'text-muted' };
        }
        if (status === 'UNAVAILABLE — INVALID INPUT DATA') {
            return { label: 'UNAVAILABLE — INVALID INPUT DATA', badgeClass: 'text-red' };
        }
        const ms = (analytics.market_structure && analytics.market_structure.structure_state) ||
                   (analytics.market_intelligence && analytics.market_intelligence.market_structure) ||
                   'NEUTRAL';
        const str = String(ms).toUpperCase();
        if (str.includes('INSUFFICIENT')) return { label: 'INSUFFICIENT HISTORICAL DATA', badgeClass: 'text-muted' };
        if (str.includes('UNAVAILABLE') || str.includes('INVALID')) return { label: 'UNAVAILABLE — INVALID INPUT DATA', badgeClass: 'text-red' };
        if (str.includes('BULLISH')) return { label: 'Bullish', badgeClass: 'text-green' };
        if (str.includes('BEARISH')) return { label: 'Bearish', badgeClass: 'text-red' };
        return { label: 'Neutral', badgeClass: 'text-yellow' };
    }

    /**
     * Resolves the VWAP Position indicator (Above VWAP / Below VWAP / At VWAP).
     */
    function resolveVwapPosition(spotPrice, vwapPrice) {
        const spot = parseFloat(spotPrice || 0);
        const vwap = parseFloat(vwapPrice || 0);
        if (vwap <= 0 || spot <= 0) {
            return { label: 'At VWAP', badgeClass: 'text-cyan', diffPct: 0 };
        }
        const diffPct = (spot - vwap) / vwap;
        if (diffPct > 0.0005) {
            return { label: 'Above VWAP', badgeClass: 'text-green', diffPct };
        } else if (diffPct < -0.0005) {
            return { label: 'Below VWAP', badgeClass: 'text-red', diffPct };
        }
        return { label: 'At VWAP', badgeClass: 'text-cyan', diffPct };
    }

    /**
     * Resolves Order Flow indicator (Buyers Dominating / Sellers Dominating / Balanced / Unavailable).
     * 50.0% BUY or CVD <= 0 must strictly classify as Balanced / Neutral.
     */
    function resolveOrderFlow(orderFlow) {
        if (!orderFlow || orderFlow.status === 'UNAVAILABLE' || orderFlow.is_cvd_available === false) {
            return { label: 'Unavailable', badgeClass: 'text-muted', buyerPct: 50.0 };
        }
        const buyerPct = parseFloat(orderFlow.buyer_percentage || 50.0);
        const sessionCvd = parseInt(orderFlow.session_cvd != null ? orderFlow.session_cvd : (orderFlow.cvd || 0), 10);
        const flowState = String(orderFlow.order_flow_state || '').toUpperCase();

        // Moderate or Strong Bullish requires actual evidence: buyerPct > 52 and positive CVD
        if ((buyerPct >= 52.0 && sessionCvd > 0) || (flowState.includes('STRONG_BULLISH') && sessionCvd > 0)) {
            return { label: 'Buyers Dominating', badgeClass: 'text-green', buyerPct };
        } else if ((buyerPct <= 48.0 && sessionCvd < 0) || (flowState.includes('STRONG_BEARISH') && sessionCvd < 0)) {
            return { label: 'Sellers Dominating', badgeClass: 'text-red', buyerPct };
        }
        return { label: 'Balanced', badgeClass: 'text-yellow', buyerPct };
    }

    /**
     * Resolves Options Sentiment indicator (Bullish / Bearish / Neutral / Unavailable).
     */
    function resolveOptionsSentiment(optData, activeSymbol) {
        if (!optData) return { label: 'Unavailable', badgeClass: 'text-muted' };
        const sent = String(optData.sentiment || optData.options_sentiment || optData.sentiment_label || 'Unavailable').trim();
        const upper = sent.toUpperCase();
        if (upper === 'POSITIVE' || upper === 'BULLISH') return { label: 'Bullish', badgeClass: 'text-green' };
        if (upper === 'NEGATIVE' || upper === 'BEARISH') return { label: 'Bearish', badgeClass: 'text-red' };
        if (upper === 'NEUTRAL' || upper === 'NEUTRAL/RANGEBOUND' || upper === 'RANGEBOUND') return { label: 'Neutral', badgeClass: 'text-yellow' };
        return { label: 'Unavailable', badgeClass: 'text-muted' };
    }

    /**
     * Resolves Key Watch Levels when waiting for confirmation.
     */
    function resolveKeyWatchLevels(signals, spotPrice, isMarketClosed = false) {
        signals = signals || {};
        const spot = parseFloat(spotPrice || signals.spot_price || 0);

        let reclaimTrigger = signals.bullish_reclaim_trigger;
        if (!reclaimTrigger || reclaimTrigger <= 0) {
            if (signals.stop_loss && signals.stop_loss > spot) {
                reclaimTrigger = signals.stop_loss;
            } else if (spot > 0) {
                reclaimTrigger = spot * 1.002;
            } else {
                reclaimTrigger = 0;
            }
        }

        let liquidityZone = signals.downside_liquidity_zone;
        if (!liquidityZone || liquidityZone <= 0) {
            if (signals.target_1 && signals.target_1 < spot && signals.target_1 > 0) {
                liquidityZone = signals.target_1;
            } else if (spot > 0) {
                liquidityZone = spot * 0.995;
            } else {
                liquidityZone = 0;
            }
        }

        const tradeStatus = isMarketClosed
            ? 'Execution Locked (Market Closed)'
            : 'Execution Locked — Waiting for Confirmation';

        return {
            bullishReclaimTrigger: parseFloat(reclaimTrigger),
            downsideLiquidityZone: parseFloat(liquidityZone),
            tradeStatus: tradeStatus,
            positionSizing: '0% (100% Cash)',
        };
    }

    return {
        SIGNAL_LABEL_MAP,
        formatEnumLabel,
        formatPrice,
        classifySignal,
        resolveMarketStructure,
        resolveVwapPosition,
        resolveOrderFlow,
        resolveOptionsSentiment,
        resolveKeyWatchLevels,
    };
}));
