"""
KIBOR Publish-Time Sniffer
===========================
Purpose: purely diagnostic. Checks whether today's KIBOR PDF has appeared
on SBP's API yet. If found, appends a row to sighting_log.csv with the
timestamp -- this is what a scheduled workflow uses to empirically
determine what time SBP actually publishes, without sending any emails
or touching the real pipeline.

If today's sighting is already logged, this exits immediately and does
nothing (so we don't spam commits every 15 minutes for the rest of the day
once we already have the answer).
"""
import csv
import os
import sys
from datetime import datetime

from main import search_pdf_in_api, PKT_ZONE, configure_logging

LOG_FILE = "sighting_log.csv"


def already_logged_today(today_str: str) -> bool:
    if not os.path.exists(LOG_FILE):
        return False
    with open(LOG_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0] == today_str:
                return True
    return False


def main() -> None:
    log = configure_logging()
    now_pkt = datetime.now(PKT_ZONE)
    today = now_pkt.date()
    today_str = today.isoformat()

    if now_pkt.weekday() >= 5:
        log.info("Weekend -- skipping sniffer check.")
        sys.exit(0)

    if already_logged_today(today_str):
        log.info(f"Already have a sighting logged for {today_str}. Nothing to do.")
        sys.exit(0)

    log.info(f"Checking API for today's ({today_str}) KIBOR file...")
    result = search_pdf_in_api(today)

    if result:
        file_new = not os.path.exists(LOG_FILE)
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if file_new:
                writer.writerow(["date", "first_seen_pkt", "url"])
            writer.writerow([today_str, now_pkt.strftime("%Y-%m-%d %H:%M:%S"), result.get("url", "")])
        log.info(f"[FOUND] Logged sighting at {now_pkt.strftime('%H:%M:%S')} PKT")
        # Signal to the workflow that a commit is needed
        print("::set-output name=found::true")
        with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as gh_out:
            gh_out.write("found=true\n")
    else:
        log.info("Not published yet. No log entry made.")
        with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as gh_out:
            gh_out.write("found=false\n")


if __name__ == "__main__":
    main()
