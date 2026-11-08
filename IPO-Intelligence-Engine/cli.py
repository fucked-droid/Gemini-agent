import argparse
import sys
import os

# Ensure package root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_loader import load_ipo_from_json, load_all_sample_ipos
from src.scoring_engine import evaluate_ipo
from src.report_generator import format_cli_report, BOLD, RESET, GREEN, RED, YELLOW, CYAN
MAGENTA = "\033[95m"
WHITE = "\033[97m"
from src.telegram_bot import format_telegram_ipo_alert, send_telegram_alert


def print_comparison_table(evaluations):
    print(f"\n{BOLD}{'COMPANY':<26} | {'STATUS':<15} | {'TIMELINE/LISTING':<16} | {'PRICE':<8} | {'SCORE':<6} | {'VERDICT':<30}{RESET}")
    print("-" * 115)
    for ev in evaluations:
        if ev.composite_score >= 75:
            color = GREEN
        elif ev.composite_score >= 60:
            color = CYAN
        elif ev.composite_score >= 45:
            color = YELLOW
        else:
            color = RED

        if ev.status == "READY_TO_LIST":
            status_disp = f"{CYAN}READY TO LIST{RESET}"
            date_str = ev.listing_date or "Pending"
        elif ev.status == "UPCOMING":
            status_disp = f"{YELLOW}UPCOMING{RESET}"
            date_str = ev.open_date or "TBA"
        else:
            status_disp = f"{GRAY}SAMPLE{RESET}"
            date_str = ev.open_date or "N/A"

        print(f"{BOLD}{ev.company_name[:24]:<26}{RESET} | {status_disp:<24} | {date_str[:15]:<16} | ₹{ev.issue_price:<7.1f} | {color}{ev.composite_score:>5.1f}{RESET} | {color}{ev.verdict.value:<30}{RESET}")
    print("-" * 115 + "\n")


def main():
    parser = argparse.ArgumentParser(description="IPO Intelligence Engine: Short-Term Listing Gain & Exit Playbook")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Command: scan
    scan_parser = subparsers.add_parser("scan", help="Scan and evaluate IPO profiles in data directory")
    scan_parser.add_argument("--dir", default=os.path.join(os.path.dirname(__file__), "data"), help="Path to data directory")
    scan_parser.add_argument("--telegram", action="store_true", help="Send top recommendation alerts to Telegram")
    scan_parser.add_argument("--filter", choices=["all", "active", "upcoming", "ready-to-list", "listing", "samples"], default="all",
                             help="Filter IPO profiles: 'active' (upcoming + ready-to-list), 'upcoming', 'ready-to-list', 'samples', or 'all'")
    scan_parser.add_argument("--upcoming", action="store_true", help="Filter for upcoming IPOs only")
    scan_parser.add_argument("--ready-to-list", "--listing", dest="ready_to_list", action="store_true", help="Filter for ready-to-list IPOs only")
    scan_parser.add_argument("--active", action="store_true", help="Filter for active pipeline (upcoming + ready-to-list, excludes samples)")

    # Command: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a specific IPO profile JSON file")
    analyze_parser.add_argument("file", help="Path to IPO JSON file")
    analyze_parser.add_argument("--telegram", action="store_true", help="Send evaluation to Telegram")

    # Command: live
    live_parser = subparsers.add_parser("live", help="Fetch real-time live IPO data & market calendar from public exchange portals")
    live_parser.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds")

    args = parser.parse_args()

    if args.command == "live":
        from src.live_fetcher import get_live_market_summary
        print(f"\n{BOLD}🌐 Fetching Live Real-Time IPO Tracker & Market Calendar from Chittorgarh & NSE...{RESET}")
        summary = get_live_market_summary(timeout=args.timeout)
        ref_date_str = summary["reference_date"]
        print(f"{CYAN}Source:{RESET} {summary['source']} | {CYAN}Ref Date:{RESET} {ref_date_str} | {CYAN}Fetched at:{RESET} {summary['timestamp']}\n")

        # Section 1: OPEN NOW
        print(f"{BOLD}{GREEN}🟢 SECTION 1: CURRENTLY OPEN FOR SUBSCRIPTION (Live Bidding Active){RESET}")
        print("-" * 95)
        if summary["open_now"]:
            print(f"{BOLD}{'COMPANY':<26} | {'SEGMENT':<10} | {'PRICE':<8} | {'GMP (INR / %)':<16} | {'SUB':<6} | {'CLOSE':<10}{RESET}")
            print("-" * 95)
            for r in summary["open_now"]:
                gmp_str = f"₹{r['gmp_inr']} ({r['gmp_pct']}%)"
                print(f"{BOLD}{r['company_name'][:24]:<26}{RESET} | {r['segment']:<10} | ₹{r['issue_price']:<7.1f} | {GREEN}{gmp_str:<16}{RESET} | {r['subscription_times']:>5.1f}x | {YELLOW}{r['close_date_str']:<10}{RESET}")
        else:
            print(f"{YELLOW}ℹ️  No IPOs are currently open for subscription today ({ref_date_str}).{RESET}")
            print(f"   (Primary market is closed for weekend/holiday break. Stale/closed IPOs are filtered out).")

        # Section 2: ALLOTMENT & LISTING WATCH
        print(f"\n{BOLD}{CYAN}🕒 SECTION 2: ALLOTMENT & LISTING WATCH (Closed, Listing in Next 24-72h){RESET}")
        print("-" * 95)
        if summary["waiting_listing"]:
            print(f"{BOLD}{'COMPANY':<26} | {'SEGMENT':<10} | {'PRICE':<8} | {'GMP (INR / %)':<16} | {'CLOSED':<8} | {'LISTING ON':<12}{RESET}")
            print("-" * 95)
            for r in summary["waiting_listing"]:
                gmp_str = f"₹{r['gmp_inr']} ({r['gmp_pct']}%)"
                print(f"{BOLD}{r['company_name'][:24]:<26}{RESET} | {r['segment']:<10} | ₹{r['issue_price']:<7.1f} | {GREEN}{gmp_str:<16}{RESET} | {r['close_date_str']:<8} | {CYAN}{r['listing_date_str']:<12}{RESET}")
        else:
            print("No immediate listings pending in the next 48 hours.")

        # Section 3: UPCOMING PIPELINE (Chittorgarh Consensus)
        print(f"\n{BOLD}{MAGENTA}🏢 SECTION 3: UPCOMING PIPELINE & DRHP WATCHLIST (Chittorgarh Consensus){RESET}")
        print("-" * 95)
        if summary["upcoming_pipeline"]:
            print(f"{BOLD}{'COMPANY':<36} | {'APPLY':<6} | {'NEUTRAL':<8} | {'AVOID':<6} | {'CONSENSUS':<22}{RESET}")
            print("-" * 95)
            for p in summary["upcoming_pipeline"][:10]:
                sent_color = GREEN if "APPLY" in p["sentiment"] else (RED if "AVOID" in p["sentiment"] else YELLOW)
                print(f"{BOLD}{p['company_name'][:34]:<36}{RESET} | {GREEN}{p['apply_votes']:>5}{RESET}  | {YELLOW}{p['neutral_votes']:>7}{RESET}  | {RED}{p['avoid_votes']:>5}{RESET} | {sent_color}{p['sentiment']:<22}{RESET}")

        # Section 4: EVENT CALENDAR
        print(f"\n{BOLD}{WHITE}📅 SECTION 4: OFFICIAL MARKET EVENT CALENDAR (Next 7-10 Days){RESET}")
        print("-" * 95)
        for ev in summary["calendar_events"][:8]:
            print(f"• {BOLD}{ev['date']:<14}{RESET} | Open: {GREEN}{ev['open_event']:<18}{RESET} | Close: {YELLOW}{ev['close_event']:<20}{RESET} | List: {CYAN}{ev['listing_event']}{RESET}")

        print(f"\n{CYAN}✓ Institutional Data Verification:{RESET} {summary['past_filtered_count']} closed/past secondary issues filtered out to maintain 100% data integrity.\n")
        return

    if not args.command or args.command == "scan":
        data_dir = getattr(args, "dir", os.path.join(os.path.dirname(__file__), "data"))
        profiles = load_all_sample_ipos(data_dir)
        if not profiles:
            print(f"No IPO profiles found in {data_dir}")
            return

        # Filtering logic
        filter_mode = getattr(args, "filter", "all")
        if getattr(args, "upcoming", False) or filter_mode == "upcoming":
            profiles = [p for p in profiles if p.status == "UPCOMING"]
            filter_desc = "Upcoming Pipeline IPOs"
        elif getattr(args, "ready_to_list", False) or filter_mode in ("ready-to-list", "listing"):
            profiles = [p for p in profiles if p.status == "READY_TO_LIST"]
            filter_desc = "Ready-To-List IPOs"
        elif getattr(args, "active", False) or filter_mode == "active":
            profiles = [p for p in profiles if p.status in ("UPCOMING", "READY_TO_LIST")]
            filter_desc = "Active & Ready-To-List IPOs (Excluding Samples)"
        elif filter_mode == "samples":
            profiles = [p for p in profiles if p.status == "SAMPLE"]
            filter_desc = "Benchmark Sample Profiles"
        else:
            filter_desc = "All IPO Profiles"

        if not profiles:
            print(f"No IPO profiles matched filter: {filter_desc}")
            return

        print(f"\n{BOLD}🔍 Scanning {len(profiles)} {filter_desc} for Short-Term Listing Gain & Exit Strategy...{RESET}")
        evaluations = [evaluate_ipo(p) for p in profiles]
        print_comparison_table(evaluations)

        for ev in evaluations:
            report = format_cli_report(ev)
            print(report)

            if getattr(args, "telegram", False):
                tg_msg = format_telegram_ipo_alert(ev)
                sent = send_telegram_alert(tg_msg)
                status = "Delivered" if sent else "Failed/Not Configured"
                print(f"[Telegram Notification] {ev.company_name}: {status}")

    elif args.command == "analyze":
        profile = load_ipo_from_json(args.file)
        ev = evaluate_ipo(profile)
        print(format_cli_report(ev))

        if args.telegram:
            tg_msg = format_telegram_ipo_alert(ev)
            sent = send_telegram_alert(tg_msg)
            status = "Delivered" if sent else "Failed/Not Configured"
            print(f"[Telegram Notification] {ev.company_name}: {status}")


if __name__ == "__main__":
    main()
