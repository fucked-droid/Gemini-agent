from dataclasses import dataclass, field
from typing import List, Optional
from src.models.ipo_schema import IPOProfile, PeerComparison


@dataclass
class ValuationAnalysisResult:
    implied_market_cap_crores: float
    implied_pe: float
    industry_pe_median: float
    valuation_premium_pct: float       # Positive means IPO is more expensive than peers
    peg_ratio: float                   # PE / PAT CAGR
    valuation_status: str              # "DEEP_DISCOUNT", "FAIR_VALUE", "RICHLY_PRICED", "EXORBITANT_PREMIUM"
    score: float                       # 0 to 100
    strengths: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)


def analyze_valuation(profile: IPOProfile, pat_cagr: float) -> ValuationAnalysisResult:
    """Evaluates IPO pricing relative to sector peers, earnings growth, and implied multiples."""
    meta = profile.meta
    issue = profile.issue_structure
    peers = profile.peers
    latest_pat = profile.financials[-1].pat_crores if profile.financials else 0.0

    # Estimate Implied Market Cap:
    # Public post-issue stake % = 100 - promoter_post_holding_pct
    public_stake_pct = max(5.0, 100.0 - issue.promoter_post_holding_pct)
    implied_mcap = round((meta.issue_size_crores / (public_stake_pct / 100.0)), 2) if public_stake_pct > 0 else 0.0

    # Implied P/E
    implied_pe = 0.0
    if latest_pat > 0 and implied_mcap > 0:
        implied_pe = round(implied_mcap / latest_pat, 2)
    elif latest_pat <= 0:
        implied_pe = 999.0  # Loss-making IPO

    # Industry PE median
    ind_pe = peers.industry_pe_median
    if ind_pe <= 0 and peers.peers:
        valid_pes = [p.pe_ratio for p in peers.peers if p.pe_ratio > 0]
        if valid_pes:
            valid_pes.sort()
            mid = len(valid_pes) // 2
            ind_pe = valid_pes[mid] if len(valid_pes) % 2 != 0 else (valid_pes[mid - 1] + valid_pes[mid]) / 2.0
    ind_pe = round(ind_pe, 2)

    # Premium / Discount vs Peers
    val_premium_pct = 0.0
    if ind_pe > 0 and implied_pe > 0 and implied_pe < 900:
        val_premium_pct = round(((implied_pe - ind_pe) / ind_pe) * 100.0, 2)

    # PEG Ratio
    peg = 0.0
    if pat_cagr > 0 and implied_pe > 0 and implied_pe < 900:
        peg = round(implied_pe / pat_cagr, 2)

    # Valuation Status & Scoring
    strengths = []
    red_flags = []
    score = 50.0

    if implied_pe >= 900:
        val_status = "EXORBITANT_PREMIUM"
        score = 10.0
        red_flags.append("Loss-making IPO: Asking for multi-hundred crore valuation with negative earnings.")
    elif val_premium_pct <= -25.0:
        val_status = "DEEP_DISCOUNT"
        score += 35.0
        strengths.append(f"Significant margin of safety: Priced at a {abs(val_premium_pct)}% discount to peer median (P/E {implied_pe} vs Peer {ind_pe}).")
    elif val_premium_pct <= 0.0:
        val_status = "FAIR_VALUE"
        score += 20.0
        strengths.append(f"Fairly priced: At or slightly below listed peer median (P/E {implied_pe} vs Peer {ind_pe}).")
    elif val_premium_pct <= 25.0:
        val_status = "RICHLY_PRICED"
        score -= 5.0
        strengths.append(f"Slight growth premium: Priced {val_premium_pct}% above peers (P/E {implied_pe}).")
    elif val_premium_pct <= 60.0:
        val_status = "RICHLY_PRICED"
        score -= 20.0
        red_flags.append(f"Expensive pricing: Promoters demanding {val_premium_pct}% premium over established peers (P/E {implied_pe} vs Peer {ind_pe}).")
    else:
        val_status = "EXORBITANT_PREMIUM"
        score -= 35.0
        red_flags.append(f"Extreme greed valuation: Trading at {val_premium_pct}% premium to sector peers (P/E {implied_pe} vs Peer {ind_pe}).")

    # PEG checks
    if 0.0 < peg <= 1.2:
        score += 15.0
        strengths.append(f"Undervalued on growth: PEG ratio is {peg}x (< 1.2 indicates high earnings justification).")
    elif peg > 2.5:
        score -= 15.0
        red_flags.append(f"Poor growth justification: PEG ratio is {peg}x (> 2.0 indicates price is running far ahead of earnings growth).")

    score = max(0.0, min(100.0, round(score, 1)))

    return ValuationAnalysisResult(
        implied_market_cap_crores=implied_mcap,
        implied_pe=implied_pe,
        industry_pe_median=ind_pe,
        valuation_premium_pct=val_premium_pct,
        peg_ratio=peg,
        valuation_status=val_status,
        score=score,
        strengths=strengths,
        red_flags=red_flags
    )
