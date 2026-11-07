import sys
from src.scoring_engine import FundamentalEvaluation
from src.models.ipo_schema import VerdictTier

# Terminal ANSI Colors
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"


def format_cli_report(eval_res: FundamentalEvaluation) -> str:
    """Renders a beautifully structured ANSI terminal report for fundamental IPO evaluation."""
    # Choose banner color based on verdict
    if eval_res.verdict == VerdictTier.STRONG_BUY:
        banner_color = GREEN
    elif eval_res.verdict == VerdictTier.BUY_ON_DIPS:
        banner_color = CYAN
    elif eval_res.verdict == VerdictTier.SPECULATIVE:
        banner_color = YELLOW
    else:
        banner_color = RED

    lines = []
    lines.append(f"{banner_color}{BOLD}================================================================================{RESET}")
    lines.append(f"{banner_color}{BOLD}        🏛️  INSTITUTIONAL IPO FUNDAMENTAL EVALUATION REPORT  🏛️{RESET}")
    lines.append(f"{banner_color}{BOLD}================================================================================{RESET}")
    lines.append(f"{BOLD}Company Name    :{RESET} {WHITE}{eval_res.company_name} ({eval_res.symbol}){RESET}")
    lines.append(f"{BOLD}Segment/Exchange:{RESET} {CYAN}{eval_res.category}{RESET} | {BOLD}Issue Price:{RESET} ₹{eval_res.issue_price:,.2f}")
    lines.append(f"{BOLD}Lot Size / Cost :{RESET} {eval_res.lot_size} shares (Min Investment: {BOLD}₹{eval_res.lot_cost_inr:,.0f}{RESET})")
    lines.append(f"{banner_color}--------------------------------------------------------------------------------{RESET}")
    lines.append(f"{BOLD}COMPOSITE SCORE :{RESET} {banner_color}{BOLD}{eval_res.composite_score} / 100{RESET}")
    lines.append(f"{BOLD}FINAL VERDICT   :{RESET} {banner_color}{BOLD}{eval_res.verdict_title}{RESET}")
    lines.append(f"{banner_color}--------------------------------------------------------------------------------{RESET}")
    lines.append(f"{BOLD}Executive Summary:{RESET}")
    lines.append(f"  {eval_res.recommendation_summary}")
    lines.append(f"{BOLD}Action Playbook  :{RESET}")
    lines.append(f"  {banner_color}👉 {eval_res.suggested_action}{RESET}")
    lines.append(f"{banner_color}--------------------------------------------------------------------------------{RESET}")

    # Section 1: Financial Health
    f = eval_res.financial_res
    lines.append(f"{BOLD}1. 📊 FINANCIAL HEALTH & GROWTH ENGINE (Score: {f.score}/100){RESET}")
    lines.append(f"   • 3-Year Revenue CAGR : {GREEN if f.revenue_cagr_pct >= 15 else YELLOW}{f.revenue_cagr_pct}%{RESET}")
    lines.append(f"   • 3-Year PAT CAGR     : {GREEN if f.pat_cagr_pct >= 15 else RED}{f.pat_cagr_pct}%{RESET}")
    lines.append(f"   • Latest Revenue / PAT: ₹{f.latest_revenue_crores:,.1f} Cr / ₹{f.latest_pat_crores:,.1f} Cr")
    lines.append(f"   • Operating Margin    : {f.latest_ebitda_margin_pct}% ({f.ebitda_margin_trend})")
    lines.append(f"   • Capital Efficiency  : ROCE {GREEN if f.latest_roce_pct >= 20 else YELLOW}{f.latest_roce_pct}%{RESET} | RoNW {f.latest_ronw_pct}%")
    lines.append(f"   • Balance Sheet D/E   : {GREEN if f.latest_debt_to_equity <= 0.5 else RED}{f.latest_debt_to_equity}x{RESET}")
    cfo_color = RED if f.negative_cfo_flag else GREEN
    lines.append(f"   • Cash Flow Conversion: {cfo_color}{f.cfo_to_pat_ratio}x (CFO vs PAT){RESET}")

    # Section 2: Valuation
    v = eval_res.valuation_res
    lines.append(f"\n{BOLD}2. 🏷️ VALUATION & PEER BENCHMARKING (Score: {v.score}/100){RESET}")
    lines.append(f"   • Implied Post-Issue P/E : {WHITE}{v.implied_pe}x{RESET}")
    lines.append(f"   • Sector Peer Median P/E : {CYAN}{v.industry_pe_median}x{RESET}")
    prem_color = GREEN if v.valuation_premium_pct <= 0 else (YELLOW if v.valuation_premium_pct <= 25 else RED)
    prem_sign = "+" if v.valuation_premium_pct > 0 else ""
    lines.append(f"   • Premium / Discount vs Peers: {prem_color}{prem_sign}{v.valuation_premium_pct}% ({v.valuation_status}){RESET}")
    lines.append(f"   • PEG (Price/Earnings Growth): {v.peg_ratio}x")

    # Section 3: Issue Structure & Governance
    g = eval_res.governance_res
    lines.append(f"\n{BOLD}3. 🏛️ ISSUE STRUCTURE & GOVERNANCE (Score: {g.score}/100){RESET}")
    fresh_col = GREEN if g.fresh_issue_pct >= 70 else (YELLOW if g.fresh_issue_pct >= 40 else RED)
    lines.append(f"   • Fresh Issue vs OFS  : {fresh_col}{g.fresh_issue_pct}% Fresh Issue{RESET} / {g.ofs_pct}% OFS")
    lines.append(f"   • Post-Issue Promoter : {g.promoter_post_holding_pct}% skin in the game")
    pledge_col = GREEN if g.promoter_pledge_pct == 0 else RED
    lines.append(f"   • Promoter Share Pledge: {pledge_col}{g.promoter_pledge_pct}%{RESET}")
    lines.append(f"   • Legal Contingencies : {g.litigation_to_networth_pct}% of Net Worth")

    # Section 4: SME Specifics (if applicable)
    if eval_res.sme_res.is_sme:
        s = eval_res.sme_res
        conc_col = GREEN if s.customer_concentration_risk == "LOW" else (YELLOW if s.customer_concentration_risk == "MODERATE" else RED)
        lines.append(f"\n{BOLD}4. 🏭 SME OPERATIONAL & LIQUIDITY RISK (Score: {s.score}/100){RESET}")
        lines.append(f"   • Client Concentration: {conc_col}{s.top_3_revenue_pct}% in Top 3 Clients ({s.customer_concentration_risk}){RESET}")
        lines.append(f"   • Debtor Days         : {s.debtor_days} days | Working Capital: {s.working_capital_days} days")
        lines.append(f"   • Min Ticket Size     : ₹{s.lot_size_capital_inr:,.0f} per lot")

    # Section 5: Key Moats & Strengths
    lines.append(f"\n{GREEN}{BOLD}✨ KEY MOATS & STRENGTHS:{RESET}")
    for st in eval_res.key_strengths[:5]:
        lines.append(f"   {GREEN}✔{RESET} {st}")

    # Section 6: Key Red Flags
    lines.append(f"\n{RED}{BOLD}⚠️ CRITICAL RED FLAGS & RISKS:{RESET}")
    if eval_res.key_risks:
        for rf in eval_res.key_risks[:5]:
            lines.append(f"   {RED}✖{RESET} {rf}")
    else:
        lines.append(f"   {GREEN}✔ None identified. Clean operational track record.{RESET}")

    lines.append(f"{banner_color}{BOLD}================================================================================{RESET}\n")
    return "\n".join(lines)
