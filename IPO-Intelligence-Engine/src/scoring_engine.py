from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.models.ipo_schema import IPOProfile, VerdictTier, ExchangeCategory
from src.analyzers.short_term_listing_analyzer import (
    analyze_short_term_listing, ShortTermListingResult, ListingExitPlaybook
)
from src.analyzers.financial_analyzer import analyze_financials, FinancialAnalysisResult
from src.analyzers.valuation_analyzer import analyze_valuation, ValuationAnalysisResult
from src.analyzers.governance_issue_analyzer import analyze_governance_and_structure, GovernanceAnalysisResult
from src.analyzers.sme_risk_analyzer import analyze_sme_risk, SMERiskResult


@dataclass
class FundamentalEvaluation:
    company_name: str
    symbol: str
    category: str
    issue_price: float
    lot_size: int
    lot_cost_inr: float
    composite_score: float
    verdict: VerdictTier
    verdict_title: str
    recommendation_summary: str
    expected_listing_price: float
    expected_gain_pct: float
    expected_profit_per_lot_inr: float
    playbook: ListingExitPlaybook
    short_term_res: ShortTermListingResult
    financial_res: FinancialAnalysisResult
    valuation_res: ValuationAnalysisResult
    governance_res: GovernanceAnalysisResult
    sme_res: SMERiskResult
    status: str = "SAMPLE"
    open_date: str = ""
    listing_date: str = ""
    key_strengths: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)
    suggested_action: str = ""


def evaluate_ipo(profile: IPOProfile) -> FundamentalEvaluation:
    """Runs a dedicated short-term listing gain evaluation to optimize profit booking and quick exits."""
    # 1. Run all analyzers
    st_res = analyze_short_term_listing(profile)
    fin_res = analyze_financials(profile.financials)
    val_res = analyze_valuation(profile, fin_res.pat_cagr_pct)
    gov_res = analyze_governance_and_structure(profile)
    sme_res = analyze_sme_risk(profile)

    is_sme = profile.meta.category in (ExchangeCategory.SME_NSE, ExchangeCategory.SME_BSE)

    # 2. Short-Term Priority Weighted Score:
    # 55% Short-Term GMP/QIB, 15% Valuation, 15% Financial Safety Floor, 15% Governance/SME
    if is_sme:
        raw_score = (
            st_res.listing_score * 0.55 +
            val_res.score * 0.15 +
            fin_res.score * 0.15 +
            sme_res.score * 0.15
        )
    else:
        raw_score = (
            st_res.listing_score * 0.55 +
            val_res.score * 0.15 +
            fin_res.score * 0.15 +
            gov_res.score * 0.15
        )

    composite_score = round(raw_score, 1)

    # 3. Institutional Hard Veto Overrides for Short-Term
    hard_veto_applied = False
    veto_reason = ""

    # Rule 1: Zero or Negative GMP with poor QIB subscription
    if st_res.gmp_pct <= 0.0 and st_res.qib_subscription < 3.0:
        composite_score = min(composite_score, 25.0)
        hard_veto_applied = True
        veto_reason = "VETO OVERRIDE: Zero/Negative GMP combined with weak institutional bidding (< 3x)."

    # Rule 2: Deteriorating falling GMP into listing date
    if st_res.gmp_trend == "FALLING" and st_res.gmp_pct < 10.0:
        composite_score = min(composite_score, 38.0)
        hard_veto_applied = True
        veto_reason = "VETO OVERRIDE: Falling GMP trend (< 10%) indicates high danger of listing day discount."

    # Rule 3: Severe Accounting / Governance Red Flag (Statutory qualification)
    if gov_res.auditor_qualification_flag:
        composite_score = min(composite_score, 40.0)
        hard_veto_applied = True
        veto_reason = "VETO OVERRIDE: Auditor qualifications could trigger opening panic."

    # 4. Map Score to Short-Term Verdict Tier
    if composite_score >= 75.0:
        verdict = VerdictTier.APPLY_LISTING_POP
        verdict_title = "🚀 APPLY FOR LISTING POP (STRONG BUY & QUICK EXIT)"
        rec_summary = (
            f"High-conviction listing gain opportunity. Expected opening pop of +{st_res.expected_gain_pct}% "
            f"(~₹{st_res.expected_listing_price:,.1f}), delivering approximately ₹{st_res.expected_profit_per_lot_inr:,.0f} "
            f"profit per lot. Driven by {st_res.qib_subscription}x QIB subscription and strong grey market demand."
        )
        suggested_action = (
            f"APPLY in retail/HNI category. On listing day at 9:15 AM, execute {st_res.playbook.market_open_sell_rule}"
        )
    elif composite_score >= 55.0:
        verdict = VerdictTier.APPLY_SPECULATIVE
        verdict_title = "⚡ APPLY FOR SPECULATIVE FLIP (CALCULATED RISK)"
        rec_summary = (
            f"Moderate listing pop expected (+{st_res.expected_gain_pct}%). Estimated profit ₹{st_res.expected_profit_per_lot_inr:,.0f} per lot. "
            f"Decent demand cushion, but requires strict pre-open selling discipline."
        )
        suggested_action = "Apply with calculated allocation. Sell 100% quantity right at 9:15 AM open."
    elif composite_score >= 40.0:
        verdict = VerdictTier.AVOID_LOW_GAIN
        verdict_title = "✋ AVOID / LOW LISTING GAIN (POOR REWARD-TO-RISK)"
        rec_summary = (
            f"Thin margin of safety (expected gain only +{st_res.expected_gain_pct}%). Tepid institutional rush "
            f"({st_res.qib_subscription}x QIB) means capital could be blocked for negligible returns."
        )
        suggested_action = "AVOID. Better to deploy funds into stronger IPOs or secondary market opportunities."
    else:
        verdict = VerdictTier.AVOID_DISCOUNT_TRAP
        verdict_title = "🛑 STRICT AVOID / LISTING DISCOUNT TRAP"
        rec_summary = (
            f"Severe capital erosion danger. Current GMP is ₹{st_res.gmp_inr} ({st_res.gmp_pct}%). "
            f"High risk of opening below the ₹{profile.meta.issue_price:,.1f} issue price."
        )
        suggested_action = "DO NOT APPLY. High probability of immediate listing losses."

    # 5. Compile Strengths & Risks
    all_strengths = st_res.strengths + fin_res.strengths + val_res.strengths + gov_res.strengths + sme_res.strengths
    all_risks = st_res.red_flags + fin_res.red_flags + val_res.red_flags + gov_res.red_flags + sme_res.red_flags

    if hard_veto_applied:
        all_risks.insert(0, veto_reason)

    lot_cost = round(profile.meta.lot_size * profile.meta.issue_price, 2)

    return FundamentalEvaluation(
        company_name=profile.meta.company_name,
        symbol=profile.meta.symbol,
        category=profile.meta.category.value,
        issue_price=profile.meta.issue_price,
        lot_size=profile.meta.lot_size,
        lot_cost_inr=lot_cost,
        composite_score=composite_score,
        verdict=verdict,
        verdict_title=verdict_title,
        recommendation_summary=rec_summary,
        expected_listing_price=st_res.expected_listing_price,
        expected_gain_pct=st_res.expected_gain_pct,
        expected_profit_per_lot_inr=st_res.expected_profit_per_lot_inr,
        playbook=st_res.playbook,
        short_term_res=st_res,
        financial_res=fin_res,
        valuation_res=val_res,
        governance_res=gov_res,
        sme_res=sme_res,
        status=profile.status,
        open_date=profile.meta.open_date,
        listing_date=profile.meta.listing_date,
        key_strengths=all_strengths,
        key_risks=all_risks,
        suggested_action=suggested_action
    )
