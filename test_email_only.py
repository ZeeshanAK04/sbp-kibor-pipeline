"""
Quick isolated test -- confirms SMTP credentials work by sending
yesterday's already-verified KIBOR PDF to yourself, WITHOUT waiting
for today's polling loop.

Usage:
    (after loading .env into the session, same as test_pipeline.py)
    python test_email_only.py
"""
from datetime import datetime, timedelta
from main import (
    configure_logging, load_config, fetch_and_validate,
    email_file, PKT_ZONE
)

log = configure_logging()

config = load_config()

now_pkt = datetime.now(PKT_ZONE)
yesterday = now_pkt.date() - timedelta(days=1)

print(f"Fetching known-good KIBOR PDF for {yesterday.isoformat()}...")
result = fetch_and_validate(yesterday)

if not result:
    print("[FAIL] Could not fetch yesterday's PDF -- unexpected, since test_pipeline.py found it earlier.")
else:
    pdf_bytes, html_table, filename = result
    print(f"[OK] Fetched {filename} ({len(pdf_bytes)/1024:.1f} KB). Sending test email to: {config['EMAIL_TO']}")
    email_file(config, pdf_bytes, filename, html_table, yesterday)
    print("[OK] Email send attempted -- check your inbox (and spam folder).")