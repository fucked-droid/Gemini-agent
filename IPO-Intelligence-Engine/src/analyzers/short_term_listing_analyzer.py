from dataclasses import dataclass, field
from typing import List, Dict, Any
from src.models.ipo_schema import IPOProfile, ExchangeCategory


@dataclass
class ListingExitPlaybook:
    expected_listing_price_inr: float
    expected_gain_pct: float
    expected_profit_per_lot_inr: float
    pre_open_action: str              # 9:00 - 9:08 AM IST
    market_open_sell_rule: str        # 9:15 AM IST
    circuit_freeze_strategy: str      # Upper circuit (5% or 20%) rule
    emergency_bailout_rule: str       # If opening below expected GMP


@dataclass
class ShortTermListingResult:
    gmp_inr: float
    gmp_pct: float
    gmp_trend: str
    qib_subscription: float
    nii_subscription: float
    retail_subscription: float
    total_subscription: float
    anchor_quality: str
    expected_listing_price: float
    expected_gain_pct: float
    expected_profit_per_lot_inr: float
    listing_score: float              # 0 to 100
    playbook: ListingExitPlaybook
    strengths: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)


def analyze_short_term_listing(profile: IPOProfile) -> ShortTermListingResult:
    """Evaluates short-term listing gain potential, grey market momentum, institutional subscription rush, and generates a T+0 exit playbook."""
    meta = profile.meta
    st = profile.short_term

    issue_price = meta.issue_price
    lot_size = meta.lot_size
    gmp = st.gmp_inr

    # 1. GMP % over issue price
    gmp_pct = round((gmp / issue_price * 100.0), 2) if issue_price > 0 else 0.0
    expected_listing_price = round(issue_price + gmp, 2)
    expected_profit_lot = round(gmp * lot_size, 2)

    score = 40.0  # Base
    strengths = []
    red_flags = []

    # 2. GMP Score Contribution
    if gmp_pct >= 40.0:
        score += 30.0
        strengths.append(f"Explosive Grey Market Premium: Current GMP is ₹{gmp:,.1f} (+{gmp_pct}% over issue price).")
    elif gmp_pct >= 20.0:
        score += 20.0
        strengths.append(f"Healthy Listing Premium: Current GMP is ₹{gmp:,.1f} (+{gmp_pct}%).")
    elif gmp_pct >= 8.0:
        score += 5.0
        strengths.append(f"Moderate Listing Premium: GMP is ₹{gmp:,.1f} (+{gmp_pct}%). Thin cushion.")
    elif gmp_pct <= 0.0:
        score -= 30.0
        red_flags.append(f"Zero/Negative GMP Warning: Grey market premium is ₹{gmp:,.1f} ({gmp_pct}%). High probability of opening at a discount.")
    else:
        score -= 15.0
        red_flags.append(f"Weak GMP: Only +{gmp_pct}% premium. Vulnerable to market open slippage.")

    # 3. GMP Trend Momentum
    if st.gmp_trend == "RISING":
        score += 10.0
        strengths.append("Rising GMP Momentum: Grey market rates are actively expanding into bidding close.")
    elif st.gmp_trend == "FALLING":
        score -= 20.0
        red_flags.append("Deteriorating GMP Trend: Grey market premium is declining as listing approaches (Smart money exiting).")

    # 4. QIB Institutional Rush (The Master Listing Engine)
    qib = st.qib_subscription_times
    if qib >= 50.0:
        score += 25.0
        strengths.append(f"Blockbuster Institutional Frenzy: QIB category subscribed {qib}x times (FII/DII aggressive bidding).")
    elif qib >= 20.0:
        score += 15.0
        strengths.append(f"Strong Institutional Backing: QIB subscription is {qib}x times.")
    elif qib >= 5.0:
        score += 5.0
        strengths.append(f"Adequate QIB participation: {qib}x subscribed.")
    elif qib < 2.0:
        score -= 25.0
        red_flags.append(f"Institutional Rejection: QIB book barely subscribed ({qib}x). Low post-listing institutional buying support.")

    # 5. HNI / NII Subscription & Break-Even Margin
    nii = st.nii_subscription_times
    if nii >= 40.0:
        score += 10.0
        strengths.append(f"High HNI demand: NII category subscribed {nii}x times.")
    elif nii < 2.0:
        score -= 10.0
        red_flags.append(f"Tepid HNI interest: NII category only {nii}x subscribed.")

    # 6. Float & Size Dynamics
    is_sme = meta.category in (ExchangeCategory.SME_NSE, ExchangeCategory.SME_BSE)
    if is_sme and gmp_pct >= 25.0:
        score += 10.0
        strengths.append("SME Circuit Squeeze Potential: Micro float allows high probability of multiple Upper Circuit locks.")
    elif meta.issue_size_crores > 7500.0:
        score -= 10.0
        red_flags.append(f"Heavy Supply Float: Mega issue size (₹{meta.issue_size_crores:,.0f} Cr) limits immediate listing day surge.")

    # 7. Anchor Quality
    if st.anchor_quality == "TIER_1_MARQUEE":
        score += 5.0
        strengths.append("Top-Tier Anchor Book: Allocated to marquee domestic mutual funds and sovereign funds.")
    elif st.anchor_quality == "WEAK":
        score -= 10.0
        red_flags.append("Uncertain Anchor Book: Dominated by low-reputation entities.")

    score = max(0.0, min(100.0, round(score, 1)))

    # 8. Synthesize Concrete T+0 Exit Playbook
    if score >= 70.0:
        pre_open = "Monitor indicative matching price between 9:00 - 9:08 AM. Ensure opening tick meets or exceeds ₹" + f"{expected_listing_price:,.1f}."
        market_open = "Place PRE-OPEN LIMIT SELL or MARKET SELL at 9:15 AM to lock in 100% allotment profit within the first 15 minutes."
        circuit_rule = (
            "If price freezes in UPPER CIRCUIT (e.g. +5% for SME or +20% for Mainboard) with massive pending buy orders: "
            "Hold with a trailing stop-loss at opening price. Exit immediately if circuit unfreezes!"
        )
        emergency_rule = "If opening below expected GMP (e.g. < ₹" + f"{(issue_price + gmp * 0.5):,.1f}): Dump immediately at market open."
    elif score >= 50.0:
        pre_open = "Check 9:00 AM pre-open order book depth. If bids are thinning out, prepare early sell order."
        market_open = "Sell 100% quantity right at the 9:15 AM opening bell. Do not wait for intra-day recovery."
        circuit_rule = "Do not expect sustained circuit locks. Book immediate quick flip profit."
        emergency_rule = "Strict cut-loss: If opening near or below issue price (₹" + f"{issue_price:,.1f}), exit instantly to protect capital."
    else:
        pre_open = "High risk of opening flat or in the red."
        market_open = "STRICT AVOID / IMMEDIATE BAILOUT: Exit all shares at 9:15 AM opening tick. Do not baghold!"
        circuit_rule = "High danger of Lower Circuit freeze. Get out at pre-open."
        emergency_rule = "Place market order to salvage capital before post-open dump."

    playbook = ListingExitPlaybook(
        expected_listing_price_inr=expected_listing_price,
        expected_gain_pct=gmp_pct,
        expected_profit_per_lot_inr=expected_profit_lot,
        pre_open_action=pre_open,
        market_open_sell_rule=market_open,
        circuit_freeze_strategy=circuit_rule,
        emergency_bailout_rule=emergency_rule
    )

    return ShortTermListingResult(
        gmp_inr=gmp,
        gmp_pct=gmp_pct,
        gmp_trend=st.gmp_trend,
        qib_subscription=qib,
        nii_subscription=nii,
        retail_subscription=st.retail_subscription_times,
        total_subscription=st.total_subscription_times,
        anchor_quality=st.anchor_quality,
        expected_listing_price=expected_listing_price,
        expected_gain_pct=gmp_pct,
        expected_profit_per_lot_inr=expected_profit_lot,
        listing_score=score,
        playbook=playbook,
        strengths=strengths,
        red_flags=red_flags
    )
