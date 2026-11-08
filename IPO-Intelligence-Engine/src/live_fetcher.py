"""
Live IPO Data Fetcher & Real-Time Market Feed.
Directly scrapes real-time primary market data and official IPO calendar events from:
- InvestorGain Live GMP Tracker: https://www.investorgain.com/report/live-ipo-gmp/331/
- InvestorGain Live IPO Event Calendar: https://www.investorgain.com/report/watch-live-ipo-event-calendar/554/
"""

import os
import re
import sys
import json
import urllib.request
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
LIVE_GMP_URL = "https://www.investorgain.com/report/live-ipo-gmp/331/"
EVENT_CALENDAR_URL = "https://www.investorgain.com/report/watch-live-ipo-event-calendar/554/"


def clean_html(text: str) -> str:
    """Removes HTML tags and unescapes entities."""
    t = re.sub(r"<[^>]+>", " ", text)
    t = t.replace("&#8377;", "₹").replace("&amp;", "&").replace("&#128293;", "🔥")
    t = re.sub(r"\[email&#160;protected\]", "", t)
    return " ".join(t.split()).strip()


def parse_numeric(val: str) -> float:
    """Extracts first valid floating point number from string."""
    clean = val.replace(",", "").replace("₹", "").strip()
    match = re.search(r"[-+]?\d*\.?\d+", clean)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return 0.0
    return 0.0


def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetches URL contents using requests or urllib."""
    headers = {"User-Agent": USER_AGENT}
    if HAS_REQUESTS:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    else:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")


def fetch_live_gmp_table(timeout: int = 15) -> List[Dict[str, Any]]:
    """Scrapes the live GMP and subscription tracker table."""
    html = fetch_url(LIVE_GMP_URL, timeout=timeout)
    rows = re.findall(r"<tr.*?>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    records = []

    for row in rows:
        cols = re.findall(r"<td.*?>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
        if len(cols) < 11:
            continue

        raw_name = clean_html(cols[0])
        segment = "MAINBOARD"
        if "BSE SME" in raw_name.upper():
            segment = "SME_BSE"
        elif "NSE SME" in raw_name.upper() or "SME" in raw_name.upper():
            segment = "SME_NSE"

        clean_name = re.sub(r"(BSE SME|NSE SME|SME|IPO|C)\b", "", raw_name, flags=re.IGNORECASE)
        clean_name = " ".join(clean_name.split()).strip()

        # GMP extraction
        gmp_text = clean_html(cols[1])
        gmp_inr = 0.0
        gmp_pct = 0.0
        inr_match = re.search(r"₹\s*([0-9.]+)", gmp_text)
        if inr_match:
            gmp_inr = parse_numeric(inr_match.group(1))
        pct_match = re.search(r"\(([0-9.]+)%\)", gmp_text)
        if pct_match:
            gmp_pct = parse_numeric(pct_match.group(1))

        trend = "STABLE"
        if "↓" in gmp_text and "↑" not in gmp_text:
            trend = "FALLING"
        elif "↑" in gmp_text and "↓" not in gmp_text:
            trend = "RISING"

        sub_times = parse_numeric(clean_html(cols[3]))
        issue_price = parse_numeric(clean_html(cols[4]))
        issue_size_cr = parse_numeric(clean_html(cols[5]))
        lot_size = int(parse_numeric(clean_html(cols[6]))) or 1

        open_dt = clean_html(cols[7]).split()[0] if clean_html(cols[7]) else "TBA"
        close_dt = clean_html(cols[8]).split()[0] if clean_html(cols[8]) else "TBA"
        listing_dt = clean_html(cols[10]).split()[0] if len(cols) > 10 and clean_html(cols[10]) else "TBA"

        records.append({
            "company_name": clean_name,
            "raw_name": raw_name,
            "segment": segment,
            "issue_price": issue_price,
            "lot_size": lot_size,
            "issue_size_cr": issue_size_cr,
            "gmp_inr": gmp_inr,
            "gmp_pct": gmp_pct,
            "gmp_trend": trend,
            "subscription_times": sub_times,
            "open_date": open_dt,
            "close_date": close_dt,
            "listing_date": listing_dt,
            "lot_cost_inr": issue_price * lot_size
        })

    return records


def fetch_live_calendar_events(timeout: int = 15) -> List[Dict[str, Any]]:
    """Scrapes the live official IPO event calendar."""
    html = fetch_url(EVENT_CALENDAR_URL, timeout=timeout)
    rows = re.findall(r"<tr.*?>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    events = []

    for row in rows:
        cols = re.findall(r"<t[hd].*?>(.*?)</t[hd]>", row, re.DOTALL | re.IGNORECASE)
        if len(cols) >= 6:
            cleaned = [" ".join(clean_html(c).split()) for c in cols]
            date_str = cleaned[0]
            if date_str and not date_str.startswith("Date"):
                open_str = cleaned[1]
                close_str = cleaned[2]
                boa_str = cleaned[3]
                unblock_str = cleaned[4]
                listing_str = cleaned[5]
                if any([open_str, close_str, boa_str, unblock_str, listing_str]):
                    events.append({
                        "date": date_str,
                        "open_event": open_str,
                        "close_event": close_str,
                        "allotment_event": boa_str,
                        "unblock_event": unblock_str,
                        "listing_event": listing_str
                    })
    return events


def get_live_market_summary(timeout: int = 15) -> Dict[str, Any]:
    """Combines live GMP table and event calendar into a unified live feed."""
    gmp_data = fetch_live_gmp_table(timeout=timeout)
    cal_events = fetch_live_calendar_events(timeout=timeout)

    return {
        "source": "InvestorGain Live Feed & Official Market Calendar",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "gmp_records": gmp_data,
        "calendar_events": cal_events
    }


if __name__ == "__main__":
    print("=" * 80)
    print("  LIVE REAL-TIME IPO DATA & CALENDAR (Direct Public Portal Feed)")
    print("=" * 80)
    try:
        summary = get_live_market_summary()
        print(f"Source: {summary['source']} | Timestamp: {summary['timestamp']}\n")
        
        print("--- UPCOMING IPO EVENT CALENDAR (Next 7-10 Days) ---")
        for ev in summary["calendar_events"][:10]:
            print(f"• {ev['date']:<14} | Open: {ev['open_event']:<20} | Close: {ev['close_event']:<20} | Listing: {ev['listing_event']}")

        print("\n--- RECENT & ACTIVE ISSUES FROM LIVE TRACKER ---")
        for r in summary["gmp_records"][:10]:
            print(f"• {r['company_name'][:26]:<28} | {r['segment']:<10} | ₹{r['issue_price']:<6.1f} | GMP: ₹{r['gmp_inr']} ({r['gmp_pct']}%) | Close: {r['close_date']} | List: {r['listing_date']}")
    except Exception as e:
        print("Error fetching live feed:", e)
