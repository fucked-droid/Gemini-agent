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
    """Renders a beautifully structured ANSI terminal report optimized for short-term listing gain & exit."""
    # Banner color
    if eval_res.verdict == VerdictTier.APPLY_LISTING_POP:
        banner_color = GREEN
    elif eval_res.verdict == VerdictTier.APPLY_SPECULATIVE:
        banner_color = CYAN
    elif eval_res.verdict == VerdictTier.AVOID_LOW_GAIN:
        banner_color = YELLOW
    else:
        banner_color = RED

    pb = eval_res.playbook
    st = eval_res.short_term_res

    lines = []
    lines.append(f"{banner_color}{BOLD}================================================================================{RESET}")
    lines.append(f"{banner_color}{BOLD}     ⚡  SHORT-TERM IPO LISTING GAIN & QUICK PROFIT EXIT REPORT  ⚡{RESET}")
    lines.append(f"{banner_color}{BOLD}================================================================================{RESET}")
    lines.append(f"{BOLD}Company Name    :{RESET} {WHITE}{eval_res.company_name} ({eval_res.symbol}){RESET}")
    lines.append(f"{BOLD}Segment/Exchange:{RESET} {CYAN}{eval_res.category}{RESET} | {BOLD}Issue Price:{RESET} ₹{eval_res.issue_price:,.2f}")
    lines.append(f"{BOLD}Lot Size / Cost :{RESET} {eval_res.lot_size} shares (Min Investment: {BOLD}₹{eval_res.lot_cost_inr:,.0f}{RESET})")
    lines.append(f"{banner_color}--------------------------------------------------------------------------------{RESET}")
    lines.append(f"{BOLD}LISTING GAIN SCORE :{RESET} {banner_color}{BOLD}{eval_res.composite_score} / 100{RESET}")
    lines.append(f"{BOLD}APPLICATION VERDICT:{RESET} {banner_color}{BOLD}{eval_res.verdict_title}{RESET}")
    lines.append(f"{banner_color}--------------------------------------------------------------------------------{RESET}")

    # Core Short-Term Metrics
    gain_color = GREEN if eval_res.expected_gain_pct >= 20 else (YELLOW if eval_res.expected_gain_pct >= 10 else RED)
    lines.append(f"{BOLD}🎯 EXPECTED LISTING GAIN:{RESET} {gain_color}{BOLD}+{eval_res.expected_gain_pct}%{RESET} (Target: ₹{eval_res.expected_listing_price:,.1f})")
    lines.append(f"{BOLD}💰 ESTIMATED PROFIT/LOT :{RESET} {GREEN if eval_res.expected_profit_per_lot_inr > 0 else RED}{BOLD}₹{eval_res.expected_profit_per_lot_inr:,.0f}{RESET}")
    lines.append(f"{BOLD}📊 CURRENT GMP          :{RESET} ₹{st.gmp_inr:,.1f} ({st.gmp_trend} Trend)")
    lines.append(f"{BOLD}🏛️ QIB SUBSCRIPTION     :{RESET} {GREEN if st.qib_subscription >= 20 else (YELLOW if st.qib_subscription >= 5 else RED)}{st.qib_subscription}x times{RESET} (Total: {st.total_subscription}x)")
    lines.append(f"{banner_color}--------------------------------------------------------------------------------{RESET}")

    # The Trader's Listing Day Exit Playbook
    lines.append(f"{BOLD}⏰ LISTING DAY (T+0) SHORT-TERM EXIT PLAYBOOK:{RESET}")
    lines.append(f"  {CYAN}1. [9:00 - 9:08 AM Pre-Open]{RESET} : {pb.pre_open_action}")
    lines.append(f"  {GREEN}2. [9:15 AM Market Open]{RESET}     : {BOLD}{pb.market_open_sell_rule}{RESET}")
    lines.append(f"  {YELLOW}3. [Upper Circuit Rule]{RESET}      : {pb.circuit_freeze_strategy}")
    lines.append(f"  {RED}4. [Emergency Bail-out]{RESET}      : {pb.emergency_bailout_rule}")
    lines.append(f"{banner_color}--------------------------------------------------------------------------------{RESET}")

    # Quick Fundamental Safety Floor Check
    f = eval_res.financial_res
    v = eval_res.valuation_res
    g = eval_res.governance_res
    lines.append(f"{BOLD}🛡️ FUNDAMENTAL SAFETY FLOOR CHECK:{RESET}")
    lines.append(f"   • Financial Health  : 3-Yr Rev CAGR {f.revenue_cagr_pct}% | ROCE {f.latest_roce_pct}% | D/E {f.latest_debt_to_equity}x")
    cfo_txt = "Healthy Positive" if not f.negative_cfo_flag else "NEGATIVE CFO WARNING"
    lines.append(f"   • Cash Quality      : {GREEN if not f.negative_cfo_flag else RED}{cfo_txt} (CFO/PAT {f.cfo_to_pat_ratio}x){RESET}")
    lines.append(f"   • Peer Valuation    : Implied P/E {v.implied_pe}x vs Peer {v.industry_pe_median}x ({v.valuation_status})")
    lines.append(f"   • Issue Capital     : {g.fresh_issue_pct}% Fresh Issue / {g.ofs_pct}% OFS (Promoter Post: {g.promoter_post_holding_pct}%)")

    # Key Catalysts & Risks
    lines.append(f"\n{GREEN}{BOLD}✨ KEY LISTING CATALYSTS:{RESET}")
    for st_text in eval_res.key_strengths[:4]:
        lines.append(f"   {GREEN}✔{RESET} {st_text}")

    lines.append(f"\n{RED}{BOLD}⚠️ SHORT-TERM RISKS & TRAPS:{RESET}")
    if eval_res.key_risks:
        for rf in eval_res.key_risks[:4]:
            lines.append(f"   {RED}✖{RESET} {rf}")
    else:
        lines.append(f"   {GREEN}✔ Zero listing risks detected.{RESET}")

    lines.append(f"{banner_color}{BOLD}================================================================================{RESET}\n")
    return "\n".join(lines)
