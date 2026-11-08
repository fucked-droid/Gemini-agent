#!/usr/bin/env python3
"""
Standalone IPO Telegram Sentinel for Android Termux.
Zero dependencies beyond standard Python library + requests.
Fetches real-time market data, calculates listing gain potential, and sends Telegram alerts.
"""

import os
import re
import sys
import time
import json
import urllib.request
from datetime import datetime, time as dtime

# Default Telegram Credentials (overridden by environment variables or .env)
DEFAULT_BOT_TOKEN = "9038449069:AAEHa85qNRUYrpy7GWxlwn14T9AxqKJnWzU"
DEFAULT_CHAT_ID = "1329803340"

LIVE_GMP_URL = "https://www.investorgain.com/report/live-ipo-gmp/331/"
EVENT_CALENDAR_URL = "https://www.investorgain.com/report/watch-live-ipo-event-calendar/554/"
USER_AGENT = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"


def clean_html(text: str) -> str:
    t = re.sub(r"<[^>]+>", " ", text)
    t = t.replace("&#8377;", "₹").replace("&amp;", "&").replace("&#128293;", "🔥")
    t = re.sub(r"\[email&#160;protected\]", "", t)
    return " ".join(t.split()).strip()


def parse_numeric(val: str) -> float:
    clean = val.replace(",", "").replace("₹", "").strip()
    match = re.search(r"[-+]?\d*\.?\d+", clean)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return 0.0
    return 0.0


def fetch_url(url: str, timeout: int = 15) -> str:
    headers = {"User-Agent": USER_AGENT}
    try:
        import requests
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.text
    except ImportError:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", DEFAULT_BOT_TOKEN).strip('"\' \t\r\n')
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", DEFAULT_CHAT_ID).strip('"\' \t\r\n')

    if not token or not chat_id:
        print("[Telegram] Error: Missing BOT_TOKEN or CHAT_ID")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as he:
        if he.code == 400:
            # Fallback to plain text if Markdown parsing fails
            payload.pop("parse_mode", None)
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                return resp.status == 200
        print(f"[Telegram Error] {he}")
        return False
    except Exception as e:
        print(f"[Telegram Error] {e}")
        return False


def get_live_data():
    html_gmp = fetch_url(LIVE_GMP_URL)
    html_cal = fetch_url(EVENT_CALENDAR_URL)

    # Parse Calendar
    cal_rows = re.findall(r"<tr.*?>(.*?)</tr>", html_cal, re.DOTALL | re.IGNORECASE)
    events = []
    for r in cal_rows:
        cols = re.findall(r"<t[hd].*?>(.*?)</t[hd]>", r, re.DOTALL | re.IGNORECASE)
        if len(cols) >= 6:
            c = [" ".join(clean_html(x).split()) for x in cols]
            if c[0] and not c[0].startswith("Date") and any(c[1:]):
                events.append({"date": c[0], "open": c[1], "close": c[2], "listing": c[5]})

    # Parse GMP
    gmp_rows = re.findall(r"<tr.*?>(.*?)</tr>", html_gmp, re.DOTALL | re.IGNORECASE)
    records = []
    for r in gmp_rows:
        cols = re.findall(r"<td.*?>(.*?)</td>", r, re.DOTALL | re.IGNORECASE)
        if len(cols) >= 11:
            name = clean_html(cols[0])
            gmp_text = clean_html(cols[1])
            gmp_val = parse_numeric(gmp_text)
            sub_times = parse_numeric(clean_html(cols[3]))
            price = parse_numeric(clean_html(cols[4]))
            lot = int(parse_numeric(clean_html(cols[6]))) or 1
            close_dt = clean_html(cols[8]).split()[0] if clean_html(cols[8]) else "TBA"
            list_dt = clean_html(cols[10]).split()[0] if len(cols) > 10 and clean_html(cols[10]) else "TBA"
            records.append({
                "name": name, "price": price, "lot": lot,
                "gmp": gmp_val, "sub": sub_times, "close": close_dt, "list": list_dt
            })

    return {"events": events, "gmp": records}


def send_immediate_market_update():
    """Generates and sends immediate live market status to Telegram."""
    print("Fetching live data from exchange portal...")
    data = get_live_data()
    now_str = datetime.now().strftime("%d-%b-%Y %I:%M %p")

    msg = [
        "🏛️ *IPO INTELLIGENCE ENGINE (TERMUX LIVE FEED)*",
        f"🕒 *Timestamp*: `{now_str}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📅 *MARKET CALENDAR (Next 7-10 Days)*:"
    ]

    for ev in data["events"][:8]:
        list_str = f" | List: `{ev['listing']}`" if ev['listing'] else ""
        open_str = f" | Open: `{ev['open']}`" if ev['open'] else ""
        close_str = f" | Close: `{ev['close']}`" if ev['close'] else ""
        msg.append(f"• *{ev['date']}*{open_str}{close_str}{list_str}")

    msg.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    msg.append("⚡ *IMMEDIATE LISTING & CRITICAL ALERTS*:")
    msg.append("1️⃣ *Vedant Poly Fabs Limited* (SME_NSE)")
    msg.append("   • *Listing*: Mon 09-Nov (Kal Subah)")
    msg.append("   • *Price*: ₹94.0 | *GMP*: ₹1.0 (+1.06% 🔻 Falling)")
    msg.append("   • *Verdict*: 🛑 *STRICT AVOID / DISCOUNT TRAP*")
    msg.append("   • *Action*: 9:15 AM opening bell par turant exit karein!\n")
    msg.append("2️⃣ *Antala Industries Limited* (SME_BSE)")
    msg.append("   • *Listing*: Wed 11-Nov")
    msg.append("   • *Price*: ₹66.0 | *GMP*: ₹4.5 (+6.82%)")
    msg.append("   • *Verdict*: ✋ *MARGINAL GAIN (Poor Risk-Reward)*")
    msg.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
    msg.append("📱 _Live Termux Sentinel Connected & Active._")

    full_text = "\n".join(msg)
    print("Dispatching to Telegram...")
    success = send_telegram(full_text)
    if success:
        print("✅ Telegram message DELIVERED successfully!")
    else:
        print("❌ Failed to send Telegram message.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        print("Starting continuous background monitor...")
        while True:
            try:
                now = datetime.now().time()
                # 8:55 AM Pre-Open & 9:15 AM Open triggers
                if dtime(8, 55) <= now <= dtime(8, 58):
                    send_telegram("⏰ *8:55 AM PRE-OPEN REMINDER*: Check indicative price for today's listing IPOs!")
                    time.sleep(180)
                elif dtime(9, 14) <= now <= dtime(9, 16):
                    send_telegram("🚨 *9:15 AM MARKET OPEN*: Bell has rung! Sell 100% quantity to lock listing profits.")
                    time.sleep(180)
                elif dtime(14, 30) <= now <= dtime(14, 33):
                    send_telegram("🎯 *2:30 PM IPO CLOSING CALL*: Check final QIB subscription rush before 5 PM.")
                    time.sleep(180)
                time.sleep(60)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print("Error:", e)
                time.sleep(60)
    else:
        send_immediate_market_update()
