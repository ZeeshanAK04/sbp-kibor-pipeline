"""
Quick verification script -- tests the core pipeline logic
against the live SBP API / website WITHOUT sending any emails.
"""
import sys
import io

# Fix Windows console encoding for Unicode
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from main import (
    configure_logging, fetch_and_validate, PKT_ZONE
)
from datetime import datetime, timedelta

log = configure_logging()

print("=" * 60)
print("SBP Pipeline -- Verification Test (GitHub Actions Version)")
print("=" * 60)

now_pkt = datetime.now(PKT_ZONE)
today = now_pkt.date()
print(f"\nCurrent PKT time : {now_pkt.strftime('%Y-%m-%d %H:%M:%S PKT')}")
print(f"Today (target)   : {today.isoformat()} ({today.strftime('%A')})")

# -- Test 1: Fetch and Validate for Today --
print(f"\n{'-' * 40}")
print(f"TEST 1: Run fetch and validate for today ({today.isoformat()})")
try:
    result = fetch_and_validate(today)
    if result:
        pdf_bytes, html_table, filename = result
        print(f"  [OK] Successfully fetched and validated today's rates!")
        print(f"  File name : {filename}")
        print(f"  PDF size  : {len(pdf_bytes) / 1024:.1f} KB")
        print("\n  Extracted Table HTML snippet:")
        print("\n".join(html_table.split("\n")[:15])) # Print first 15 lines of HTML table
    else:
        print("  [INFO] Today's exchange rate PDF is not published by SBP yet.")
        
        # Test 2: Try yesterday's date to verify the download and parsing logic
        print(f"\n{'-' * 40}")
        yesterday = today - timedelta(days=1)
        # Skip Sunday/Saturday target if today is Monday
        if today.weekday() == 0:
            yesterday = today - timedelta(days=3)
            
        print(f"TEST 2: Fallback test for date {yesterday.isoformat()} ({yesterday.strftime('%A')})")
        y_result = fetch_and_validate(yesterday)
        if y_result:
            pdf_bytes, html_table, filename = y_result
            print(f"  [OK] Successfully fetched and validated date rates!")
            print(f"  File name : {filename}")
            print(f"  PDF size  : {len(pdf_bytes) / 1024:.1f} KB")
            print("\n  Extracted Table HTML snippet:")
            print("\n".join(html_table.split("\n")[:15]))
        else:
            print("  [WARN] Could not retrieve rates for fallback date either. SBP site may be experiencing transient downtime.")

except Exception as exc:
    print(f"  [FAIL] Test encountered error: {exc}")
    import traceback
    traceback.print_exc()

print(f"\n{'-' * 40}")
print("TEST 3: Email send (SKIPPED -- run python main.py with correct env variables to test)")

print(f"\n{'=' * 60}")
print("VERIFICATION COMPLETED")
print("=" * 60)
