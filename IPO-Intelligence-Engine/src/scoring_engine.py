from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.models.ipo_schema import IPOProfile, VerdictTier, ExchangeCategory
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
    financial_res: FinancialAnalysisResult
    valuation_res: ValuationAnalysisResult
    governance_res: GovernanceAnalysisResult
    sme_res: SMERiskResult
    key_strengths: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)
    suggested_action: str = ""


def evaluate_ipo(profile: IPOProfile) -> FundamentalEvaluation:
    """Runs end-to-end fundamental audit across all four pillars and produces an institutional verdict."""
    # 1. Run all analyzers
    fin_res = analyze_financials(profile.financials)
    val_res = analyze_valuation(profile, fin_res.pat_cagr_pct)
    gov_res = analyze_governance_and_structure(profile)
    sme_res = analyze_sme_risk(profile)

    is_sme = profile.meta.category in (ExchangeCategory.SME_NSE, ExchangeCategory.SME_BSE)

    # 2. Weighted Score Synthesis
    if is_sme:
        # 30% Financial, 25% Valuation, 25% Governance, 20% SME Risk
        raw_score = (
            fin_res.score * 0.30 +
            val_res.score * 0.25 +
            gov_res.score * 0.25 +
            sme_res.score * 0.20
        )
    else:
        # 40% Financial, 35% Valuation, 25% Governance
        raw_score = (
            fin_res.score * 0.40 +
            val_res.score * 0.35 +
            gov_res.score * 0.25
        )

    composite_score = round(raw_score, 1)

    # 3. Institutional Hard Veto Overrides
    hard_veto_applied = False
    veto_reason = ""

    # Rule 1: Cash flow trap with heavy OFS
    if fin_res.negative_cfo_flag and gov_res.ofs_pct >= 70.0:
        composite_score = min(composite_score, 35.0)
        hard_veto_applied = True
        veto_reason = "VETO OVERRIDE: Bleeding operating cash flow combined with >70% OFS exit."

    # Rule 2: Auditor qualification / serious accounting doubt
    if gov_res.auditor_qualification_flag:
        composite_score = min(composite_score, 45.0)
        hard_veto_applied = True
        veto_reason = "VETO OVERRIDE: Adverse remarks / qualification by statutory auditors."

    # Rule 3: High promoter share pledge
    if gov_res.promoter_pledge_pct > 25.0:
        composite_score = min(composite_score, 40.0)
        hard_veto_applied = True
        veto_reason = f"VETO OVERRIDE: Dangerous promoter share pledge ({gov_res.promoter_pledge_pct}%)."

    # Rule 4: Extreme greed valuation (> 100% premium over peer group)
    if val_res.valuation_premium_pct > 100.0:
        composite_score = min(composite_score, 48.0)
        hard_veto_applied = True
        veto_reason = f"VETO OVERRIDE: Exorbitant greed premium (+{val_res.valuation_premium_pct}% vs peers)."

    # 4. Map Score to Verdict Tier
    if composite_score >= 75.0:
        verdict = VerdictTier.STRONG_BUY
        verdict_title = "💎 LONG-TERM COMPOUNDER (STRONG BUY)"
        rec_summary = (
            f"{profile.meta.company_name} demonstrates exceptional capital efficiency (ROCE {fin_res.latest_roce_pct}%), "
            f"positive cash conversion, and disciplined peer valuation. High long-term compounder potential."
        )
        suggested_action = "Apply with high conviction for portfolio allocation. Add aggressively if market dips post-listing."
    elif composite_score >= 60.0:
        verdict = VerdictTier.BUY_ON_DIPS
        verdict_title = "📈 CONDITIONAL BUY (WAIT FOR POST-LISTING DIP)"
        rec_summary = (
            f"Solid underlying business with {fin_res.revenue_cagr_pct}% revenue CAGR, but IPO valuation is fully priced "
            f"leaving thin initial margin of safety. Worth owning at better entry multiples."
        )
        suggested_action = "Avoid chasing at listing peak. Set price alerts for post-listing lock-in expiry or market cool-off."
    elif composite_score >= 45.0:
        verdict = VerdictTier.SPECULATIVE
        verdict_title = "⚠️ SPECULATIVE / HIGH RISK"
        rec_summary = (
            f"Mixed risk profile. While revenue growth is visible, concerns in client concentration or "
            f"balance sheet leverage warrant caution."
        )
        suggested_action = "High-risk appetite only. Position sizing must be strictly limited."
    else:
        verdict = VerdictTier.AVOID_TRAP
        verdict_title = "🛑 AVOID / PROMOTER CASH-OUT TRAP"
        rec_summary = (
            f"Capital preservation alert. Characterized by {gov_res.ofs_pct}% OFS exit, negative operating cash flows, "
            f"or excessive valuation premium. Poor risk-reward for retail investors."
        )
        suggested_action = "Strictly AVOID. Do not risk hard-earned capital on speculative euphoria."

    # 5. Compile Strengths & Risks
    all_strengths = fin_res.strengths + val_res.strengths + gov_res.strengths + sme_res.strengths
    all_risks = fin_res.red_flags + val_res.red_flags + gov_res.red_flags + sme_res.red_flags

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
        financial_res=fin_res,
        valuation_res=val_res,
        governance_res=gov_res,
        sme_res=sme_res,
        key_strengths=all_strengths,
        key_risks=all_risks,
        suggested_action=suggested_action
    )
