"""
Automated IPO Market Sentinel & Notification Daemon.
Monitors the market calendar continuously and delivers automatic alerts:
1. Listing Day 9:00 AM & 9:15 AM Sell Alerts.
2. Bidding Day 2:30 PM Final Application Decisions.
3. New IPO Launch Alerts.
Delivers via Telegram + Windows Desktop Toast Notifications.
"""

import os
import sys
import time
import shutil
import subprocess
from datetime import datetime, time as dtime

# Ensure package root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.live_fetcher import get_live_market_summary
from src.telegram_bot import send_telegram_alert


def send_windows_toast(title: str, message: str):
    """Sends native desktop notification (Windows Toast or Termux Android Notification)."""
    clean_title = title.replace('"', '').replace("'", "")
    clean_msg = message.replace('"', '').replace("'", "")

    # On Android Termux: use termux-notification if available
    if sys.platform != "win32":
        termux_notify = "/data/data/com.termux/files/usr/bin/termux-notification"
        if os.path.exists(termux_notify) or shutil.which("termux-notification"):
            try:
                subprocess.run(["termux-notification", "--title", clean_title, "--content", clean_msg], timeout=3)
            except Exception:
                pass
        return

    # On Windows: use Windows.UI.Notifications
    ps_cmd = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $toastXml = [xml]$template.GetXml()
    $toastXml.GetElementsByTagName('text')[0].AppendChild($toastXml.CreateTextNode('{clean_title}')) > $null
    $toastXml.GetElementsByTagName('text')[1].AppendChild($toastXml.CreateTextNode('{clean_msg}')) > $null
    $toast = [Windows.UI.Notifications.ToastNotification]::new($toastXml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('IPO Intelligence Engine').Show($toast)
    """
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=5)
    except Exception as e:
        print(f"[Toast Notification Error] {e}")


def dispatch_dual_alert(title: str, text: str, short_summary: str = ""):
    """Dispatches alert to both Telegram (phone) and Windows Desktop Toast (screen)."""
    # 1. Desktop notification
    toast_body = short_summary or text[:120] + "..."
    send_windows_toast(title, toast_body)
    
    # 2. Telegram message
    sent_tg = send_telegram_alert(f"*{title}*\n\n{text}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Alert Dispatched -> Desktop: OK | Telegram: {'OK' if sent_tg else 'Blocked/Offline'}")


def check_and_notify_events():
    """Checks the live calendar and market timing to deliver automated alerts."""
    now = datetime.now()
    cur_time = now.time()
    cur_day_str = now.strftime("%d-%b")

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Checking IPO Primary Market Sentinel...")

    try:
        summary = get_live_market_summary(timeout=15)
    except Exception as e:
        print(f"Failed to fetch market data: {e}")
        return

    # Check 1: Listing Day Morning (Between 8:55 AM and 9:16 AM)
    for ev in summary.get("calendar_events", []):
        if cur_day_str.lower() in ev.get("date", "").lower():
            listing_event = ev.get("listing_event", "")
            if listing_event and not listing_event.lower().startswith("no"):
                # Pre-Open Alert (8:55 AM - 9:05 AM)
                if dtime(8, 55) <= cur_time <= dtime(9, 5):
                    title = "⏰ IPO LISTING DAY PRE-OPEN (9:00 AM)"
                    body = (
                        f"🚨 *{listing_event}* is listing TODAY!\n\n"
                        f"• Check Pre-Open indicative price (9:00 - 9:08 AM).\n"
                        f"• Prepare your 9:15 AM market/limit sell order to lock in listing pop.\n"
                        f"• Strict Rule: Do not baghold!"
                    )
                    dispatch_dual_alert(title, body, f"{listing_event} is listing today! Prepare 9:15 AM exit.")

                # Opening Bell Exit Reminder (9:14 AM - 9:16 AM)
                elif dtime(9, 14) <= cur_time <= dtime(9, 17):
                    title = "🚨 9:15 AM MARKET OPEN: SELL ALLOTMENT NOW!"
                    body = (
                        f"🔔 Opening Bell has rung for *{listing_event}*!\n\n"
                        f"• Execute 100% quantity exit now.\n"
                        f"• Lock in your listing profit per lot.\n"
                        f"• Cut-loss immediately if opening below issue price!"
                    )
                    dispatch_dual_alert(title, body, f"9:15 AM BELL: Exit {listing_event} now to lock profits!")

    # Check 2: Day 3 Bidding Closing Call (Between 2:15 PM and 2:45 PM)
    if dtime(14, 15) <= cur_time <= dtime(14, 45):
        for ev in summary.get("calendar_events", []):
            if cur_day_str.lower() in ev.get("date", "").lower():
                close_event = ev.get("close_event", "")
                if close_event:
                    title = "🎯 IPO CLOSING DAY (2:30 PM FINAL CALL)"
                    body = (
                        f"⏳ *{close_event}* bidding CLOSES TODAY at 5:00 PM!\n\n"
                        f"• Review final institutional QIB subscription numbers.\n"
                        f"• If QIB > 15x & GMP > 20%: Good for listing pop.\n"
                        f"• If QIB < 3x: AVOID to prevent capital loss."
                    )
                    dispatch_dual_alert(title, body, f"{close_event} closing today at 5 PM! Check final verdict.")


def run_continuous_daemon(poll_interval_seconds: int = 60):
    """Runs continuous background monitor checking every poll interval."""
    print("=" * 75)
    print("  🚀 IPO INTELLIGENCE ENGINE — BACKGROUND SENTINEL RUNNING")
    print(f"  • Interval : Every {poll_interval_seconds} seconds")
    print("  • Alerts   : Automatic 9:00 AM Pre-Open, 9:15 AM Bell Exit, 2:30 PM Closing Call")
    print("  • Delivery : Windows Desktop Notification + Telegram Bot")
    print("=" * 75)

    # Run initial check immediately
    check_and_notify_events()

    while True:
        try:
            time.sleep(poll_interval_seconds)
            check_and_notify_events()
        except KeyboardInterrupt:
            print("\nSentinel stopped by user.")
            break
        except Exception as e:
            print(f"Sentinel loop exception: {e}")
            time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="IPO Automated Sentinel Daemon")
    parser.add_argument("--once", action="store_true", help="Run once and exit (for Task Scheduler / Cron)")
    parser.add_argument("--interval", type=int, default=60, help="Loop interval in seconds (default 60)")
    args = parser.parse_args()

    if args.once:
        check_and_notify_events()
    else:
        run_continuous_daemon(poll_interval_seconds=args.interval)
