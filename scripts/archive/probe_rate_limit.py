#!/usr/bin/env python3
"""
Inner West rate limit probe.

Sends HEAD requests to a sample of chapter URLs at increasing delays
and reports which delay avoids 429s.

Usage:
    python scripts/probe_rate_limit.py

Does NOT write to DB or R2. Read-only probe. Run once to find the threshold.
"""

import time
import sys
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "application/pdf,*/*",
}

BASE = "https://www.innerwest.nsw.gov.au"

# 20 chapters across all three councils — enough to stress the rate limit
SAMPLE_URLS = [
    # Marrickville
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%20Contents%20Nov%2022.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%201%20-%20Statutory%20Information%20with%20IWLEP%202022%20amendments%20Nov%2022.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%201%20Urban%20Design.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%203%20Site%20Context%20Analysis.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%205%20Equity%20of%20Access%20and%20Mobility.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%206%20Acoustic%20and%20Visual%20Privacy.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%207%20Solar%20Access%20and%20Overshadowing.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%208%20Social%20Impact%20Assessment.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%209%20Community%20Safety.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2010%20Parking.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2011%20Fencing.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2012%20Signs%20and%20Advertising%20Structures.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2013%20Biodiversity.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2014%20Unique%20Environmental%20Features.pdf.aspx",
    "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2016%20Energy%20Efficiency.pdf.aspx",
    # Leichhardt
    "/ArticleDocuments/209/Leichhardt%20DCP%202013%20-%20Part%20A%20Introduction.pdf.aspx",
    "/ArticleDocuments/209/Leichhardt%20DCP%202013%20-%20Part%20B%20General%20Controls.pdf.aspx",
    "/ArticleDocuments/209/Leichhardt%20DCP%202013%20-%20Part%20C%20Residential%20Development.pdf.aspx",
    # Ashfield
    "/ArticleDocuments/260/Ashfield%20DCP%202007%20-%20Part%20A.pdf.aspx",
    "/ArticleDocuments/260/Ashfield%20DCP%202007%20-%20Part%20B.pdf.aspx",
]

DELAYS_TO_TEST = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]


def probe_at_delay(delay: float) -> dict:
    """Send all sample requests at the given inter-request delay. Return results."""
    results = {"delay": delay, "ok": 0, "rate_limited": 0, "other_error": 0, "first_429_at": None}
    print(f"\n--- Testing delay={delay}s ---")
    for i, path in enumerate(SAMPLE_URLS):
        url = BASE + path
        try:
            resp = requests.head(url, headers=HEADERS, timeout=30, allow_redirects=True)
            status = resp.status_code
            retry_after = resp.headers.get("Retry-After", "")
            if status in (200, 206):
                print(f"  [{i+1:02d}] {status} OK")
                results["ok"] += 1
            elif status == 429:
                print(f"  [{i+1:02d}] 429 RATE LIMITED  (Retry-After: {retry_after or 'not set'})")
                results["rate_limited"] += 1
                if results["first_429_at"] is None:
                    results["first_429_at"] = i + 1
            else:
                print(f"  [{i+1:02d}] {status} unexpected")
                results["other_error"] += 1
        except Exception as exc:
            print(f"  [{i+1:02d}] ERROR: {exc}")
            results["other_error"] += 1

        if i < len(SAMPLE_URLS) - 1:
            time.sleep(delay)

    return results


def main():
    print("Inner West rate limit probe")
    print(f"Sample size: {len(SAMPLE_URLS)} URLs")
    print(f"Testing delays: {DELAYS_TO_TEST}")
    print("\nThis will send HEAD requests only — no downloads, no DB writes.")
    print("Pause 30s between delay tiers to let the rate limit window reset.\n")

    all_results = []

    for delay in DELAYS_TO_TEST:
        result = probe_at_delay(delay)
        all_results.append(result)

        if result["rate_limited"] == 0:
            print(f"\n  -> Clean run at {delay}s — no 429s.")
            # Run one more time at same delay to confirm it's stable
            print(f"  -> Confirming with second pass at {delay}s...")
            confirm = probe_at_delay(delay)
            if confirm["rate_limited"] == 0:
                print(f"\n  CONFIRMED: {delay}s is sufficient. Stopping.")
                all_results.append(confirm)
                break
            else:
                print(f"  Second pass had {confirm['rate_limited']} 429s — not stable, continuing.")
                all_results.append(confirm)
        else:
            print(f"\n  -> {result['rate_limited']} 429s at {delay}s (first at request #{result['first_429_at']})")

        if delay != DELAYS_TO_TEST[-1]:
            print(f"  Waiting 30s before next tier...")
            time.sleep(30)

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for r in all_results:
        status = "CLEAN" if r["rate_limited"] == 0 else f"{r['rate_limited']} 429s (first at #{r['first_429_at']})"
        print(f"  {r['delay']:4.1f}s  {status}")

    clean = [r for r in all_results if r["rate_limited"] == 0]
    if clean:
        recommended = clean[0]["delay"]
        # Add 20% buffer
        with_buffer = round(recommended * 1.2, 1)
        print(f"\nRecommended sleep in r2_monitor.py: {with_buffer}s  ({recommended}s observed threshold + 20% buffer)")
    else:
        print("\nAll delays tested produced 429s. Try longer delays manually.")
        sys.exit(1)


if __name__ == "__main__":
    main()
