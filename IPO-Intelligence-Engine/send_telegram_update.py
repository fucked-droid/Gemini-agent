import os
import sys

# Ensure package root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_loader import load_ipo_from_json
from src.scoring_engine import evaluate_ipo
from src.telegram_bot import format_telegram_ipo_alert, send_telegram_alert

def dispatch_all_alerts():
    print("Initiating Telegram Alert Dispatch...")
    
    # 1. Dispatch Executive Briefing
    briefing = (
        "🏛️ *IPO INTELLIGENCE ENGINE — EXECUTIVE DISPATCH*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📅 *Current Market Status*: Diwali Festival Window\n"
        "• *Open IPOs for Bidding*: `0` (Exchange Holiday Break)\n"
        "• *Upcoming Listings This Week*:\n"
        "  1️⃣ *Vedant Poly Fabs* (SME_NSE) — *Listing Mon 09-Nov (Tomorrow)*\n"
        "  2️⃣ *Antala Industries* (SME_BSE) — *Listing Wed 11-Nov*\n\n"
        "Detailed actionable 9:15 AM T+0 exit reports dispatched below 👇"
    )
    sent_brief = send_telegram_alert(briefing)
    print(f"Executive Briefing: {'Sent successfully' if sent_brief else 'Failed'}")

    # 2. Vedant Poly Fabs Alert
    vedant_path = os.path.join(os.path.dirname(__file__), "data", "live_vedant_poly_fabs_ipo.json")
    if os.path.exists(vedant_path):
        p = load_ipo_from_json(vedant_path)
        ev = evaluate_ipo(p)
        msg = format_telegram_ipo_alert(ev)
        sent = send_telegram_alert(msg)
        print(f"Vedant Poly Fabs Alert: {'Sent successfully' if sent else 'Failed'}")

    # 3. Antala Industries Alert
    antala_path = os.path.join(os.path.dirname(__file__), "data", "live_antala_industries_ipo.json")
    if os.path.exists(antala_path):
        p = load_ipo_from_json(antala_path)
        ev = evaluate_ipo(p)
        msg = format_telegram_ipo_alert(ev)
        sent = send_telegram_alert(msg)
        print(f"Antala Industries Alert: {'Sent successfully' if sent else 'Failed'}")

    # 4. Jio Platforms Alert
    jio_path = os.path.join(os.path.dirname(__file__), "data", "live_jio_platforms_ipo.json")
    if os.path.exists(jio_path):
        p = load_ipo_from_json(jio_path)
        ev = evaluate_ipo(p)
        msg = format_telegram_ipo_alert(ev)
        sent = send_telegram_alert(msg)
        print(f"Jio Platforms Alert: {'Sent successfully' if sent else 'Failed'}")

if __name__ == "__main__":
    dispatch_all_alerts()
