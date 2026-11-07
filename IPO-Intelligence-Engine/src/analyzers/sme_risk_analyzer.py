from dataclasses import dataclass, field
from typing import List, Optional
from src.models.ipo_schema import IPOProfile, SMERiskMetrics, ExchangeCategory


@dataclass
class SMERiskResult:
    is_sme: bool
    customer_concentration_risk: str   # "LOW", "MODERATE", "CRITICAL"
    top_3_revenue_pct: float
    debtor_days: float
    working_capital_days: float
    lot_size_capital_inr: float        # lot_size * issue_price
    score: float                       # 0 to 100
    strengths: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)


def analyze_sme_risk(profile: IPOProfile) -> SMERiskResult:
    """Evaluates specialized operational, concentration, and liquidity risks for SME exchange listings."""
    is_sme = profile.meta.category in (ExchangeCategory.SME_NSE, ExchangeCategory.SME_BSE)
    sme = profile.sme_metrics

    lot_cap = round(profile.meta.lot_size * profile.meta.issue_price, 2)

    if not is_sme or not sme:
        return SMERiskResult(
            is_sme=False,
            customer_concentration_risk="LOW",
            top_3_revenue_pct=0.0,
            debtor_days=0.0,
            working_capital_days=0.0,
            lot_size_capital_inr=lot_cap,
            score=100.0,
            strengths=["Mainboard listing provides standard institutional disclosure and high liquidity."],
            red_flags=[]
        )

    score = 60.0
    strengths = []
    red_flags = []

    # 1. Customer Concentration Risk
    top3 = sme.top_3_clients_revenue_pct
    top5 = sme.top_5_clients_revenue_pct

    if top3 > 65.0 or top5 > 80.0:
        conc_risk = "CRITICAL"
        score -= 25.0
        red_flags.append(f"Severe Client Concentration: Top 3 clients contribute {top3}% of total revenue (Loss of 1 client poses existential threat).")
    elif top3 > 45.0 or top5 > 65.0:
        conc_risk = "MODERATE"
        score -= 10.0
        red_flags.append(f"Moderate Client Concentration: Top 3 clients contribute {top3}% of revenue.")
    else:
        conc_risk = "LOW"
        score += 15.0
        strengths.append(f"Diversified client base: Top 3 clients contribute only {top3}% of total revenue.")

    # 2. Debtor Days & Working Capital
    if sme.debtor_days > 120.0:
        score -= 15.0
        red_flags.append(f"Stretched Receivable Cycle: High debtor days ({sme.debtor_days} days) indicates weak bargaining power with buyers.")
    elif sme.debtor_days <= 60.0:
        score += 10.0
        strengths.append(f"Disciplined collections: Debtor days are lean at {sme.debtor_days} days.")

    if sme.working_capital_days > 150.0:
        score -= 15.0
        red_flags.append(f"High working capital drag: Working capital cycle is {sme.working_capital_days} days.")

    # 3. Liquidity & Ticket Size Friction
    if lot_cap >= 120000:
        red_flags.append(f"High Retail Barrier: Minimum investment per lot is ₹{lot_cap:,.0f} with 2-way market maker spread (~{sme.market_maker_spread_pct}%).")

    score = max(0.0, min(100.0, round(score, 1)))

    return SMERiskResult(
        is_sme=True,
        customer_concentration_risk=conc_risk,
        top_3_revenue_pct=top3,
        debtor_days=sme.debtor_days,
        working_capital_days=sme.working_capital_days,
        lot_size_capital_inr=lot_cap,
        score=score,
        strengths=strengths,
        red_flags=red_flags
    )
