import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.models.ipo_schema import FinancialYear


@dataclass
class FinancialAnalysisResult:
    revenue_cagr_pct: float
    pat_cagr_pct: float
    latest_revenue_crores: float
    latest_pat_crores: float
    latest_ebitda_margin_pct: float
    ebitda_margin_trend: str          # "EXPANDING", "STABLE", "CONTRACTING"
    latest_roce_pct: float
    latest_ronw_pct: float
    latest_debt_to_equity: float
    cfo_to_pat_ratio: float           # Cash flow conversion: CFO / PAT
    negative_cfo_flag: bool
    score: float                      # 0 to 100
    strengths: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)


def analyze_financials(financials: List[FinancialYear]) -> FinancialAnalysisResult:
    """Audits 3-year historical financial performance and computes fundamental metrics."""
    if not financials:
        return FinancialAnalysisResult(
            revenue_cagr_pct=0.0,
            pat_cagr_pct=0.0,
            latest_revenue_crores=0.0,
            latest_pat_crores=0.0,
            latest_ebitda_margin_pct=0.0,
            ebitda_margin_trend="UNKNOWN",
            latest_roce_pct=0.0,
            latest_ronw_pct=0.0,
            latest_debt_to_equity=0.0,
            cfo_to_pat_ratio=0.0,
            negative_cfo_flag=True,
            score=0.0,
            strengths=[],
            red_flags=["No financial history provided in prospectus."]
        )

    # Sort by year or assume ordered
    n_years = len(financials)
    first = financials[0]
    latest = financials[-1]

    # 1. Revenue CAGR
    rev_cagr = 0.0
    if n_years > 1 and first.revenue_crores > 0 and latest.revenue_crores > 0:
        periods = n_years - 1
        rev_cagr = ((latest.revenue_crores / first.revenue_crores) ** (1.0 / periods) - 1.0) * 100.0
    elif n_years == 1:
        rev_cagr = 0.0
    rev_cagr = round(rev_cagr, 2)

    # 2. PAT CAGR
    pat_cagr = 0.0
    if n_years > 1 and first.pat_crores > 0 and latest.pat_crores > 0:
        periods = n_years - 1
        pat_cagr = ((latest.pat_crores / first.pat_crores) ** (1.0 / periods) - 1.0) * 100.0
    elif n_years > 1 and (first.pat_crores <= 0 or latest.pat_crores <= 0):
        # Loss to profit or profit to loss
        if latest.pat_crores > first.pat_crores:
            pat_cagr = 99.0  # Turnaround from loss
        else:
            pat_cagr = -99.0  # Slipping into loss
    pat_cagr = round(pat_cagr, 2)

    # 3. EBITDA Margins & Trend
    first_margin = (first.ebitda_crores / first.revenue_crores * 100.0) if first.revenue_crores > 0 else 0.0
    latest_margin = (latest.ebitda_crores / latest.revenue_crores * 100.0) if latest.revenue_crores > 0 else 0.0
    latest_margin = round(latest_margin, 2)

    margin_diff = latest_margin - first_margin
    if margin_diff > 1.5:
        margin_trend = "EXPANDING"
    elif margin_diff < -1.5:
        margin_trend = "CONTRACTING"
    else:
        margin_trend = "STABLE"

    # 4. Capital Efficiency (ROCE / RoNW)
    latest_roce = latest.roce_pct if latest.roce_pct is not None else 0.0
    latest_ronw = latest.ronw_pct if latest.ronw_pct is not None else 0.0
    if latest_roce == 0.0 and (latest.net_worth_crores + latest.total_debt_crores) > 0:
        capital_employed = latest.net_worth_crores + latest.total_debt_crores
        latest_roce = round((latest.ebitda_crores / capital_employed) * 100.0, 2)
    if latest_ronw == 0.0 and latest.net_worth_crores > 0:
        latest_ronw = round((latest.pat_crores / latest.net_worth_crores) * 100.0, 2)

    # 5. Debt to Equity
    latest_de = 0.0
    if latest.net_worth_crores > 0:
        latest_de = round(latest.total_debt_crores / latest.net_worth_crores, 2)

    # 6. Cash Flow Conversion: Total CFO vs Total PAT over all years
    tot_cfo = sum(f.cfo_crores for f in financials)
    tot_pat = sum(f.pat_crores for f in financials)
    negative_cfo = tot_cfo <= 0 or latest.cfo_crores <= 0

    cfo_pat_ratio = 0.0
    if tot_pat > 0:
        cfo_pat_ratio = round(tot_cfo / tot_pat, 2)
    elif tot_pat < 0 and tot_cfo > 0:
        cfo_pat_ratio = 1.0  # Positive cash flow despite accounting losses

    # Scoring computation (0 to 100)
    score = 50.0  # Baseline
    strengths = []
    red_flags = []

    # Growth Score
    if rev_cagr >= 25.0:
        score += 15.0
        strengths.append(f"High top-line momentum: 3-Yr Revenue CAGR is {rev_cagr}%.")
    elif rev_cagr >= 15.0:
        score += 8.0
        strengths.append(f"Healthy top-line growth: 3-Yr Revenue CAGR is {rev_cagr}%.")
    elif rev_cagr < 5.0:
        score -= 10.0
        red_flags.append(f"Stagnant revenue growth: 3-Yr Revenue CAGR is only {rev_cagr}%.")

    if pat_cagr >= 25.0:
        score += 15.0
        strengths.append(f"Robust earnings expansion: 3-Yr PAT CAGR is {pat_cagr}%.")
    elif pat_cagr < 0.0:
        score -= 15.0
        red_flags.append(f"Earnings contraction: 3-Yr PAT CAGR is negative ({pat_cagr}%).")

    # Capital Efficiency Score
    if latest_roce >= 20.0 or latest_ronw >= 20.0:
        score += 10.0
        strengths.append(f"Superior capital efficiency: ROCE {latest_roce}%, RoNW {latest_ronw}%.")
    elif latest_roce < 10.0 and latest_ronw < 10.0:
        score -= 10.0
        red_flags.append(f"Poor capital efficiency: ROCE ({latest_roce}%) & RoNW ({latest_ronw}%) below cost of capital.")

    # Earnings Quality & Cash Flow
    if negative_cfo:
        score -= 25.0
        red_flags.append(f"Earnings Quality Warning: Bleeding operating cash flow (CFO is negative: {latest.cfo_crores} Cr).")
    elif cfo_pat_ratio >= 0.75:
        score += 10.0
        strengths.append(f"High earnings cash conversion: CFO/PAT ratio is {cfo_pat_ratio}x (real cash profits).")
    elif cfo_pat_ratio < 0.4:
        score -= 10.0
        red_flags.append(f"Weak cash conversion: CFO/PAT ratio is only {cfo_pat_ratio}x (working capital locked in receivables).")

    # Solvency & Debt
    if latest_de <= 0.3:
        score += 5.0
        strengths.append(f"Pristine balance sheet: Debt-to-Equity is virtually zero ({latest_de}x).")
    elif latest_de > 1.5:
        score -= 15.0
        red_flags.append(f"Leverage risk: High Debt-to-Equity of {latest_de}x ({latest.total_debt_crores} Cr debt).")

    # Clamp score
    score = max(0.0, min(100.0, round(score, 1)))

    return FinancialAnalysisResult(
        revenue_cagr_pct=rev_cagr,
        pat_cagr_pct=pat_cagr,
        latest_revenue_crores=latest.revenue_crores,
        latest_pat_crores=latest.pat_crores,
        latest_ebitda_margin_pct=latest_margin,
        ebitda_margin_trend=margin_trend,
        latest_roce_pct=latest_roce,
        latest_ronw_pct=latest_ronw,
        latest_debt_to_equity=latest_de,
        cfo_to_pat_ratio=cfo_pat_ratio,
        negative_cfo_flag=negative_cfo,
        score=score,
        strengths=strengths,
        red_flags=red_flags
    )
