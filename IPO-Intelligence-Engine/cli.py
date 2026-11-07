import argparse
import sys
import os

# Ensure package root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_loader import load_ipo_from_json, load_all_sample_ipos
from src.scoring_engine import evaluate_ipo
from src.report_generator import format_cli_report, BOLD, RESET, GREEN, RED, YELLOW, CYAN
from src.telegram_bot import format_telegram_ipo_alert, send_telegram_alert


def print_comparison_table(evaluations):
    print(f"\n{BOLD}{'COMPANY':<28} | {'SEGMENT':<10} | {'PRICE':<8} | {'SCORE':<6} | {'VERDICT':<30}{RESET}")
    print("-" * 92)
    for ev in evaluations:
        if ev.composite_score >= 75:
            color = GREEN
        elif ev.composite_score >= 60:
            color = CYAN
        elif ev.composite_score >= 45:
            color = YELLOW
        else:
            color = RED

        print(f"{BOLD}{ev.company_name[:26]:<28}{RESET} | {ev.category:<10} | ₹{ev.issue_price:<7.1f} | {color}{ev.composite_score:>5.1f}{RESET} | {color}{ev.verdict.value:<30}{RESET}")
    print("-" * 92 + "\n")


def main():
    parser = argparse.ArgumentParser(description="IPO Intelligence Engine: Long-Term Fundamental Evaluation System")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Command: scan
    scan_parser = subparsers.add_parser("scan", help="Scan and evaluate all IPO profiles in data directory")
    scan_parser.add_argument("--dir", default=os.path.join(os.path.dirname(__file__), "data"), help="Path to data directory")
    scan_parser.add_argument("--telegram", action="store_true", help="Send top recommendation alerts to Telegram")

    # Command: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a specific IPO profile JSON file")
    analyze_parser.add_argument("file", help="Path to IPO JSON file")
    analyze_parser.add_argument("--telegram", action="store_true", help="Send evaluation to Telegram")

    args = parser.parse_args()

    if not args.command or args.command == "scan":
        data_dir = getattr(args, "dir", os.path.join(os.path.dirname(__file__), "data"))
        profiles = load_all_sample_ipos(data_dir)
        if not profiles:
            print(f"No IPO profiles found in {data_dir}")
            return

        print(f"\n{BOLD}🔍 Scanning {len(profiles)} IPO Profiles for Fundamental Quality & Long-Term Moats...{RESET}")
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
