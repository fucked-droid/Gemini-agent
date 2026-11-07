import os
import urllib.request
import urllib.parse
import json
from src.scoring_engine import FundamentalEvaluation
from src.models.ipo_schema import VerdictTier


def format_telegram_ipo_alert(eval_res: FundamentalEvaluation) -> str:
    """Formats an IPO evaluation for short-term listing gain & exit alerts on Telegram."""
    if eval_res.verdict == VerdictTier.APPLY_LISTING_POP:
        icon = "🚀"
        tier_str = "APPLY FOR LISTING POP (STRONG BUY & SELL)"
    elif eval_res.verdict == VerdictTier.APPLY_SPECULATIVE:
        icon = "⚡"
        tier_str = "APPLY FOR SPECULATIVE FLIP"
    elif eval_res.verdict == VerdictTier.AVOID_LOW_GAIN:
        icon = "✋"
        tier_str = "AVOID / LOW LISTING GAIN"
    else:
        icon = "🛑"
        tier_str = "STRICT AVOID / DISCOUNT TRAP"

    st = eval_res.short_term_res
    pb = eval_res.playbook

    msg = [
        f"{icon} *IPO SHORT-TERM LISTING GAIN ALERT*",
        f"🏢 *{eval_res.company_name}* (`{eval_res.symbol}` | {eval_res.category})",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🎯 *APPLICATION VERDICT*: *{tier_str}*",
        f"📊 *Listing Score*: `{eval_res.composite_score} / 100`",
        f"💰 *Issue Price*: `₹{eval_res.issue_price:,.2f}` | *Lot*: `{eval_res.lot_size}` (₹{eval_res.lot_cost_inr:,.0f})",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"💸 *EXPECTED LISTING PROFIT*:",
        f"• *Expected Pop*: `+{eval_res.expected_gain_pct}%` (Target: `₹{eval_res.expected_listing_price:,.1f}`)",
        f"• *Estimated Profit/Lot*: `₹{eval_res.expected_profit_per_lot_inr:,.0f}`",
        f"• *Current GMP*: `₹{st.gmp_inr:,.1f}` ({st.gmp_trend} Trend)",
        f"• *Institutional QIB Rush*: `{st.qib_subscription}x` (Total: `{st.total_subscription}x`)",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⏰ *LISTING DAY 9:15 AM SELL STRATEGY*:",
        f"1. *Pre-Open (9:00 AM)*: {pb.pre_open_action}",
        f"2. *Market Open (9:15 AM)*: {pb.market_open_sell_rule}",
        f"3. *Upper Circuit*: {pb.circuit_freeze_strategy}",
        f"4. *Bailout*: {pb.emergency_bailout_rule}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"✨ *KEY CATALYSTS*:",
    ]

    for c in eval_res.key_strengths[:3]:
        msg.append(f"• {c}")

    msg.append("")
    msg.append("⚠️ *RISKS & TRAPS*:")
    if eval_res.key_risks:
        for r in eval_res.key_risks[:3]:
            msg.append(f"• {r}")
    else:
        msg.append("• Zero significant listing risks identified.")

    msg.append("")
    msg.append("🛡️ *TRADER DISCIPLINE*:")
    msg.append("_Never marry an IPO. Lock in listing profits and protect your trading capital._")

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
