import os
import urllib.request
import urllib.parse
import json
from src.scoring_engine import FundamentalEvaluation
from src.models.ipo_schema import VerdictTier


def format_telegram_ipo_alert(eval_res: FundamentalEvaluation) -> str:
    """Formats an institutional fundamental evaluation for Telegram mobile alerts."""
    if eval_res.verdict == VerdictTier.STRONG_BUY:
        icon = "💎"
        tier_str = "LONG-TERM COMPOUNDER (STRONG BUY)"
    elif eval_res.verdict == VerdictTier.BUY_ON_DIPS:
        icon = "📈"
        tier_str = "CONDITIONAL BUY (ACCUMULATE ON DIPS)"
    elif eval_res.verdict == VerdictTier.SPECULATIVE:
        icon = "⚠️"
        tier_str = "SPECULATIVE / HIGH RISK"
    else:
        icon = "🛑"
        tier_str = "AVOID / PROMOTER TRAP"

    f = eval_res.financial_res
    v = eval_res.valuation_res
    g = eval_res.governance_res
    s = eval_res.sme_res

    prem_sign = "+" if v.valuation_premium_pct > 0 else ""

    msg = [
        f"{icon} *IPO FUNDAMENTAL INTELLIGENCE | {eval_res.category}*",
        f"🏢 *{eval_res.company_name}* (`{eval_res.symbol}`)",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🎯 *VERDICT*: *{tier_str}*",
        f"📊 *FUNDAMENTAL SCORE*: `{eval_res.composite_score} / 100`",
        f"💰 *Price Band*: `₹{eval_res.issue_price:,.2f}` | *Lot*: `{eval_res.lot_size} shares` (₹{eval_res.lot_cost_inr:,.0f})",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📍 *INVESTMENT THESIS*:",
        f"_{eval_res.recommendation_summary}_",
        f"",
        f"👉 *STRATEGY*: {eval_res.suggested_action}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🔍 *CORE PILLAR AUDIT*:",
        f"• *Growth*: 3-Yr Rev CAGR `{f.revenue_cagr_pct}%` | PAT CAGR `{f.pat_cagr_pct}%`",
        f"• *Efficiency*: ROCE `{f.latest_roce_pct}%` | RoNW `{f.latest_ronw_pct}%`",
        f"• *Cash Quality*: CFO/PAT Ratio `{f.cfo_to_pat_ratio}x` | D/E `{f.latest_debt_to_equity}x`",
        f"• *Valuation*: Implied P/E `{v.implied_pe}x` vs Peer `{v.industry_pe_median}x` ({prem_sign}{v.valuation_premium_pct}%)",
        f"• *Structure*: Fresh `{g.fresh_issue_pct}%` / OFS `{g.ofs_pct}%` | Promoter `{g.promoter_post_holding_pct}%`",
    ]

    if s.is_sme:
        msg.append(f"• *SME Risk*: Top 3 Clients `{s.top_3_revenue_pct}%` | Debtors `{s.debtor_days}d`")

    msg.append("")
    msg.append("✨ *KEY MOATS*:")
    for st in eval_res.key_strengths[:3]:
        msg.append(f"• {st}")

    msg.append("")
    msg.append("⚠️ *KEY RISKS*:")
    if eval_res.key_risks:
        for rf in eval_res.key_risks[:3]:
            msg.append(f"• {rf}")
    else:
        msg.append("• No critical governance or financial red flags detected.")

    msg.append("")
    msg.append("🛡️ *LONG-TERM DISCIPLINE*:")
    msg.append("_Invest in businesses with high ROCE and honest promoters. Avoid overpaying at IPO peaks._")

    return "\n".join(msg)


def send_telegram_alert(message: str, bot_token: str = None, chat_id: str = None) -> bool:
    """Dispatches Telegram alert to user's Telegram channel or chat."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Telegram Bot Error] {e}")
        return False
